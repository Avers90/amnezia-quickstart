#!/usr/bin/env python3
"""
Generate per-host AmneziaWG obfuscation parameters.

Every host must get its own set. Sharing H1-H4 or the I1 signature across
servers means one leaked client config fingerprints all of them at once. The
script scans the inventory and refuses to hand out an H value, a CPS signature
or even a CPS domain that another host already uses.

Config versions (implied by which parameters are present, mirrors
awgVersionOf() in amnezia-client/client/core/models/protocols/awgProtocolConfig.cpp):

  1.0  none of the below
  1.5  any of I1-I5 set
  2.0  S3 > 0, or S4 > 0, or any of H1-H4 given as a range "a-b"

Constraints (amnezia-client protocolConstants.h + kernel module):
  Jc:    1 <= Jc <= 128                 recommended 3-12
  Jmin:  Jmin < Jmax < 1280             recommended 8-10
  Jmax:  Jmin < Jmax <= 1280            recommended 30-80
  S1:    0, or 12..150; S1 + 56 != S2
  S2:    0, or 12..150
  S3:    0, or 12..64; S3 != S2 + 28    (2.0)
  S4:    0, or 12..64                   (2.0)  see MTU note below
  H1-H4: unique, 5 <= H <= 2147483647
  I1-I5: CPS tags, no separators        (1.5)

Jc/Jmin/Jmax presets (--preset). These are junk packets sent before the
handshake; they need NOT match between server and client, so the preset only
seeds the defaults handed out with new configs:

  mobile   Jc=3, Jmin 30..50, Jmax Jmin+20..Jmin+80   (default)
  default  Jc 3..8, Jmin 8..16, Jmax Jmin+10..80

"mobile" follows bivlked/amneziawg-installer field reports (Tattelecom, Yota,
Tele2, Megafon): Jc 4-8 connected only on the ~3rd attempt, Jc=3 at once. It is
no worse on wired/home networks, so it is the default for all new hosts.

MTU: S4 prefixes every data packet but the kernel module does not account for
it (device.c always sets dev->mtu = 1420). The client MTU must therefore be at
most 1420 - S4. This script emits wgdashboard_peer_mtu accordingly.

Usage:
  python3 scripts/gen-awg-params.py                          # human readable
  python3 scripts/gen-awg-params.py --yaml                   # YAML block
  python3 scripts/gen-awg-params.py --host vpn1              # host_vars block
  python3 scripts/gen-awg-params.py --version 1.0            # legacy param set
  python3 scripts/gen-awg-params.py --preset default         # old Jc/Jmin/Jmax ranges
"""

import argparse
import ipaddress
import pathlib
import random
import re
import sys

IFACE_MTU = 1420  # device.c: ETH_DATA_LEN (1500) - (32 + 8 + 40)

# Client MTU to emit when S4 is enabled. 1420 - S4 is the hard ceiling, but the
# Amnezia reference value of 1376 also survives PPPoE (1492) paths, so it is
# used whenever it fits.
AMNEZIA_REFERENCE_MTU = 1376

H_MIN, H_MAX = 5, 2147483647

# Plausible (domain, A-record) pairs for the synthetic DNS response used as the
# I1 signature. Deliberately NOT the client default (icloud.com -> 77.88.55.55),
# which ships with every default Amnezia installation and is a fingerprint on
# its own.
DNS_POOL = [
    ("www.wikipedia.org", "185.15.59.224"),
    ("detectportal.firefox.com", "34.107.221.82"),
    ("captive.apple.com", "17.253.109.201"),
    ("www.gstatic.com", "142.250.186.67"),
    ("clients3.google.com", "142.250.185.110"),
    ("ocsp.pki.goog", "142.250.185.99"),
    ("ocsp.sectigo.com", "104.18.32.68"),
    ("pool.ntp.org", "162.159.200.123"),
    ("api.github.com", "140.82.121.6"),
    ("registry.npmjs.org", "104.16.24.34"),
    ("pypi.org", "151.101.0.223"),
    ("dl.google.com", "142.250.185.206"),
    ("cdnjs.cloudflare.com", "104.17.24.14"),
    ("www.msftconnecttest.com", "13.107.4.52"),
    ("ajax.googleapis.com", "142.250.185.74"),
    ("unpkg.com", "104.16.123.175"),
    ("archive.ubuntu.com", "185.125.190.83"),
    ("settings-win.data.microsoft.com", "20.42.65.85"),
]

# 0x8180 = response, recursion desired + available, no error (typical recursive
# resolver reply). 0x8580 adds the authoritative-answer bit.
DNS_FLAGS = [0x8180, 0x8580]


def encode_qname(domain: str) -> bytes:
    out = bytearray()
    for label in domain.split("."):
        out.append(len(label))
        out += label.encode("ascii")
    out.append(0)
    return bytes(out)


def decode_qname(body: bytes) -> str | None:
    """Pull the QNAME out of a DNS-shaped CPS body.

    The DNS header is 12 bytes, but the leading 2-byte transaction ID lives in
    the <r 2> tag rather than in <b ...>, so within the body the QNAME starts
    at offset 10. The 0xc00c compression pointer still refers to offset 12 of
    the assembled packet, which is correct on the wire.
    """
    labels: list[str] = []
    i = 10
    try:
        while body[i] != 0:
            length = body[i]
            i += 1
            labels.append(body[i:i + length].decode("ascii"))
            i += length
    except (IndexError, UnicodeDecodeError):
        return None
    return ".".join(labels) or None


def collect_used_cps(inventory: pathlib.Path) -> tuple[set[str], set[str]]:
    """Return (full signatures, domains) already assigned to other hosts.

    The 48 static bytes of the signature are a far stronger selector than the
    H values: reusing a domain across hosts means the payloads differ only in
    the TTL, which is barely a differentiator at all.
    """
    signatures: set[str] = set()
    domains: set[str] = set()
    if not inventory.is_dir():
        return signatures, domains
    line_re = re.compile(r"^\s*amneziawg_i[1-5]\s*:\s*['\"](.+?)['\"]", re.MULTILINE)
    body_re = re.compile(r"<b 0x([0-9a-fA-F]+)>")
    for path in inventory.rglob("*.yml"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for signature in line_re.findall(text):
            signatures.add(signature)
            for hexdata in body_re.findall(signature):
                try:
                    body = bytes.fromhex(hexdata)
                except ValueError:
                    continue
                domain = decode_qname(body)
                if domain:
                    domains.add(domain)
    return signatures, domains


def gen_dns_cps(rng: random.Random, used_domains: set[str] = frozenset()) -> str:
    """Build a CPS signature shaped like a DNS response for a benign domain."""
    pool = [entry for entry in DNS_POOL if entry[0] not in used_domains]
    if not pool:
        print("WARNING: every pooled domain is already used by another host — "
              "extend DNS_POOL, this signature will only differ by its TTL",
              file=sys.stderr)
        pool = DNS_POOL
    domain, addr = rng.choice(pool)
    body = bytearray()
    body += rng.choice(DNS_FLAGS).to_bytes(2, "big")  # flags
    body += (1).to_bytes(2, "big")                    # QDCOUNT
    body += (1).to_bytes(2, "big")                    # ANCOUNT
    body += (0).to_bytes(2, "big")                    # NSCOUNT
    body += (0).to_bytes(2, "big")                    # ARCOUNT
    body += encode_qname(domain)
    body += (1).to_bytes(2, "big")                    # QTYPE  A
    body += (1).to_bytes(2, "big")                    # QCLASS IN
    body += b"\xc0\x0c"                               # NAME pointer to offset 12
    body += (1).to_bytes(2, "big")                    # TYPE   A
    body += (1).to_bytes(2, "big")                    # CLASS  IN
    body += rng.randint(60, 21600).to_bytes(4, "big")  # TTL
    body += (4).to_bytes(2, "big")                    # RDLENGTH
    body += ipaddress.IPv4Address(addr).packed        # RDATA

    # <r 2> supplies a fresh random transaction ID on every packet.
    return f"<r 2><b 0x{body.hex()}>"


def collect_used_headers(inventory: pathlib.Path) -> set[int]:
    """Scan the inventory for H1-H4 values already assigned to other hosts."""
    used: set[int] = set()
    if not inventory.is_dir():
        return used
    pattern = re.compile(r"^\s*amneziawg_h[1-4]\s*:\s*['\"]?(\d+)", re.MULTILINE)
    for path in inventory.rglob("*.yml"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        used.update(int(m) for m in pattern.findall(text))
    return used


def gen_junk(preset: str, rng: random.Random) -> tuple[int, int, int]:
    if preset == "mobile":
        jc = 3
        jmin = rng.randint(30, 50)
        jmax = rng.randint(jmin + 20, jmin + 80)
    else:
        jc = rng.randint(3, 8)
        jmin = rng.randint(8, 16)
        jmax = rng.randint(jmin + 10, 80)
    return jc, jmin, jmax


def generate(version: str, rng: random.Random, used_headers: set[int],
             used_signatures: set[str] = frozenset(),
             used_domains: set[str] = frozenset(),
             preset: str = "mobile") -> dict:
    jc, jmin, jmax = gen_junk(preset, rng)

    s1 = rng.randint(12, 150)
    s2 = rng.randint(12, 150)
    while s1 + 56 == s2:
        s2 = rng.randint(12, 150)

    headers: list[int] = []
    while len(headers) < 4:
        candidate = rng.randint(100_000_000, 2_000_000_000)
        if candidate in used_headers or candidate in headers:
            continue
        headers.append(candidate)

    params = {
        "version": version,
        "jc": jc,
        "jmin": jmin,
        "jmax": jmax,
        "s1": s1,
        "s2": s2,
        "s3": 0,
        "s4": 0,
        "h": headers,
        "i1": "",
    }

    if version in ("1.5", "2.0"):
        # Retry on the off chance the TTL collides too and reproduces a
        # signature byte-for-byte.
        for _ in range(32):
            candidate = gen_dns_cps(rng, used_domains)
            if candidate not in used_signatures:
                params["i1"] = candidate
                break
        else:
            raise RuntimeError("could not generate a unique CPS signature")
    if version == "2.0":
        # S3 == S2 + 28 would make the cookie reply (64 B) the same size as
        # the response (92 B) on the wire.
        s3 = rng.randint(12, 64)
        while s3 == s2 + 28:
            s3 = rng.randint(12, 64)
        params["s3"] = s3
        # Fixed at 12 on purpose: S4 is per-data-packet overhead and directly
        # eats client MTU. Amnezia's own reference config uses 12.
        params["s4"] = 12

    return params


def peer_mtu(params: dict) -> int | None:
    if params["s4"] <= 0:
        return None
    ceiling = IFACE_MTU - params["s4"]
    return min(AMNEZIA_REFERENCE_MTU, ceiling)


def print_plain(p: dict) -> None:
    print(f"Config version: {p['version']}")
    print(f"Jc={p['jc']}  Jmin={p['jmin']}  Jmax={p['jmax']}")
    print(f"S1={p['s1']}  S2={p['s2']}  S3={p['s3']}  S4={p['s4']}"
          f"   (S1+56={p['s1'] + 56}, != S2: {p['s1'] + 56 != p['s2']})")
    if p["s3"]:
        print(f"   (S2+28={p['s2'] + 28}, != S3: {p['s2'] + 28 != p['s3']})")
    for i, h in enumerate(p["h"], start=1):
        print(f"H{i}={h}")
    if p["i1"]:
        print(f"I1={p['i1']}")
    mtu = peer_mtu(p)
    if mtu:
        print(f"\nMTU: S4={p['s4']} -> client MTU ceiling {IFACE_MTU - p['s4']}, "
              f"use {mtu}")


def yaml_lines(p: dict, indent: str = "") -> list[str]:
    out = [
        f'{indent}amneziawg_config_version: "{p["version"]}"',
        f"{indent}amneziawg_jc: {p['jc']}",
        f"{indent}amneziawg_jmin: {p['jmin']}",
        f"{indent}amneziawg_jmax: {p['jmax']}",
        f"{indent}amneziawg_s1: {p['s1']}",
        f"{indent}amneziawg_s2: {p['s2']}",
    ]
    if p["s3"]:
        out.append(f"{indent}amneziawg_s3: {p['s3']}")
    if p["s4"]:
        out.append(f"{indent}amneziawg_s4: {p['s4']}")
    for i, h in enumerate(p["h"], start=1):
        out.append(f"{indent}amneziawg_h{i}: {h}")
    if p["i1"]:
        out.append(f'{indent}amneziawg_i1: "{p["i1"]}"')
    return out


def print_host_block(p: dict, host: str) -> None:
    mtu = peer_mtu(p)
    print("---")
    print(f"## inventory/host_vars/{host}/awg.yml — generated by scripts/gen-awg-params.py")
    print()
    print("## AmneziaWG obfuscation — per-host, overrides group_vars/awg.")
    print("## Every host MUST have its own H1-H4 and I1: shared values mean one")
    print("## leaked client config fingerprints every server that reuses them.")
    print("## Both were checked against the rest of the inventory when generated.")
    print(f"## Config version {p['version']} — requires a client with "
          f"AmneziaWG {p['version']}+ support.")
    for line in yaml_lines(p):
        print(line)
    if mtu:
        print()
        print(f"## S4={p['s4']} is not accounted for in the interface MTU "
              f"({IFACE_MTU}),")
        print(f"## so the ceiling is {IFACE_MTU - p['s4']}. {mtu} is the Amnezia "
              f"reference value,")
        print("## which also survives PPPoE (1492) paths.")
        print(f"wgdashboard_peer_mtu: {mtu}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate per-host AmneziaWG obfuscation parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--yaml", action="store_true",
                        help="output as a plain YAML block")
    parser.add_argument("--host", metavar="FQDN",
                        help="output a ready-to-paste host_vars block")
    parser.add_argument("--version", choices=["1.0", "1.5", "2.0"], default="2.0",
                        help="target config version (default: 2.0)")
    parser.add_argument("--preset", choices=["mobile", "default"], default="mobile",
                        help="Jc/Jmin/Jmax ranges (default: mobile, see docstring)")
    parser.add_argument("--inventory", default=None, metavar="DIR",
                        help="inventory dir scanned for H1-H4 and CPS signatures "
                             "already in use (default: <repo>/ansible/inventory)")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed, for reproducible output in tests")
    args = parser.parse_args()

    inventory = (pathlib.Path(args.inventory) if args.inventory
                 else pathlib.Path(__file__).resolve().parent.parent / "ansible" / "inventory")
    used_headers = collect_used_headers(inventory)
    used_signatures, used_domains = collect_used_cps(inventory)

    rng = random.Random(args.seed)
    params = generate(args.version, rng, used_headers,
                      used_signatures, used_domains, preset=args.preset)

    if args.host:
        print_host_block(params, args.host)
    elif args.yaml:
        print("\n".join(yaml_lines(params)))
    else:
        print_plain(params)
        if used_headers or used_domains:
            print(f"\nExcluded, already in use in {inventory}:")
            print(f"  {len(used_headers)} H-value(s)")
            if used_domains:
                print(f"  {len(used_domains)} CPS domain(s): "
                      f"{', '.join(sorted(used_domains))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

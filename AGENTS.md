# AGENTS.md

Public repository. Anything committed here is visible to everyone.

- Personal data lives only in gitignored files: `ansible/inventory/hosts.yml`,
  `group_vars/all/{local,vault}.yml`, `host_vars/`, `ansible/.vault_pass`.
  Tracked files hold only `*.example` with placeholder values.
- Examples use documentation ranges only: `203.0.113.0/24`, `198.51.100.0/24`,
  `example.com`. Never real IPs, domains, hostnames, providers, keys, hashes,
  obfuscation parameters (`H1`-`H4`, `I1`) or tunnel subnets of real servers.
- Before every commit: `scripts/check-secrets.sh` and `gitleaks git --staged .`
  Both must pass. Do not weaken `check-secrets.sh` to make a commit pass.
- Roles are pinned to commit SHAs in `ansible/requirements.yml`. Bump a pin
  only to a commit already tested on a real server.
- `scripts/gen-awg-params.py`: keep `DNS_POOL` as is unless there is a reason;
  never reuse domains from another project's pool.
- Docs: Russian in `docs/ru/` (English later in `docs/en/`, same file names).
  Code, comments, commits: English.

## Pitfalls found in testing

- WGDashboard caches the interface params: after `awg.yml` changes it keeps
  issuing configs with the old ones until `wg-dashboard` restarts. `vpn.yml`
  does that restart (checksum of `awg0.conf` before/after the role). Keep it.
- The `amneziawg` role never rewrites `awg0.conf` while it has peers, it only
  prints `WARNING: [Interface] params differ`. Changing params = delete every
  peer first (documented in `docs/ru/04`).
- Login check is `ssh <user>@<ip> sudo true`, not `sudo -v`: `-v` asks for a
  password because the user is also in the `sudo` group.
- Firewall bans only affect closed ports: public ports (SSH, AWG) are accepted
  before the ban check. Never document "banned = SSH is cut off".
- Changing `awg_client_endpoint` or `awg_local_dns` is picked up by the role
  (it restarts the panel). Old peers keep their DNS, Endpoint follows the
  setting on re-download.

## Testing without a VPS (Lima)

- Two VMs, Ubuntu 24.04, same network so the client reaches the server:
  `limactl start --name=awg-server --network=lima:user-v2 --mount-none template:ubuntu-24.04`
  (start them one after another: parallel starts race on the Lima SSH key).
- Make the server look like a fresh VPS: root password + `PermitRootLogin yes`,
  `PasswordAuthentication yes` in `/etc/ssh/sshd_config.d/00-vps.conf`.
- Inventory: `ansible_host: 127.0.0.1` + the VM SSH port from `limactl list`;
  `awg_client_endpoint` = the server IP on the Lima network. A throwaway key
  and known_hosts go into `host_vars/<host>/test.yml`, plus
  `sshd_allow_users: [<admin_user>, lima]`, otherwise `limactl shell` stops
  working after `make ssh`.
- Lima forwards guest port 10086 to the host by itself, so `make panel` binds
  `[::1]:10086`. Use that address when testing the tunnel.
- Client test: install `amneziawg` from the PPA on the client VM and run the
  full-tunnel test detached (`setsid nohup`), it cuts the SSH session.
- Tested so far: 1 vCPU / 1 GB without swap, configs 1.0 / 1.5 / 2.0, ports
  27015 / 443 / 51820, `CHECK=1`, reboot, bans, re-runs with `changed=0`.
  Not tested: amd64, a phone on a mobile carrier.
- Delete the VMs and every test file afterwards.

## Screenshots

- Only from a throwaway WGDashboard (`ghcr.io/wgdashboard/wgdashboard:<role
  version>` in Docker, bound to 127.0.0.1) with made-up data; blur QR codes.
- Retake them when the WGDashboard version in the role changes.

## Docs style

- GitHub alerts (`> [!NOTE]` / `TIP` / `IMPORTANT` / `WARNING` / `CAUTION`):
  at most two in a row, only where a reader can get it wrong.
  NOTE = good to know, TIP = optional advice, IMPORTANT = will not work
  without it, WARNING = can break things, CAUTION = irreversible or unsafe.
- Changing a heading changes its anchor: update every link to it.
- Client versions come from the bivlked/amneziawg-installer table and carry
  its date; update the date together with the numbers.

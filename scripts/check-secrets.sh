#!/usr/bin/env bash
## Refuse to commit personal data. Run by pre-commit and by CI.
## Usage: check-secrets.sh [file...]   (no args = every tracked file)
set -euo pipefail

files=()
if [[ $# -eq 0 ]]; then
  while IFS= read -r f; do files+=("$f"); done < <(git ls-files)
else
  files=("$@")
fi
[[ ${#files[@]} -gt 0 ]] || exit 0

fail=0
err() { echo "BLOCKED: $1" >&2; fail=1; }

for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  case "$f" in
    scripts/check-secrets.sh) continue ;;
  esac

  # Personal files must stay local, only *.example is tracked
  case "$f" in
    */hosts.yml|*/local.yml|*/vault.yml|*/host_vars/*|*.vault_pass)
      err "$f: personal file, keep it local (it is in .gitignore)" ;;
  esac

  # Private keys of any kind
  if grep -qE -- '-----BEGIN [A-Z ]*PRIVATE KEY-----' "$f"; then
    err "$f: private key"
  fi
  # WireGuard / AmneziaWG keys (base64, 44 chars) next to a key field
  if grep -qiE '(PrivateKey|PresharedKey|private_key)[^A-Za-z0-9]+[A-Za-z0-9+/]{42,43}=' "$f"; then
    err "$f: WireGuard key"
  fi
  # Password hashes
  if grep -qE '\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}|\$6\$[^$ ]+\$[./A-Za-z0-9]{86}' "$f"; then
    err "$f: password hash"
  fi
  # Real public SSH keys (examples use 'replace-me' / '...')
  if grep -E '(ssh-ed25519|ssh-rsa|ecdsa-sha2-[a-z0-9]+) AAAA[A-Za-z0-9+/]{40,}' "$f" | grep -vqE 'replace-me|\.\.\.'; then
    err "$f: SSH public key (identifies you)"
  fi
  # Vault vars with a value in a non-example file
  if [[ "$f" == *.yml || "$f" == *.yaml ]] && grep -qE '^[[:space:]]*vault_[a-z0-9_]+:[[:space:]]*["'\'']?[^"'\''{ ]' "$f" \
     && ! grep -q '^\$ANSIBLE_VAULT' "$f"; then
    err "$f: vault_* value in plain text"
  fi
  # Obfuscation parameters belong to one server only
  if [[ "$f" == *.yml ]] && grep -qE '^[[:space:]]*amneziawg_(h[1-4]|i[1-5]):[[:space:]]*["'\'']?[0-9<]' "$f"; then
    err "$f: AmneziaWG obfuscation parameters (per-server, keep in host_vars/)"
  fi
  # Public IPv4 outside documentation ranges in inventory files
  if [[ "$f" == ansible/inventory/* ]]; then
    while read -r ip; do
      case "$ip" in
        10.*|127.*|192.168.*|0.0.0.0|1.1.1.1|8.8.8.8|203.0.113.*|198.51.100.*|192.0.2.*) ;;
        *) err "$f: IP $ip (use 203.0.113.x / 198.51.100.x in examples)" ;;
      esac
    done < <(grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' "$f" | sort -u)
  fi
done

exit $fail

#!/usr/bin/env bash
## Print a bcrypt hash for WGDashboard / AdGuard Home. The password itself is
## read without echo and never written anywhere.
set -euo pipefail

read -r -s -p "Password: " pass1; echo
read -r -s -p "Repeat:   " pass2; echo
if [[ "$pass1" != "$pass2" ]]; then
  echo "Passwords do not match" >&2
  exit 1
fi
if [[ ${#pass1} -lt 12 ]]; then
  echo "Use at least 12 characters" >&2
  exit 1
fi

if python3 -c 'import bcrypt' 2>/dev/null; then
  PASS="$pass1" python3 -c 'import bcrypt, os; print(bcrypt.hashpw(os.environ["PASS"].encode(), bcrypt.gensalt()).decode())'
elif command -v htpasswd >/dev/null 2>&1; then
  printf '%s' "$pass1" | htpasswd -B -C 12 -n -i "" | head -n1 | cut -d: -f2
else
  echo "Need python3 bcrypt (pip3 install bcrypt) or htpasswd (apache2-utils)" >&2
  exit 1
fi

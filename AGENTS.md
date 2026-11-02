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

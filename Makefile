## Run every target from the repository root: make <target> HOST=<host>
## HOST is the name from ansible/inventory/hosts.yml (e.g. vpn1).
##
## Optional:
##   CHECK=1     dry run: show what would change, change nothing (--check --diff)
##   ASK_PASS=1  init only: log in as root with a password instead of a key
##   UPGRADE=    init only: full (default, incl. kernel) | safe | none
##   VERSION=    params only: AmneziaWG config version 2.0 (default) | 1.5 | 1.0

SHELL := /bin/bash
ANSIBLE_DIR := ansible
INVENTORY := $(ANSIBLE_DIR)/inventory
PLAYBOOK := cd $(ANSIBLE_DIR) && ansible-playbook
LIMIT = --limit $(HOST)
EXTRA = $(if $(CHECK),--check --diff)
VERSION ?= 2.0
UPGRADE ?= full

.PHONY: help install setup params hash vault-encrypt vault-edit vault-view \
        init ssh vpn firewall dns all panel check-host

help:
	@echo "Setup (once):"
	@echo "  make install                 install ansible roles and collections"
	@echo "  make setup                   create local config files from examples"
	@echo "  make hash                    bcrypt hash of a password (for vault.yml)"
	@echo "  make vault-encrypt           encrypt vault.yml"
	@echo "  make params HOST=vpn1        generate this server's obfuscation parameters"
	@echo ""
	@echo "Server (in this order):"
	@echo "  make init HOST=vpn1          base system, admin user (as root)"
	@echo "  make ssh HOST=vpn1           disable root/password login"
	@echo "  make vpn HOST=vpn1           AmneziaWG + firewall + WGDashboard"
	@echo "  make dns HOST=vpn1           AdGuard Home (local DNS for clients)"
	@echo "  make all HOST=vpn1           all four above"
	@echo ""
	@echo "Day to day:"
	@echo "  make panel HOST=vpn1         SSH tunnel to WGDashboard -> http://localhost:10086"
	@echo "  make firewall HOST=vpn1      re-apply firewall rules only"
	@echo "  add CHECK=1 to any server target for a dry run"

check-host:
	@test -n "$(HOST)" || { echo "HOST is not set: make $(MAKECMDGOALS) HOST=vpn1"; exit 1; }

## --- setup ------------------------------------------------------------------

install:
	cd $(ANSIBLE_DIR) && ansible-galaxy role install -r requirements.yml --force
	cd $(ANSIBLE_DIR) && ansible-galaxy collection install -r requirements.yml

setup:
	@for f in $(INVENTORY)/hosts.yml $(INVENTORY)/group_vars/all/local.yml $(INVENTORY)/group_vars/all/vault.yml; do \
		if [ -e "$$f" ]; then echo "exists:  $$f"; else cp "$$f.example" "$$f" && echo "created: $$f"; fi; \
	done
	@if [ -e $(ANSIBLE_DIR)/.vault_pass ]; then echo "exists:  $(ANSIBLE_DIR)/.vault_pass"; \
	else umask 077 && openssl rand -base64 32 > $(ANSIBLE_DIR)/.vault_pass && echo "created: $(ANSIBLE_DIR)/.vault_pass (keep a copy in your password manager)"; fi

params: check-host
	@f=$(INVENTORY)/host_vars/$(HOST)/awg.yml; \
	if [ -e "$$f" ]; then \
		echo "$$f already exists. New parameters break every issued client config."; \
		echo "Delete it by hand only if no clients exist yet."; exit 1; \
	fi; \
	mkdir -p $(INVENTORY)/host_vars/$(HOST) && \
	python3 scripts/gen-awg-params.py --host $(HOST) --version $(VERSION) > "$$f" && \
	echo "created: $$f"

hash:
	@scripts/hash-password.sh

vault-encrypt:
	cd $(ANSIBLE_DIR) && ansible-vault encrypt inventory/group_vars/all/vault.yml

vault-edit:
	cd $(ANSIBLE_DIR) && ansible-vault edit inventory/group_vars/all/vault.yml

vault-view:
	cd $(ANSIBLE_DIR) && ansible-vault view inventory/group_vars/all/vault.yml

## --- server -----------------------------------------------------------------

init: check-host
	$(PLAYBOOK) playbooks/init.yml $(LIMIT) -e ansible_user=root -e init_upgrade_mode=$(UPGRADE) $(if $(ASK_PASS),--ask-pass) $(EXTRA)

ssh: check-host
	$(PLAYBOOK) playbooks/ssh.yml $(LIMIT) $(EXTRA)

vpn: check-host
	$(PLAYBOOK) playbooks/vpn.yml $(LIMIT) $(EXTRA)

firewall: check-host
	$(PLAYBOOK) playbooks/firewall.yml $(LIMIT) $(EXTRA)

dns: check-host
	$(PLAYBOOK) playbooks/dns.yml $(LIMIT) $(EXTRA)

all: init ssh vpn dns

panel: check-host
	@cd $(ANSIBLE_DIR) && \
	ip=$$(ansible-inventory --host $(HOST) | python3 -c 'import json,sys; print(json.load(sys.stdin)["ansible_host"])') && \
	user=$$(ansible-inventory --host $(HOST) | python3 -c 'import json,sys; print(json.load(sys.stdin)["admin_user"])') && \
	echo "WGDashboard: http://localhost:10086  (Ctrl+C to close the tunnel)" && \
	ssh -N -L 10086:127.0.0.1:10086 "$$user@$$ip"

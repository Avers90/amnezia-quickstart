<p align="center">
  🇷🇺 <b>Русский</b> | 🇬🇧 English (скоро)
</p>

# amnezia-quickstart

Свой VPN-сервер на [AmneziaWG](https://github.com/amnezia-vpn/amneziawg-linux-kernel-module)
за несколько команд: Ansible ставит всё сам, вы правите пару файлов с настройками.

Что получится:

- **AmneziaWG**: WireGuard с маскировкой трафика, которую сложнее заблокировать по DPI
- **[WGDashboard](https://github.com/WGDashboard/WGDashboard)**: веб-панель, где вы создаёте клиентов и скачиваете конфиги или QR-коды
- **Firewall** (iptables): открыты только SSH и порт VPN, сканеры портов автоматически банятся
- **[AdGuard Home](https://github.com/AdguardTeam/AdGuardHome)** (по желанию): свой DNS для клиентов VPN с блокировкой рекламы и трекеров
- Защищённый вход: отдельный пользователь, только SSH-ключ, root отключён

Всё ставится ролями из [Avers90/ansible-role-*](https://github.com/Avers90?tab=repositories&q=ansible-role).

## Два варианта

| | Простой | Полный |
|---|---|---|
| AmneziaWG + WGDashboard | ✅ | ✅ |
| Firewall + NAT | ✅ (без него у клиентов нет интернета) | ✅ |
| Защищённый SSH | ✅ | ✅ |
| AdGuard Home (свой DNS) | — | ✅ |
| Что поменять | `awg_local_dns: false` | `awg_local_dns: true` |

Firewall есть в обоих вариантах: он не только закрывает лишние порты, но и
выпускает трафик клиентов в интернет (NAT).

## Быстрый старт

Нужно: VPS на **Ubuntu 24.04** (от 1 ГБ RAM), компьютер с macOS, Linux или
Windows + WSL. Подробности по каждому шагу ниже, в [инструкции](#инструкция).

```bash
git clone https://github.com/Avers90/amnezia-quickstart.git
cd amnezia-quickstart

make install                # роли и коллекции Ansible
make setup                  # создаёт личные файлы настроек из примеров
```

Заполните три файла (они в `.gitignore`, в git не попадут):

| Файл | Что вписать |
|---|---|
| `ansible/inventory/hosts.yml` | IP сервера |
| `ansible/inventory/group_vars/all/local.yml` | имя пользователя, **публичный** SSH-ключ, нужен ли свой DNS, домен для клиентов ([зачем](docs/ru/04-amneziawg-wgdashboard.md#адрес-сервера-в-конфигах-домен-а-не-ip)) |
| `ansible/inventory/group_vars/all/vault.yml` | хеши паролей от `make hash` |

### Пароли

Пароли для WGDashboard и AdGuard Home задаются заранее: `make hash` превращает
пароль в хеш, хеш сохраняется в `vault.yml`. При установке панели сразу
получают ваш логин (`admin_user`) и пароль, без мастера первого запуска и
без `admin/admin`. Можно один пароль на оба, лучше разные.

Ansible ничего не спрашивает: vault открывается ключом из `ansible/.vault_pass`,
вход на сервер по SSH-ключу, sudo без пароля. Исключение: `make init
ASK_PASS=1`, если провайдер дал только пароль root.

```bash
make hash                   # дважды: пароль для WGDashboard и для AdGuard Home
make vault-encrypt          # зашифровать vault.yml
make params HOST=vpn1       # уникальные параметры маскировки для этого сервера

make init HOST=vpn1         # базовая система (под root)
ssh vpnadmin@<IP> sudo true # проверить вход под новым пользователем!
make ssh HOST=vpn1          # отключить вход под root и по паролю
make vpn HOST=vpn1          # AmneziaWG + firewall + WGDashboard
make dns HOST=vpn1          # AdGuard Home (только для полного варианта)

make panel HOST=vpn1        # открыть панель: http://localhost:10086
```

## Инструкция

1. [Подготовка](docs/ru/01-preparation.md): VPS, SSH-ключ, Ansible
2. [Базовая настройка сервера](docs/ru/02-base-system.md)
3. [Защита SSH](docs/ru/03-ssh.md)
4. [AmneziaWG и WGDashboard](docs/ru/04-amneziawg-wgdashboard.md)
5. [Firewall](docs/ru/05-firewall.md)
6. [Свой DNS: AdGuard Home](docs/ru/06-adguard-dns.md)
7. [Клиенты](docs/ru/07-clients.md)
8. [Если что-то не работает](docs/ru/08-troubleshooting.md)
9. [Секреты и безопасность репозитория](docs/ru/09-secrets.md)

## Структура

```
Makefile                    все команды: make help
ansible/
  inventory/
    hosts.yml.example       → hosts.yml          (ваш сервер)
    group_vars/all/
      main.yml              общие настройки (пользователь, sudo, ssh)
      local.yml.example     → local.yml          (ваши личные настройки)
      vault.yml.example     → vault.yml          (пароли, шифруется)
    group_vars/awg/main.yml настройки VPN, firewall, панели, DNS
    host_vars/<host>/awg.yml параметры маскировки (make params)
  playbooks/                init, ssh, vpn, firewall, dns
  requirements.yml          роли, закреплённые на конкретных коммитах
scripts/
  gen-awg-params.py         генератор параметров маскировки
  hash-password.sh          bcrypt-хеш пароля
  check-secrets.sh          защита от коммита личных данных
```

## Лицензия

[MIT](LICENSE)

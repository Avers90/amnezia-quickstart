# 1. Подготовка

## VPS

- **ОС:** Ubuntu 24.04 (другие версии не проверялись)
- **Ресурсы:** от 1 vCPU и 1 ГБ RAM, swap не нужен. Проверено на 1 vCPU и
  1 ГБ без swap: установка проходит, самый долгий шаг (сборка веб-интерфейса
  WGDashboard в `make vpn`) занимает около 7 минут
- **Сеть:** публичный IPv4
- **Страна:** вне РФ. Перед покупкой полезно убедиться, что IP провайдера не
  заблокирован у вашего мобильного оператора: некоторые подсети хостеров
  режут целиком

От провайдера нужны IP и пароль root (или вход под root по ключу).

## SSH-ключ

Если ключа ещё нет:

```bash
ssh-keygen -t ed25519 -C "vpn"
```

Появятся два файла:

- `~/.ssh/id_ed25519`: **приватный** ключ, никому не передаётся, в репозиторий не кладётся
- `~/.ssh/id_ed25519.pub`: **публичный**, его содержимое вписывается в `local.yml`

## Ansible

Нужны Ansible (2.15+), `make`, `git`, Python 3, модуль `netaddr` и
`htpasswd` (для `make hash`; на macOS уже есть).

**macOS:**

```bash
brew install ansible
```

**Ubuntu / Debian / Windows + WSL:**

```bash
sudo apt install -y pipx make git apache2-utils
pipx install --include-deps ansible
pipx inject ansible netaddr
pipx ensurepath   # потом перезапустить терминал
```

На Windows всё делается внутри WSL (Ubuntu). Ключ тоже создаётся там.

Проверка:

```bash
ansible --version
```

## Репозиторий

```bash
git clone https://github.com/Avers90/amnezia-quickstart.git
cd amnezia-quickstart
make install    # роли → ansible/roles/, коллекции → ~/.ansible/
make setup      # личные файлы из примеров + пароль от vault
```

`make setup` создаёт:

| Файл | Зачем |
|---|---|
| `ansible/inventory/hosts.yml` | список серверов |
| `ansible/inventory/group_vars/all/local.yml` | ваши настройки |
| `ansible/inventory/group_vars/all/vault.yml` | хеши паролей (будет зашифрован) |
| `ansible/.vault_pass` | случайный пароль, которым шифруется `vault.yml` |

Все четыре в `.gitignore`. **Сохраните содержимое `ansible/.vault_pass` в
менеджер паролей**: без него `vault.yml` не расшифровать.

## Список серверов

`ansible/inventory/hosts.yml`:

```yaml
all:
  children:
    awg:
      hosts:
        vpn1:
          ansible_host: 203.0.113.10   # IP вашего VPS
```

`vpn1` — просто ваше название сервера. Оно используется в командах
(`make vpn HOST=vpn1`) и как имя папки `host_vars/vpn1/`. Серверов может быть
несколько, у каждого своё название.

Дальше: [2. Базовая настройка сервера](02-base-system.md)

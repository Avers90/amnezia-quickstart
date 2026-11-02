# 2. Базовая настройка сервера

## Настройки

`ansible/inventory/group_vars/all/local.yml`:

```yaml
admin_user: "vpnadmin"            # ваш пользователь на сервере (не root)

admin_ssh_keys:                   # содержимое ~/.ssh/id_ed25519.pub
  - "ssh-ed25519 AAAAC3Nza... you@laptop"

awg_local_dns: true               # свой DNS (AdGuard Home), см. раздел 6
```

Если не уверены насчёт `awg_local_dns`, оставьте `true`. Это нужно решить до
создания первого клиента: DNS прописывается в конфиг клиента при его создании.

## Запуск

Вход под root по ключу (если провайдер добавил ваш ключ):

```bash
make init HOST=vpn1
```

Вход под root по паролю (нужен `sshpass`: `brew install sshpass` или
`apt install sshpass`):

```bash
make init HOST=vpn1 ASK_PASS=1
```

Что происходит:

1. Установка Python, если его нет
2. `apt upgrade`, включая ядро. Это 5–20 минут. Быстрее, без ядра:
   `UPGRADE=safe`; совсем без обновлений: `UPGRADE=none`
3. Имя хоста, часовой пояс (по умолчанию Europe/Moscow, меняется через
   `common_timezone` в `local.yml`), настройки ядра для VPN (BBR, буферы,
   conntrack)
4. Пользователь `admin_user` с вашим ключом и sudo без пароля
5. Перезагрузка, если обновилось ядро

## Проверка: обязательно

```bash
ssh vpnadmin@203.0.113.10 sudo true
```

Команда должна пройти без запроса пароля. Если не прошла, **не переходите к
следующему шагу**: после него root зайти уже не сможет.

Дальше: [3. Защита SSH](03-ssh.md)

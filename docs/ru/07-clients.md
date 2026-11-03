# 7. Клиенты

## Приложения

Подходит любое из двух:

| Приложение | Платформы | Конфиг 2.0 (по умолчанию) | Где взять |
|---|---|---|---|
| Amnezia VPN | Windows, macOS, Linux, Android, iOS | с версии 4.8.12.7 | [amnezia.org](https://amnezia.org) |
| AmneziaWG (лёгкий клиент) | Windows | с версии 2.0.0 | [GitHub](https://github.com/amnezia-vpn/amneziawg-windows-client/releases) |
| AmneziaWG (лёгкий клиент) | Android | актуальная | [Google Play](https://play.google.com/store/apps/details?id=org.amnezia.awg) · [GitHub](https://github.com/amnezia-vpn/amneziawg-android/releases) |
| AmneziaWG (лёгкий клиент) | iOS, macOS | актуальная | [App Store](https://apps.apple.com/app/amneziawg/id6478942365) |

AmneziaWG для iOS есть и в российском App Store, Amnezia VPN там нет
(данные на 15 октября 2026). На iPhone с российским аккаунтом берите
AmneziaWG.

Обычный WireGuard **не подойдёт**: он не понимает параметры маскировки.

> [!TIP]
> Старое приложение с конфигом 2.0 просто не подключится, без понятной
> ошибки. Если обновиться нельзя, используйте конфиг версии 1.0
> ([раздел 4](04-amneziawg-wgdashboard.md#версия-конфига)). Свежие данные по
> клиентам: [таблица в bivlked/amneziawg-installer](https://github.com/bivlked/amneziawg-installer/blob/main/ADVANCED.md#client-gen-adv).

## Подключение

1. В WGDashboard создайте клиента (peer) для каждого устройства, по шагам со
   скриншотами в [разделе 4](04-amneziawg-wgdashboard.md#первый-клиент)
2. Скачайте `.conf` или откройте QR-код. QR-кодов два: верхний для
   AmneziaWG, нижний для AmneziaVPN
3. В приложении: «Добавить» → «Из файла» или «Сканировать QR»

## Как передавать конфиг

> [!CAUTION]
> В конфиге лежит **приватный ключ** клиента. Любой, у кого есть файл, может
> подключиться к вашему серверу.

Поэтому:

- передавайте лично или через мессенджер с шифрованием, потом удалите сообщение
- не выкладывайте конфиг в открытые чаты и облака
- если конфиг утёк, удалите этого клиента в панели и создайте нового

## Проверка

После подключения:

- <https://ifconfig.me> показывает IP сервера
- при своём DNS: в AdGuard Home в «Журнале запросов» появились запросы с
  адреса клиента (`10.66.0.x`)

## Запасной порт

Если не подключается через мобильного оператора, но работает через Wi-Fi,
попробуйте в конфиге поменять порт:

```ini
Endpoint = 203.0.113.10:443
```

Подробнее: [раздел 5](05-firewall.md#запасные-порты) и [раздел 8](08-troubleshooting.md).

Дальше: [8. Если что-то не работает](08-troubleshooting.md)

# 🎨 attheme → tdesktop converter

<div align="center">

**Конвертер тем Telegram из Android (.attheme) в Desktop (.tdesktop-theme)**

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0-blueviolet)]()

</div>

---

## Что это?

Скрипт берёт вашу Android-тему Telegram (`.attheme`) и создаёт из неё полноценную тему для Telegram Desktop (`.tdesktop-theme`). Поддерживает Material Design 3 (Monet), извлечение встроенных обоев и все 362 параметра цветовой схемы Desktop.

## Возможности

- **Полная конвертация** — 362 параметра Desktop-темы, маппинг из Android-переменных
- **Извлечение оригинального фона** — если в `.attheme` встроены обои (JPEG/PNG), они будут использованы
- **Автогенерация фона** — если обоев нет, создаётся градиент в цветах темы
- **Material Design 3** — встроенная палитра Monet (Neutral1/2, Accent1/2/3)
- **Умный парсинг цветов** — hex, ARGB, десятичные, ссылки на переменные, модификаторы `(a=80)`, `(l=70)`
- **Интерактивный режим** — запустите без аргументов, скрипт сам найдёт `.attheme` файлы
- **CLI** — полноценный интерфейс командной строки для автоматизации

## Быстрый старт

```bash
# Установите зависимость (необязательно — нужна только для генерации фона)
pip install Pillow

# Самый простой способ — просто запустите:
python attheme_to_tdesktop.py

# Или укажите файл напрямую:
python attheme_to_tdesktop.py MyTheme.attheme

# С кастомным именем выхода:
python attheme_to_tdesktop.py MyTheme.attheme -o CoolTheme.tdesktop-theme
```

## Использование

### Интерактивный режим

Просто запустите скрипт без аргументов — он найдёт все `.attheme` файлы в текущей папке и предложит выбрать:

```
$ python attheme_to_tdesktop.py

Найдены .attheme файлы в текущей папке:
  1) Monet_Dark.attheme  (48 КБ)
  2) Monet_Light.attheme (45 КБ)
  0) Ввести путь вручную

  Выберите файл [1-2, 0]: 1

🎨 Конвертация Android → Desktop темы
  ℹ Входной файл:  Monet_Dark.attheme
  ℹ Выходной файл: Monet_Dark.tdesktop-theme
  ✓ Загружено 187 параметров цвета
  ✓ Извлечён оригинальный фон из темы (124 КБ)
  ✓ Тема: Monet_Dark.tdesktop-theme  (130.2 КБ)
```

### CLI

```
usage: attheme_to_tdesktop [-h] [-o OUTPUT] [--no-bg] [--extract-bg FILE]
                           [--list-colors] [-v]
                           [input]
```

| Аргумент | Описание |
|---|---|
| `input` | Путь к `.attheme` файлу (необязательный — спросит интерактивно) |
| `-o`, `--output` | Путь к выходному файлу |
| `--no-bg` | Не добавлять фоновое изображение |
| `--extract-bg FILE` | Только извлечь обои из `.attheme` в файл |
| `--list-colors` | Показать все цвета из `.attheme` и выйти |
| `-v`, `--version` | Версия |

### Примеры

```bash
# Конвертация с автоматическим именем
python attheme_to_tdesktop.py Monet_Dark.attheme

# Без фона
python attheme_to_tdesktop.py theme.attheme --no-bg

# Извлечь только обои
python attheme_to_tdesktop.py theme.attheme --extract-bg wallpaper.jpg

# Посмотреть все цвета
python attheme_to_tdesktop.py theme.attheme --list-colors
```

## Установка темы

1. Скачайте созданный `.tdesktop-theme` файл
2. Откройте **Telegram Desktop**
3. Перетащите файл в окно Telegram
4. Нажмите **Apply theme**

## Как работает

### Формат `.attheme`

Android-тема — это текстовый файл с парами `ключ=значение`, где значения могут быть:

| Формат | Пример |
|---|---|
| Hex | `#1a1a1a` |
| ARGB число | `-14643754` |
| Hex с суффиксом | `-14643754h` |
| Material Design | `n1_900`, `a1_200`, `mWhite` |
| С модификатором | `n1_800(a=80)`, `primaryDark(l=70)` |
| Ссылка | `windowBackgroundWhite` |

Дополнительно, после маркера `WPS` может быть встроено JPEG/PNG изображение обоев (до маркера `WPE`).

### Формат `.tdesktop-theme`

Desktop-тема — это ZIP-архив, содержащий:
- `colors.tdesktop-theme` — текстовый файл с цветами (`параметр: значение;`)
- `background.jpg` / `background.png` — фоновое изображение (опционально)

### Маппинг цветов

Основные соответствия Android → Desktop:

| Android | Desktop |
|---|---|
| `windowBackgroundWhite` | `windowBg` |
| `chat_inBubble` | `msgInBg` |
| `chat_outBubble` | `msgOutBg` |
| `chats_name` | `dialogsNameFg` |
| `chats_menuBackground` | `dialogsBg` |
| `actionBarDefault` | `topBarBg` |
| `chat_messagePanelBackground` | `historyComposeAreaBg` |
| `chat_emojiPanelBackground` | `emojiPanBg` |

## Требования

- **Python 3.6+**
- **Pillow** — только для генерации градиентного фона (если в `.attheme` уже есть обои, Pillow не нужен)

```bash
pip install Pillow
```

## Известные ограничения

- Не все Android-параметры имеют прямые аналоги в Desktop — некоторые цвета интерполируются
- Модификатор `(l=X)` (lightness) пока игнорируется — берётся базовый цвет
- Если в теме нет встроенных обоев и Pillow не установлен — тема будет без фона

## Лицензия

[MIT](LICENSE) — используйте свободно.

## Ссылки

- [Telegram Desktop Themes](https://github.com/telegramdesktop/tdesktop)
- [Material Design 3 Color System](https://m3.material.io/styles/color/the-color-system/key-colors-tones)
- [Telegram Android Themes](https://t.me/themes)

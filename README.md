# Android Telegram Theme to Desktop Converter

Конвертер тем Telegram из Android формата (`.attheme`) в Desktop формат (`.tdesktop-theme`).

## 🎨 Возможности

- ✅ Конвертация всех цветов из Android темы в Desktop формат
- ✅ Поддержка Material Design 3 цветовой палитры (Monet)
- ✅ Автоматическое создание фонового изображения с градиентами
- ✅ Полная поддержка всех 362 параметров Desktop темы
- ✅ Обработка различных форматов цветов (hex, ARGB, ссылки на переменные)

## 📋 Требования

```bash
pip install Pillow
```

## 🚀 Использование

### Базовое использование

```bash
python attheme_to_tdesktop.py
```

По умолчанию скрипт ищет файл `Monet_Dark.attheme` в текущей директории и создаёт `Monet_Dark.tdesktop-theme`.

### Использование с параметрами

Отредактируйте последние строки скрипта:

```python
if __name__ == '__main__':
    attheme_path = 'путь/к/вашей/теме.attheme'
    output_path = 'выходная_тема.tdesktop-theme'
    
    create_desktop_theme(attheme_path, output_path)
```

## 📦 Что создаётся

Скрипт создаёт ZIP-архив `.tdesktop-theme`, содержащий:

1. **colors.tdesktop-theme** - файл с цветовой схемой (~12 КБ)
   - 362 параметра цветовой схемы
   - Полная совместимость с Telegram Desktop
   
2. **background.png** - фоновое изображение (1024x768)
   - Градиент в цветах вашей темы
   - Тонкие акцентные элементы

## 🎯 Установка темы

1. Скачайте созданный файл `.tdesktop-theme`
2. Откройте Telegram Desktop
3. Перетащите файл в окно Telegram
4. Нажмите "Apply theme"

## 🔧 Как работает конвертер

### Парсинг цветов

Скрипт поддерживает различные форматы цветов из Android тем:

- **Hex цвета**: `#1a1a1a`
- **ARGB числа**: `-14643754h`
- **Десятичные**: `2147483647`
- **Material Design**: `n1_900`, `a1_200`, `mWhite`
- **С прозрачностью**: `n1_800(a=80)`, `primaryDark(l=70)`

### Цветовая палитра Material Design 3

Скрипт включает полную палитру Material Design 3:

- `n1_*` - Neutral1 (основные серые)
- `n2_*` - Neutral2 (вторичные серые)
- `a1_*` - Accent1 (основной акцент)
- `a2_*` - Accent2 (вторичный акцент)
- `a3_*` - Accent3 (третичный акцент)
- `m*` - Предопределённые Material цвета

### Маппинг цветов

Автоматическое сопоставление Android параметров с Desktop:

| Android | Desktop |
|---------|---------|
| `windowBackgroundWhite` | `windowBg` |
| `chat_inBubble` | `msgInBg` |
| `chat_outBubble` | `msgOutBg` |
| `chats_name` | `dialogsNameFg` |
| И т.д. |

## 📝 Пример

### Входная тема (Android)
```
chat_inBubble=n1_800(l=70)
chat_outBubble=a1_200
windowBackgroundWhite=n1_900
```

### Выходная тема (Desktop)
```
msgInBg: #2b2930;
msgOutBg: #b69df8;
windowBg: #1a1a1a;
```

## 🎨 Кастомизация фонового изображения

Скрипт автоматически создаёт фоновое изображение на основе цветов темы:

- Базовый градиент от основного цвета фона
- Тонкие акцентные круги в цвете `primaryColor`
- Разрешение 1024x768
- Оптимизация размера

Вы можете изменить параметры в функции создания фона:

```python
width, height = 1920, 1080  # Изменить разрешение
alpha = (1 - dist / radius1) * 0.05  # Изменить интенсивность акцента
```

## 🐛 Известные ограничения

- Не все специфичные для Android параметры имеют прямые аналоги в Desktop версии
- Некоторые цвета могут требовать ручной настройки для идеального соответствия
- Фоновое изображение создаётся автоматически (не копируется из Android темы)

## 🤝 Вклад

Приветствуются любые улучшения! Если вы нашли баг или хотите добавить функцию:

1. Fork репозиторий
2. Создайте feature branch
3. Commit изменения
4. Push в branch
5. Создайте Pull Request

## 📄 Лицензия

MIT License - используйте свободно!

## 🙏 Благодарности

- Telegram за открытую экосистему тем
- Material Design 3 за цветовую систему
- Всем создателям тем для Telegram

## 📚 Полезные ссылки

- [Telegram Desktop Themes Documentation](https://github.com/telegramdesktop/tdesktop/blob/dev/docs/building-cmake.md)
- [Material Design 3 Colors](https://m3.material.io/styles/color/the-color-system/key-colors-tones)
- [Android Telegram Themes](https://t.me/themes)

---

**Автор**: Создано с помощью Claude  
**Дата**: Январь 2026  
**Версия**: 1.0

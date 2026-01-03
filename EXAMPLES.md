# Примеры использования

## Пример 1: Базовая конвертация

```python
from attheme_to_tdesktop import create_desktop_theme

# Конвертация темы
create_desktop_theme('MyTheme.attheme', 'MyTheme.tdesktop-theme')
```

## Пример 2: Пакетная конвертация

```python
from attheme_to_tdesktop import create_desktop_theme
import os

# Конвертация всех .attheme файлов в директории
themes_dir = './themes'
output_dir = './converted'

for filename in os.listdir(themes_dir):
    if filename.endswith('.attheme'):
        input_path = os.path.join(themes_dir, filename)
        output_name = filename.replace('.attheme', '.tdesktop-theme')
        output_path = os.path.join(output_dir, output_name)
        
        print(f'Конвертация {filename}...')
        create_desktop_theme(input_path, output_path)
```

## Пример 3: Использование из командной строки

Создайте файл `convert.py`:

```python
#!/usr/bin/env python3
import sys
from attheme_to_tdesktop import create_desktop_theme

if len(sys.argv) != 3:
    print("Использование: python convert.py input.attheme output.tdesktop-theme")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

create_desktop_theme(input_file, output_file)
```

Затем используйте:

```bash
python convert.py MyTheme.attheme MyTheme.tdesktop-theme
```

## Пример 4: Анализ цветов темы

```python
from attheme_to_tdesktop import load_android_colors

# Загружаем цвета из темы
colors = load_android_colors('MyTheme.attheme')

# Выводим основные цвета
print("Основные цвета темы:")
print(f"Фон: {colors.get('windowBackgroundWhite')}")
print(f"Текст: {colors.get('windowBackgroundWhiteBlackText')}")
print(f"Акцент: {colors.get('windowBackgroundWhiteBlueText')}")
print(f"Входящие сообщения: {colors.get('chat_inBubble')}")
print(f"Исходящие сообщения: {colors.get('chat_outBubble')}")
```

## Пример 5: Кастомизация фона

Если вы хотите создать тему без фонового изображения или с собственным фоном, можете модифицировать код:

```python
import zipfile
from attheme_to_tdesktop import load_android_colors

# Загружаем цвета
colors = load_android_colors('MyTheme.attheme')

# Создаём только файл цветов (без автоматического фона)
# ... ваш код создания colors.tdesktop-theme ...

# Создаём архив с вашим собственным фоном
with zipfile.ZipFile('MyTheme.tdesktop-theme', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('colors.tdesktop-theme', 'colors.tdesktop-theme')
    zipf.write('my_custom_background.png', 'background.png')
```

## Пример 6: Получение информации о теме

```python
from attheme_to_tdesktop import load_android_colors, parse_color_value

# Загружаем тему
colors = load_android_colors('MyTheme.attheme')

# Статистика
print(f"Всего параметров: {len(colors)}")
print(f"\nЦветовая схема:")

# Подсчитываем использование Material цветов
material_count = sum(1 for v in colors.values() 
                     if any(v.startswith(prefix) 
                           for prefix in ['n1_', 'n2_', 'a1_', 'a2_', 'a3_', 'm']))
                     
print(f"Material Design цветов: {material_count}")
print(f"Кастомных hex цветов: {len(colors) - material_count}")
```

## Пример 7: Проверка качества конвертации

```python
from attheme_to_tdesktop import create_desktop_theme, load_android_colors
import zipfile

# Конвертируем тему
create_desktop_theme('MyTheme.attheme', 'MyTheme.tdesktop-theme')

# Проверяем созданный файл
with zipfile.ZipFile('MyTheme.tdesktop-theme', 'r') as zipf:
    print("Содержимое архива:")
    for info in zipf.filelist:
        print(f"  {info.filename}: {info.file_size} байт")
    
    # Читаем и проверяем colors файл
    with zipf.open('colors.tdesktop-theme') as f:
        content = f.read().decode('utf-8')
        lines = [l.strip() for l in content.split('\n') 
                if l.strip() and not l.strip().startswith('//')]
        print(f"\nВсего параметров в Desktop теме: {len(lines)}")
```

## Пример 8: Создание вариаций темы

```python
from attheme_to_tdesktop import load_android_colors, adjust_brightness
import zipfile

# Загружаем базовую тему
base_colors = load_android_colors('BaseTheme.attheme')

# Создаём светлую версию (увеличиваем яркость фона)
light_bg = adjust_brightness(base_colors['windowBackgroundWhite'], 50)

# Создаём тёмную версию (уменьшаем яркость)
dark_bg = adjust_brightness(base_colors['windowBackgroundWhite'], -30)

# ... создайте модифицированные темы ...
```

## Troubleshooting

### Ошибка: "No module named 'PIL'"

```bash
pip install Pillow
```

### Ошибка: Неверный формат цвета

Проверьте, что в вашей .attheme теме цвета указаны корректно:

```python
from attheme_to_tdesktop import parse_color_value

# Тестируем парсинг цвета
test_color = "n1_900(a=80)"
result = parse_color_value(test_color, {})
print(f"Результат: {result}")
```

### Тема не применяется в Telegram Desktop

1. Проверьте, что файл имеет расширение `.tdesktop-theme`
2. Убедитесь, что архив содержит файл `colors.tdesktop-theme`
3. Попробуйте открыть файл темы через Settings → Chat Settings → Choose from file

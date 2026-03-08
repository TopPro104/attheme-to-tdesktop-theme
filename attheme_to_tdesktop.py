#!/usr/bin/env python3
"""
Конвертер тем Telegram: Android (.attheme) -> Desktop (.tdesktop-theme)

Версия 2.0:
  - CLI с argparse (аргументы командной строки)
  - Извлечение оригинального фона из .attheme
  - Обработка ошибок и валидация
  - Цветной вывод в терминал
"""
import re
import sys
import zipfile
import os
import argparse
import struct
from pathlib import Path

# ─── Цвета терминала ────────────────────────────────────────────────────────
class Style:
    """ANSI-цвета для терминала (отключаются если нет поддержки)."""
    _enabled = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    RESET  = '\033[0m'  if _enabled else ''
    BOLD   = '\033[1m'  if _enabled else ''
    RED    = '\033[91m' if _enabled else ''
    GREEN  = '\033[92m' if _enabled else ''
    YELLOW = '\033[93m' if _enabled else ''
    CYAN   = '\033[96m' if _enabled else ''
    DIM    = '\033[2m'  if _enabled else ''

def info(msg):
    print(f"  {Style.CYAN}ℹ{Style.RESET} {msg}")

def success(msg):
    print(f"  {Style.GREEN}✓{Style.RESET} {msg}")

def warn(msg):
    print(f"  {Style.YELLOW}⚠{Style.RESET} {msg}")

def error(msg):
    print(f"  {Style.RED}✗{Style.RESET} {msg}", file=sys.stderr)

def header(msg):
    print(f"\n{Style.BOLD}{msg}{Style.RESET}")


# ─── Material Design 3 палитра ──────────────────────────────────────────────
MATERIAL_COLORS = {
    # Neutral1
    'n1_0': '#000000', 'n1_10': '#1c1b1f', 'n1_50': '#e6e1e5',
    'n1_100': '#cac5cd', 'n1_200': '#aeaaae', 'n1_300': '#938f96',
    'n1_400': '#79767d', 'n1_500': '#605d64', 'n1_600': '#49464f',
    'n1_700': '#33303a', 'n1_800': '#1c1b1f', 'n1_900': '#1a1a1a',
    # Neutral2
    'n2_0': '#000000', 'n2_100': '#cac5cd', 'n2_200': '#aeaaae',
    'n2_300': '#938f96', 'n2_400': '#79767d', 'n2_500': '#605d64',
    'n2_600': '#49464f', 'n2_700': '#33303a', 'n2_800': '#29282c',
    'n2_900': '#1c1b1f',
    # Accent1
    'a1_0': '#000000', 'a1_50': '#eee1f7', 'a1_100': '#d0bcff',
    'a1_200': '#b69df8', 'a1_300': '#9a82db', 'a1_400': '#7f67be',
    'a1_500': '#6750a4', 'a1_600': '#4f378b', 'a1_700': '#381e72',
    'a1_800': '#23036a', 'a1_900': '#1c1b1f',
    # Accent2
    'a2_0': '#000000', 'a2_100': '#ffd7f1', 'a2_200': '#efb8c8',
    'a2_300': '#d29dad', 'a2_400': '#b6839a', 'a2_500': '#9a6b88',
    'a2_600': '#7f5376', 'a2_700': '#633b63', 'a2_800': '#48244f',
    'a2_900': '#2e0e39',
    # Accent3
    'a3_0': '#000000', 'a3_100': '#f6edff', 'a3_200': '#d6cadf',
    'a3_300': '#b9aec4', 'a3_400': '#9d93a9', 'a3_500': '#827990',
    'a3_600': '#686077', 'a3_700': '#4e475f', 'a3_800': '#353048',
    'a3_900': '#1c1b1f',
    # Material предопределённые
    'mWhite': '#ffffff', 'mBlack': '#000000',
    'mGreen500': '#4caf50', 'mRed200': '#ef9a9a', 'mRed500': '#f44336',
}


# ─── Парсинг цветов ─────────────────────────────────────────────────────────
def parse_color_value(value, color_vars=None):
    """Парсит значение цвета из Android темы.

    Поддерживает форматы:
      - hex: #1a1a1a
      - Material Design: n1_900, a1_200, mWhite
      - ссылки на другие переменные
      - alpha/lightness модификаторы: n1_800(a=80), primaryDark(l=70)
      - ARGB числа: -14643754h, 2147483647
    """
    if color_vars is None:
        color_vars = {}

    value = value.strip()

    # hex
    if value.startswith('#'):
        return value

    # Material Design
    if value in MATERIAL_COLORS:
        return MATERIAL_COLORS[value]

    # Ссылка на переменную (с защитой от рекурсии)
    if value in color_vars:
        return parse_color_value(color_vars[value], color_vars)

    # alpha модификатор: name(a=80)
    match = re.match(r'(.+?)\s*\(a=(\d+)\)', value)
    if match:
        base = match.group(1).strip()
        alpha = int(match.group(2))
        base_color = parse_color_value(base, color_vars)
        if base_color and base_color.startswith('#'):
            rgb = base_color.lstrip('#')[:6]
            alpha_hex = format(int(alpha * 255 / 100), '02x')
            return f'#{rgb}{alpha_hex}'

    # lightness модификатор: name(l=X) — просто берём базовый цвет
    match = re.match(r'(.+?)\s*\(l=(\d+)\)', value)
    if match:
        base = match.group(1).strip()
        return parse_color_value(base, color_vars)

    # Hex с суффиксом: -14643754h
    if value.endswith('h'):
        try:
            hex_str = value[:-1].lstrip('-')
            num = int(hex_str, 16)
            r = (num >> 16) & 0xFF
            g = (num >> 8) & 0xFF
            b = num & 0xFF
            return f'#{r:02x}{g:02x}{b:02x}'
        except ValueError:
            pass

    # Десятичное число (Android signed ARGB int)
    try:
        num = int(value)
        if num < 0:
            num = num & 0xFFFFFFFF
        a = (num >> 24) & 0xFF
        r = (num >> 16) & 0xFF
        g = (num >> 8) & 0xFF
        b = num & 0xFF
        if 0 < a < 255:
            return f'#{r:02x}{g:02x}{b:02x}{a:02x}'
        return f'#{r:02x}{g:02x}{b:02x}'
    except ValueError:
        pass

    return value


# ─── Извлечение фона из .attheme ────────────────────────────────────────────
# В .attheme файлах фоновое изображение хранится как бинарные данные
# после маркера «WPS\n» и до маркера «\nWPE\n» (Wallpaper Start / Wallpaper End).
# Бинарные данные — это обычный JPEG.

WPS_MARKER = b'WPS\n'
WPE_MARKER = b'\nWPE\n'

def extract_wallpaper(attheme_path):
    """Извлекает встроенное изображение обоев из .attheme файла.

    Возвращает bytes с JPEG-данными или None, если обои не встроены.
    """
    try:
        with open(attheme_path, 'rb') as f:
            data = f.read()
    except OSError as e:
        warn(f"Не удалось прочитать файл для извлечения обоев: {e}")
        return None

    wps_idx = data.find(WPS_MARKER)
    if wps_idx == -1:
        return None

    img_start = wps_idx + len(WPS_MARKER)
    wpe_idx = data.find(WPE_MARKER, img_start)
    if wpe_idx == -1:
        # Иногда маркер WPE отсутствует — берём всё до конца
        img_data = data[img_start:]
    else:
        img_data = data[img_start:wpe_idx]

    if len(img_data) < 100:
        return None

    # Проверяем что это действительно JPEG
    if img_data[:2] == b'\xff\xd8':
        return img_data

    # Или PNG
    if img_data[:4] == b'\x89PNG':
        return img_data

    warn("Встроенные данные обоев не распознаны как JPEG/PNG")
    return None


# ─── Загрузка цветов ─────────────────────────────────────────────────────────
def load_android_colors(attheme_path):
    """Загружает все цвета из Android .attheme файла.

    Читает только текстовую часть (до маркера WPS, если есть).
    """
    try:
        with open(attheme_path, 'rb') as f:
            raw = f.read()
    except OSError as e:
        error(f"Не удалось открыть файл: {e}")
        sys.exit(1)

    # Отсекаем бинарные данные обоев
    wps_idx = raw.find(WPS_MARKER)
    if wps_idx != -1:
        raw = raw[:wps_idx]

    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('utf-8', errors='replace')

    colors = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('//') or line == 'end':
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            colors[key.strip()] = value.strip()

    # Разрешаем ссылки
    resolved = {}
    for key, value in colors.items():
        resolved[key] = parse_color_value(value, colors)

    return resolved


# ─── Утилиты ─────────────────────────────────────────────────────────────────
def adjust_brightness(color, percent):
    """Регулирует яркость hex-цвета на заданный процент."""
    if not color or not color.startswith('#'):
        return color

    color_body = color.lstrip('#')
    has_alpha = len(color_body) == 8
    rgb = color_body[:6]
    alpha = color_body[6:] if has_alpha else ''

    try:
        r = int(rgb[0:2], 16)
        g = int(rgb[2:4], 16)
        b = int(rgb[4:6], 16)
    except ValueError:
        return '#' + color_body

    factor = 1 + (percent / 100)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))

    result = f'#{r:02x}{g:02x}{b:02x}'
    if has_alpha:
        result += alpha
    return result


def blend_colors(color1, color2, amount=0.5):
    """Смешивает два hex-цвета. amount=0 → color1, amount=1 → color2."""
    if not color1 or not color1.startswith('#'):
        return color2
    if not color2 or not color2.startswith('#'):
        return color1

    def to_rgb(h):
        h = h.lstrip('#')[:6]
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    try:
        r1, g1, b1 = to_rgb(color1)
        r2, g2, b2 = to_rgb(color2)
    except (ValueError, IndexError):
        return color1

    r = int(r1 * (1 - amount) + r2 * amount)
    g = int(g1 * (1 - amount) + g2 * amount)
    b = int(b1 * (1 - amount) + b2 * amount)
    return f'#{r:02x}{g:02x}{b:02x}'


def generate_gradient_background(background, primary_color, output_file):
    """Генерирует фоновое PNG-изображение с градиентом (fallback)."""
    try:
        from PIL import Image, ImageDraw
        import math
    except ImportError:
        warn("Pillow не установлен — фоновое изображение не создано.")
        warn("Установите: pip install Pillow")
        return False

    width, height = 1024, 768
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # Парсим цвета
    def hex_to_rgb(h, default):
        try:
            h = h.lstrip('#')[:6]
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except (ValueError, IndexError):
            return default

    base = hex_to_rgb(background, (26, 26, 26))
    accent = hex_to_rgb(primary_color, (182, 157, 248))

    # Градиент
    for y in range(height):
        blend = y / height
        r = int(base[0] * (1 - blend * 0.3) + base[0] * 1.3 * blend * 0.3)
        g = int(base[1] * (1 - blend * 0.3) + base[1] * 1.3 * blend * 0.3)
        b = int(base[2] * (1 - blend * 0.3) + base[2] * 1.3 * blend * 0.3)
        draw.line([(0, y), (width, y)], fill=(
            min(255, max(0, r)),
            min(255, max(0, g)),
            min(255, max(0, b)),
        ))

    # Акцентные круги
    pixels = img.load()
    circles = [
        (width * 0.85, -height * 0.1, height * 0.6, 0.03),
        (-width * 0.1, height * 1.1, height * 0.4, 0.02),
    ]
    for cx, cy, radius, strength in circles:
        # Ограничиваем область перебора bounding-box'ом круга
        x_min = max(0, int(cx - radius))
        x_max = min(width, int(cx + radius) + 1)
        y_min = max(0, int(cy - radius))
        y_max = min(height, int(cy + radius) + 1)
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < radius:
                    alpha = (1 - dist / radius) * strength
                    pr, pg, pb = pixels[x, y]
                    pixels[x, y] = (
                        int(pr * (1 - alpha) + accent[0] * alpha),
                        int(pg * (1 - alpha) + accent[1] * alpha),
                        int(pb * (1 - alpha) + accent[2] * alpha),
                    )

    img.save(output_file, optimize=True, quality=85)
    return True


# ─── Генерация темы ──────────────────────────────────────────────────────────
def create_desktop_theme(attheme_path, output_path, *, no_bg=False):
    """Создаёт .tdesktop-theme из .attheme файла."""

    attheme_path = Path(attheme_path)
    output_path = Path(output_path)

    # ── Валидация ────────────────────────────────────────────────────────
    if not attheme_path.exists():
        error(f"Файл не найден: {attheme_path}")
        sys.exit(1)

    if not attheme_path.suffix == '.attheme':
        warn(f"Файл не имеет расширения .attheme — продолжаю всё равно")

    if output_path.suffix != '.tdesktop-theme':
        warn("Выходной файл обычно имеет расширение .tdesktop-theme")

    header("🎨 Конвертация Android → Desktop темы")
    info(f"Входной файл:  {attheme_path}")
    info(f"Выходной файл: {output_path}")

    # ── Загрузка цветов ──────────────────────────────────────────────────
    info("Загрузка цветов из Android темы...")
    colors = load_android_colors(attheme_path)
    success(f"Загружено {len(colors)} параметров цвета")

    primary_color = colors.get('windowBackgroundWhiteBlueText', '#6750a4')
    background = colors.get('windowBackgroundWhite', '#1c1b1f')
    text_color = colors.get('windowBackgroundWhiteBlackText', '#e6e1e5')
    msg_in_bg = colors.get('chat_inBubble', '#2b2930')
    msg_out_bg = colors.get('chat_outBubble', primary_color)
    msg_panel_bg = colors.get('chat_messagePanelBackground', background)

    info(f"Основной:  {primary_color}")
    info(f"Фон:       {background}")
    info(f"Текст:     {text_color}")

    # ── Генерация colors.tdesktop-theme ──────────────────────────────────
    theme_content = f"""// Telegram Desktop Theme
// Converted from: {attheme_path.name}
// Generator: attheme-to-tdesktop v2.0

// Define Color Scheme
primaryColor: {primary_color};
primaryColorDark: {adjust_brightness(primary_color, -30)};
primaryColorTrans: {primary_color}80;

// Background levels
primaryDark: {background};
secondaryDark: {adjust_brightness(background, 8)};
tertiaryDark: {adjust_brightness(background, 15)};
quaternaryDark: {adjust_brightness(background, 20)};
quinaryDark: {adjust_brightness(background, 25)};
senaryDark: {adjust_brightness(background, 30)};

// Text
primaryText: {text_color};
secondaryText: {adjust_brightness(text_color, -10)};

// === BASE WINDOW COLORS ===
windowBg: primaryDark;
windowFg: primaryText;
windowBgOver: tertiaryDark;
windowBgRipple: primaryColor;
windowFgOver: primaryText;
windowSubTextFg: {colors.get('windowBackgroundWhiteGrayText', '#938f96')};
windowSubTextFgOver: primaryColor;
windowBoldFg: primaryText;
windowBoldFgOver: primaryText;
windowBgActive: primaryColor;
windowFgActive: #ffffff;
windowActiveTextFg: primaryColor;
windowShadowFg: #000000;
windowShadowFgFallback: windowBg;

shadowFg: #00000000;
slideFadeOutBg: #0000003c;
slideFadeOutShadowFg: windowShadowFg;

imageBg: primaryDark;
imageBgTransparent: primaryText;

// === BUTTONS ===
activeButtonBg: primaryColor;
activeButtonBgOver: {adjust_brightness(primary_color, 10)};
activeButtonBgRipple: {adjust_brightness(primary_color, -20)};
activeButtonFg: #ffffff;
activeButtonFgOver: #ffffff;
activeButtonSecondaryFg: {adjust_brightness(primary_color, -30)};
activeButtonSecondaryFgOver: activeButtonSecondaryFg;

activeLineFg: primaryColor;
activeLineFgError: {colors.get('text_RedRegular', '#f44336')};

lightButtonBg: #00000000;
lightButtonBgOver: #0000004f;
lightButtonBgRipple: primaryColor;
lightButtonFg: primaryColor;
lightButtonFgOver: lightButtonFg;

attentionButtonFg: {colors.get('text_RedRegular', '#f44336')};
attentionButtonFgOver: attentionButtonFg;
attentionButtonBgOver: #aa140064;
attentionButtonBgRipple: attentionButtonFgOver;

outlineButtonBg: windowBg;
outlineButtonBgOver: tertiaryDark;
outlineButtonOutlineFg: primaryColor;
outlineButtonBgRipple: primaryColor;

// === DIALOGS ===
dialogsBg: {colors.get('chats_menuBackground', 'secondaryDark')};
dialogsNameFg: {colors.get('chats_name', 'primaryText')};
dialogsChatIconFg: {colors.get('chats_secretIcon', 'primaryColor')};
dialogsDateFg: {colors.get('chats_date', 'windowSubTextFg')};
dialogsTextFg: {colors.get('chats_message', 'windowSubTextFg')};
dialogsTextFgService: {colors.get('chats_actionMessage', 'primaryColor')};
dialogsDraftFg: {colors.get('chats_draft', '#f44336')};
dialogsVerifiedIconBg: primaryColor;
dialogsVerifiedIconFg: #ffffff;
dialogsSendingIconFg: windowSubTextFg;
dialogsSentIconFg: primaryColor;
dialogsUnreadBg: {colors.get('chats_unreadCounter', 'primaryColor')};
dialogsUnreadBgMuted: {colors.get('chats_unreadCounterMuted', 'windowSubTextFg')};
dialogsUnreadFg: {colors.get('chats_unreadCounterText', '#ffffff')};

dialogsBgOver: tertiaryDark;
dialogsNameFgOver: dialogsNameFg;
dialogsChatIconFgOver: dialogsChatIconFg;
dialogsDateFgOver: dialogsDateFg;
dialogsTextFgOver: dialogsTextFg;
dialogsTextFgServiceOver: dialogsTextFgService;
dialogsDraftFgOver: dialogsDraftFg;
dialogsVerifiedIconBgOver: dialogsVerifiedIconBg;
dialogsVerifiedIconFgOver: dialogsVerifiedIconFg;
dialogsSendingIconFgOver: dialogsSendingIconFg;
dialogsSentIconFgOver: dialogsSentIconFg;
dialogsUnreadBgOver: dialogsUnreadBg;
dialogsUnreadBgMutedOver: dialogsUnreadBgMuted;
dialogsUnreadFgOver: dialogsUnreadFg;

dialogsBgActive: {blend_colors(adjust_brightness(colors.get('chats_menuBackground', background), 100), primary_color, 0.2)};
dialogsNameFgActive: primaryText;
dialogsChatIconFgActive: primaryColor;
dialogsDateFgActive: secondaryText;
dialogsTextFgActive: secondaryText;
dialogsTextFgServiceActive: primaryColor;
dialogsDraftFgActive: {colors.get('chats_draft', '#f44336')};
dialogsVerifiedIconBgActive: primaryColor;
dialogsVerifiedIconFgActive: #ffffff;
dialogsSendingIconFgActive: secondaryText;
dialogsSentIconFgActive: primaryColor;
dialogsUnreadBgActive: primaryColor;
dialogsUnreadBgMutedActive: windowSubTextFg;
dialogsUnreadFgActive: #ffffff;

dialogsRippleBg: {adjust_brightness(background, 60)};
dialogsRippleBgActive: {blend_colors(adjust_brightness(background, 130), primary_color, 0.25)};

dialogsForwardBg: dialogsBgActive;
dialogsForwardFg: dialogsNameFgActive;

searchedBarBg: secondaryDark;
searchedBarBorder: primaryColor;
searchedBarFg: primaryColor;

// === TOP BAR ===
topBarBg: {colors.get('actionBarDefault', 'primaryDark')};

// === MENU ===
menuBg: primaryDark;
menuBgOver: quaternaryDark;
menuBgRipple: primaryColor;
menuIconFg: {colors.get('actionBarDefaultIcon', 'primaryColor')};
menuIconFgOver: primaryColor;
menuSubmenuArrowFg: windowSubTextFg;
menuFgDisabled: windowSubTextFg;
menuSeparatorFg: tertiaryDark;

// === SCROLL ===
scrollBarBg: primaryColorTrans;
scrollBarBgOver: primaryColor;
scrollBg: #ffffff1a;
scrollBgOver: #ffffff24;

// === INPUT FIELDS ===
placeholderFg: {colors.get('chat_messagePanelHint', 'windowSubTextFg')};
placeholderFgActive: windowSubTextFg;
inputBorderFg: tertiaryDark;
filterInputBorderFg: primaryColor;
filterInputInactiveBg: tertiaryDark;
filterInputActiveBg: quaternaryDark;

checkboxFg: primaryColor;
sliderBgInactive: tertiaryDark;
sliderBgActive: windowBgActive;

// === INCOMING MESSAGES ===
msgInBg: {msg_in_bg};
msgInBgSelected: {adjust_brightness(msg_in_bg, 15)};
msgInShadow: #00000000;
msgInShadowSelected: #00000000;

historyTextInFg: {colors.get('chat_messageTextIn', 'primaryText')};
historyTextInFgSelected: historyTextInFg;

msgInDateFg: {colors.get('chat_inTimeText', 'windowSubTextFg')};
msgInDateFgSelected: msgInDateFg;

msgInServiceFg: {colors.get('chat_inReplyNameText', 'primaryColor')};
msgInServiceFgSelected: msgInServiceFg;

msgInReplyBarColor: {colors.get('chat_inReplyLine', 'primaryColor')};
msgInReplyBarSelColor: msgInReplyBarColor;

msgInMonoFg: {colors.get('chat_inCodeBackground', 'primaryColor')};

// === OUTGOING MESSAGES ===
msgOutBg: {msg_out_bg};
msgOutBgSelected: {adjust_brightness(msg_out_bg, -10)};
msgOutShadow: #00000000;
msgOutShadowSelected: #00000000;

historyTextOutFg: {colors.get('chat_messageTextOut', '#ffffff')};
historyTextOutFgSelected: historyTextOutFg;

msgOutDateFg: {colors.get('chat_outTimeText', '#ffffff')};
msgOutDateFgSelected: msgOutDateFg;

msgOutServiceFg: historyTextOutFg;
msgOutServiceFgSelected: historyTextOutFg;

msgOutReplyBarColor: {colors.get('chat_outReplyLine', 'historyTextOutFg')};
msgOutReplyBarSelColor: msgOutReplyBarColor;

msgOutMonoFg: historyTextOutFg;

// === FILE COLORS ===
msgFile1Bg: primaryColor;
msgFile1BgDark: primaryColorDark;
msgFile1BgOver: primaryColor;
msgFile1BgSelected: primaryColor;

msgFile2Bg: #4caf50;
msgFile2BgDark: #2e7d32;
msgFile2BgOver: #4caf50;
msgFile2BgSelected: #4caf50;

msgFile3Bg: #f44336;
msgFile3BgDark: #c62828;
msgFile3BgOver: #f44336;
msgFile3BgSelected: #f44336;

msgFile4Bg: #ffc107;
msgFile4BgDark: #f57c00;
msgFile4BgOver: #ffc107;
msgFile4BgSelected: #ffc107;

// === HISTORY / COMPOSE AREA ===
historyComposeAreaBg: {msg_panel_bg};
historyComposeAreaFg: {colors.get('chat_messagePanelText', 'primaryText')};
historyComposeAreaFgService: msgInDateFg;
historyComposeIconFg: {colors.get('chat_messagePanelIcons', 'menuIconFg')};
historyComposeIconFgOver: menuIconFgOver;
historySendIconFg: {colors.get('chat_messagePanelSend', 'primaryColor')};
historySendIconFgOver: historySendIconFg;

historyPinnedBg: secondaryDark;
historyReplyBg: primaryDark;
historyReplyIconFg: windowBgActive;
historyReplyCancelFg: windowSubTextFg;
historyReplyCancelFgOver: primaryColor;

historyComposeButtonBg: tertiaryDark;
historyComposeButtonBgOver: quaternaryDark;
historyComposeButtonBgRipple: primaryColor;

// === EMOJI PANEL ===
emojiPanBg: {colors.get('chat_emojiPanelBackground', 'primaryDark')};
emojiIconFg: {colors.get('chat_emojiPanelIcon', 'windowSubTextFg')};
emojiIconFgActive: {colors.get('chat_emojiPanelIconSelected', 'primaryColor')};

// === PROFILE ===
profileStatusFgOver: windowSubTextFg;
profileVerifiedCheckBg: windowBgActive;
profileVerifiedCheckFg: windowFgActive;
profileAdminStartFg: windowBgActive;

// === NOTIFICATIONS ===
notificationBg: windowBg;

// === CALLS ===
callBg: #26282cf2;
callNameFg: primaryText;
callFingerprintBg: #00000066;
callStatusFg: windowSubTextFg;
callIconFg: primaryText;
callAnswerBg: #4caf50;
callAnswerRipple: #2e7d32;
callHangupBg: #f44336;
callHangupRipple: #c62828;

// === MEDIA VIEWER ===
mediaviewFileBg: windowBg;
mediaviewFileNameFg: windowFg;
mediaviewFileSizeFg: windowSubTextFg;
mediaviewFileRedCornerFg: #f44336;
mediaviewFileYellowCornerFg: #ffc107;
mediaviewFileGreenCornerFg: #4caf50;
mediaviewFileBlueCornerFg: primaryColor;
mediaviewFileExtFg: activeButtonFg;

mediaviewMenuBg: #383838;
mediaviewMenuBgOver: #505050;
mediaviewMenuBgRipple: #676767;
mediaviewMenuFg: windowFgActive;

mediaviewBg: #222222eb;
mediaviewVideoBg: imageBg;
mediaviewControlBg: #0000003c;
mediaviewControlFg: windowFgActive;
mediaviewCaptionBg: #11111180;
mediaviewCaptionFg: mediaviewControlFg;
mediaviewTextLinkFg: primaryColor;

mediaviewPlaybackActive: #c7c7c7;
mediaviewPlaybackInactive: #252525;
mediaviewPlaybackActiveOver: primaryText;
mediaviewPlaybackInactiveOver: #474747;
mediaviewPlaybackProgressFg: #ffffffc7;
mediaviewPlaybackIconFg: mediaviewPlaybackActive;
mediaviewPlaybackIconFgOver: mediaviewPlaybackActiveOver;

// === ADDITIONAL ===
tooltipBg: #d4dadd;
tooltipFg: #9a9e9c;
tooltipBorderFg: #c9d1db;

titleBg: primaryDark;
titleBgActive: titleBg;
titleButtonBg: titleBg;
titleButtonFg: primaryColor;
titleButtonBgOver: primaryColor;
titleButtonFgOver: primaryText;
titleButtonBgActive: titleButtonBg;
titleButtonFgActive: titleButtonFg;
titleButtonBgActiveOver: titleButtonBgOver;
titleButtonFgActiveOver: titleButtonFgOver;
titleButtonCloseBg: titleButtonBg;
titleButtonCloseFg: titleButtonFg;
titleButtonCloseBgOver: #f44336;
titleButtonCloseFgOver: primaryText;
titleButtonCloseBgActive: titleButtonCloseBg;
titleButtonCloseFgActive: titleButtonCloseFg;
titleButtonCloseBgActiveOver: titleButtonCloseBgOver;
titleButtonCloseFgActiveOver: titleButtonCloseFgOver;

titleFg: primaryText;
titleFgActive: titleFg;

trayCounterBg: {colors.get('chats_unreadCounter', '#f44336')};
trayCounterBgMute: windowSubTextFg;
trayCounterFg: primaryText;
trayCounterBgMacInvert: primaryText;
trayCounterFgMacInvert: #ffffff01;

layerBg: #0000007f;

cancelIconFg: windowSubTextFg;
cancelIconFgOver: primaryColor;

boxBg: primaryDark;
boxTextFg: windowFg;
boxTextFgGood: #4caf50;
boxTextFgError: #f44336;
boxTitleFg: primaryText;
boxSearchBg: tertiaryDark;
boxTitleAdditionalFg: windowSubTextFg;
boxTitleCloseFg: cancelIconFg;
boxTitleCloseFgOver: cancelIconFgOver;

membersAboutLimitFg: windowSubTextFg;

contactsBg: windowBg;
contactsBgOver: windowBgOver;
contactsNameFg: primaryText;
contactsStatusFg: windowSubTextFg;
contactsStatusFgOver: windowSubTextFg;
contactsStatusFgOnline: primaryColor;

photoCropFadeBg: layerBg;
photoCropPointFg: #ffffff7f;

callArrowFg: primaryColor;
callArrowMissedFg: #f44336;

introBg: windowBg;
introTitleFg: primaryText;
introDescriptionFg: windowSubTextFg;
introErrorFg: #f44336;

introCoverTopBg: primaryColor;
introCoverBottomBg: primaryColorDark;
introCoverIconsFg: primaryText;
introCoverPlaneTrace: primaryText;
introCoverPlaneInner: primaryText;
introCoverPlaneOuter: primaryText;
introCoverPlaneTop: primaryText;

dialogsMenuIconFg: menuIconFg;
dialogsMenuIconFgOver: menuIconFgOver;

botKbBg: {colors.get('chat_botKeyboardButtonBackground', 'secondaryDark')};
botKbDownBg: primaryColor;
botKbRippleBg: primaryColor;

historyUnreadBarBg: tertiaryDark;
historyUnreadBarBorder: primaryColor;
historyUnreadBarFg: primaryColor;

msgWaveformInActive: historyTextInFg;
msgWaveformInActiveSelected: historyTextInFg;
msgWaveformInInactive: msgInDateFg;
msgWaveformInInactiveSelected: msgInDateFg;

msgWaveformOutActive: historyTextOutFg;
msgWaveformOutActiveSelected: historyTextOutFg;
msgWaveformOutInactive: msgOutDateFg;
msgWaveformOutInactiveSelected: msgOutDateFg;

msgBotKbOverBgAdd: primaryColor;
msgBotKbIconFg: msgServiceFg;
msgBotKbRippleBg: primaryColor;

mediaInFg: msgInDateFg;
mediaInFgSelected: msgInDateFg;
mediaOutFg: msgOutDateFg;
mediaOutFgSelected: msgOutDateFg;

youtubePlayIconBg: #e83131c8;
youtubePlayIconFg: windowFgActive;
videoPlayIconBg: #0000007f;
videoPlayIconFg: #ffffff;

toastBg: #000000b2;
toastFg: windowFgActive;

reportSpamBg: emojiPanBg;
reportSpamFg: windowFg;

historyToDownBg: tertiaryDark;
historyToDownBgOver: quaternaryDark;
historyToDownBgRipple: primaryColor;
historyToDownFg: menuIconFg;
historyToDownFgOver: menuIconFgOver;
historyToDownShadow: #00000040;

overviewCheckBg: #00000040;
overviewCheckFg: primaryText;
overviewCheckFgActive: primaryText;
overviewPhotoSelectOverlay: primaryColor;

historyFileInIconFg: {colors.get('chat_inFileIcon', 'primaryColor')};
historyFileInIconFgSelected: historyFileInIconFg;
historyFileInRadialFg: historyFileInIconFg;
historyFileInRadialFgSelected: historyFileInIconFg;

historyFileOutIconFg: {colors.get('chat_outFileIcon', 'historyTextOutFg')};
historyFileOutIconFgSelected: historyFileOutIconFg;
historyFileOutRadialFg: historyFileOutIconFg;
historyFileOutRadialFgSelected: historyFileOutIconFg;

linkCropFg: primaryColor;
linkWarningFg: #f44336;

historyLinkInFg: {colors.get('chat_messageLinkIn', 'primaryColor')};
historyLinkInFgSelected: historyLinkInFg;
historyLinkOutFg: {colors.get('chat_messageLinkOut', 'historyTextOutFg')};
historyLinkOutFgSelected: historyLinkOutFg;

msgFile1BgDark: msgFile1BgDark;
msgFile2BgDark: msgFile2BgDark;
msgFile3BgDark: msgFile3BgDark;
msgFile4BgDark: msgFile4BgDark;

historyFileInPlay: historyFileInIconFg;
historyFileInPlaySelected: historyFileInIconFg;
historyFileInWaveformActive: historyFileInIconFg;
historyFileInWaveformActiveSelected: historyFileInIconFg;

historyFileOutPlay: historyFileOutIconFg;
historyFileOutPlaySelected: historyFileOutIconFg;
historyFileOutWaveformActive: historyFileOutIconFg;
historyFileOutWaveformActiveSelected: historyFileOutIconFg;

msgServiceBg: #00000080;
msgServiceBgSelected: primaryColor;
msgServiceFg: windowFgActive;
msgServiceFgSelected: windowFgActive;

historyReplyBorderFg: primaryColor;
historyComposeAreaBgRipple: primaryColor;

mediaPlayerBg: windowBg;
mediaPlayerActiveFg: windowBgActive;
mediaPlayerInactiveFg: sliderBgInactive;
mediaPlayerDisabledFg: #9dd1ef;
"""

    # ── Временные файлы ──────────────────────────────────────────────────
    import tempfile
    work_dir = tempfile.mkdtemp(prefix='tg_theme_')
    colors_file = os.path.join(work_dir, 'colors.tdesktop-theme')

    with open(colors_file, 'w', encoding='utf-8') as f:
        f.write(theme_content)
    success("Файл цветов сгенерирован")

    # ── Фоновое изображение ──────────────────────────────────────────────
    bg_file = None

    if not no_bg:
        # Сначала пробуем извлечь оригинальный фон из .attheme
        info("Поиск встроенного фонового изображения...")
        wallpaper_data = extract_wallpaper(attheme_path)

        if wallpaper_data:
            # Определяем расширение
            if wallpaper_data[:4] == b'\x89PNG':
                ext = '.png'
            else:
                ext = '.jpg'

            bg_file = os.path.join(work_dir, f'background{ext}')
            with open(bg_file, 'wb') as f:
                f.write(wallpaper_data)
            bg_name = f'background{ext}'
            success(f"Извлечён оригинальный фон из темы ({len(wallpaper_data) // 1024} КБ)")
        else:
            info("Встроенный фон не найден — генерирую градиент...")
            bg_file = os.path.join(work_dir, 'background.png')
            bg_name = 'background.png'
            if generate_gradient_background(background, primary_color, bg_file):
                success("Градиентный фон создан")
            else:
                bg_file = None

    # ── Сборка ZIP ───────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)

    info(f"Создание архива...")
    with zipfile.ZipFile(str(output_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(colors_file, 'colors.tdesktop-theme')
        if bg_file and os.path.exists(bg_file):
            zipf.write(bg_file, bg_name)

    # Размер файла
    size_kb = output_path.stat().st_size / 1024

    # Чистим временные файлы
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)

    header("✅ Готово!")
    success(f"Тема: {output_path}  ({size_kb:.1f} КБ)")
    print()
    print(f"  {Style.DIM}Установка:{Style.RESET}")
    print(f"  {Style.DIM}1. Откройте Telegram Desktop{Style.RESET}")
    print(f"  {Style.DIM}2. Перетащите файл в окно Telegram{Style.RESET}")
    print(f"  {Style.DIM}3. Нажмите «Apply theme»{Style.RESET}")
    print()


# ─── CLI ─────────────────────────────────────────────────────────────────────
def build_parser():
    parser = argparse.ArgumentParser(
        prog='attheme_to_tdesktop',
        description='Конвертер тем Telegram: Android (.attheme) → Desktop (.tdesktop-theme)',
        epilog='Примеры:\n'
               '  %(prog)s                           — интерактивный выбор файла\n'
               '  %(prog)s Monet_Dark.attheme         — конвертация с авто-именем\n'
               '  %(prog)s theme.attheme -o out.tdesktop-theme\n'
               '  %(prog)s theme.attheme --no-bg\n'
               '  %(prog)s theme.attheme --extract-bg wallpaper.jpg\n'
               '  %(prog)s theme.attheme --list-colors\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'input',
        nargs='?',
        default=None,
        help='Путь к .attheme файлу (если не указан — скрипт спросит интерактивно)',
    )
    parser.add_argument(
        '-o', '--output',
        help='Путь к выходному .tdesktop-theme файлу '
             '(по умолчанию: <имя_входного>.tdesktop-theme)',
    )
    parser.add_argument(
        '--no-bg',
        action='store_true',
        help='Не добавлять фоновое изображение в тему',
    )
    parser.add_argument(
        '--extract-bg',
        metavar='FILE',
        help='Только извлечь встроенный фон из .attheme в указанный файл и выйти',
    )
    parser.add_argument(
        '--list-colors',
        action='store_true',
        help='Показать все цвета из .attheme файла и выйти',
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 2.0',
    )
    return parser


def find_attheme_files():
    """Ищет .attheme файлы в текущей директории."""
    return sorted(Path('.').glob('*.attheme'))


def ask_input_file():
    """Интерактивно запрашивает путь к .attheme файлу.

    Если в текущей папке есть .attheme файлы — предлагает выбрать из списка.
    """
    found = find_attheme_files()

    if found:
        print()
        header("Найдены .attheme файлы в текущей папке:")
        for i, f in enumerate(found, 1):
            size_kb = f.stat().st_size / 1024
            print(f"  {Style.CYAN}{i}{Style.RESET}) {f.name}  {Style.DIM}({size_kb:.0f} КБ){Style.RESET}")

        print(f"  {Style.CYAN}0{Style.RESET}) Ввести путь вручную")
        print()

        while True:
            try:
                choice = input(f"  Выберите файл [1-{len(found)}, 0]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                sys.exit(0)

            if choice == '0' or choice == '':
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(found):
                    return found[idx]
            except ValueError:
                # Может быть это путь к файлу
                p = Path(choice)
                if p.exists():
                    return p

            warn(f"Введите число от 0 до {len(found)}")

    # Ручной ввод
    print()
    while True:
        try:
            path_str = input("  Путь к .attheme файлу: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if not path_str:
            warn("Путь не может быть пустым")
            continue

        p = Path(path_str)
        if p.exists():
            return p
        else:
            error(f"Файл не найден: {p}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    # ── Определяем входной файл ──────────────────────────────────────────
    if args.input:
        input_path = Path(args.input)
    else:
        input_path = ask_input_file()

    # ── --extract-bg ─────────────────────────────────────────────────────
    if args.extract_bg:
        info(f"Извлечение фона из {input_path}...")
        wallpaper = extract_wallpaper(input_path)
        if wallpaper is None:
            error("В этом .attheme файле нет встроенного фонового изображения")
            sys.exit(1)
        out = Path(args.extract_bg)
        out.write_bytes(wallpaper)
        success(f"Фон сохранён: {out}  ({len(wallpaper) // 1024} КБ)")
        return

    # ── --list-colors ────────────────────────────────────────────────────
    if args.list_colors:
        colors = load_android_colors(input_path)
        header(f"Цвета из {input_path.name}  ({len(colors)} шт.)")
        max_key = max(len(k) for k in colors) if colors else 0
        for key in sorted(colors):
            val = colors[key]
            print(f"  {key:<{max_key}}  {val}")
        return

    # ── Обычная конвертация ──────────────────────────────────────────────
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.tdesktop-theme')

    create_desktop_theme(input_path, output_path, no_bg=args.no_bg)


if __name__ == '__main__':
    main()

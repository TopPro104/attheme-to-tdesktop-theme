#!/usr/bin/env python3
"""
Улучшенный конвертер тем Telegram: Android (.attheme) -> Desktop (.tdesktop-theme)
"""
import re
import zipfile
import os

# Material Design 3 цветовая палитра (примерные значения для темной темы)
# Префиксы: n1_ = neutral1, n2_ = neutral2, a1_ = accent1, a2_ = accent2, a3_ = accent3
MATERIAL_COLORS = {
    # Neutral1 (серые оттенки)
    'n1_0': '#000000',
    'n1_10': '#1c1b1f',
    'n1_50': '#e6e1e5',
    'n1_100': '#cac5cd',
    'n1_200': '#aeaaae',
    'n1_300': '#938f96',
    'n1_400': '#79767d',
    'n1_500': '#605d64',
    'n1_600': '#49464f',
    'n1_700': '#33303a',
    'n1_800': '#1c1b1f',
    'n1_900': '#1a1a1a',
    
    # Neutral2
    'n2_0': '#000000',
    'n2_100': '#cac5cd',
    'n2_200': '#aeaaae',
    'n2_300': '#938f96',
    'n2_400': '#79767d',
    'n2_500': '#605d64',
    'n2_600': '#49464f',
    'n2_700': '#33303a',
    'n2_800': '#29282c',
    'n2_900': '#1c1b1f',
    
    # Accent1 (основной акцентный цвет - синий/фиолетовый)
    'a1_0': '#000000',
    'a1_50': '#eee1f7',
    'a1_100': '#d0bcff',
    'a1_200': '#b69df8',
    'a1_300': '#9a82db',
    'a1_400': '#7f67be',
    'a1_500': '#6750a4',
    'a1_600': '#4f378b',
    'a1_700': '#381e72',
    'a1_800': '#23036a',
    'a1_900': '#1c1b1f',
    
    # Accent2
    'a2_0': '#000000',
    'a2_100': '#ffd7f1',
    'a2_200': '#efb8c8',
    'a2_300': '#d29dad',
    'a2_400': '#b6839a',
    'a2_500': '#9a6b88',
    'a2_600': '#7f5376',
    'a2_700': '#633b63',
    'a2_800': '#48244f',
    'a2_900': '#2e0e39',
    
    # Accent3
    'a3_0': '#000000',
    'a3_100': '#f6edff',
    'a3_200': '#d6cadf',
    'a3_300': '#b9aec4',
    'a3_400': '#9d93a9',
    'a3_500': '#827990',
    'a3_600': '#686077',
    'a3_700': '#4e475f',
    'a3_800': '#353048',
    'a3_900': '#1c1b1f',
    
    # Предопределенные Material цвета
    'mWhite': '#ffffff',
    'mBlack': '#000000',
    'mGreen500': '#4caf50',
    'mRed200': '#ef9a9a',
    'mRed500': '#f44336',
}

def parse_color_value(value, color_vars=None):
    """Парсит значение цвета из Android темы"""
    if color_vars is None:
        color_vars = {}
    
    value = value.strip()
    
    # Если это уже hex цвет
    if value.startswith('#'):
        return value
    
    # Если это ссылка на Material Design цвет
    if value in MATERIAL_COLORS:
        return MATERIAL_COLORS[value]
    
    # Если это ссылка на другую переменную
    if value in color_vars:
        return parse_color_value(color_vars[value], color_vars)
    
    # Обработка значения с альфа-каналом в скобках
    match = re.match(r'(.+?)\s*\(a=(\d+)\)', value)
    if match:
        base = match.group(1).strip()
        alpha = int(match.group(2))
        base_color = parse_color_value(base, color_vars)
        if base_color and base_color.startswith('#'):
            rgb = base_color.lstrip('#')[:6]
            alpha_hex = format(int(alpha * 255 / 100), '02x')
            return f'#{rgb}{alpha_hex}'
    
    # Обработка значения с прозрачностью в формате (l=X)
    match = re.match(r'(.+?)\s*\(l=(\d+)\)', value)
    if match:
        base = match.group(1).strip()
        return parse_color_value(base, color_vars)
    
    # Если это отрицательное hex число
    if value.endswith('h'):
        try:
            hex_str = value[:-1]
            if hex_str.startswith('-'):
                hex_str = hex_str[1:]
            # Конвертируем ARGB в RGB
            num = int(hex_str, 16)
            r = (num >> 16) & 0xFF
            g = (num >> 8) & 0xFF
            b = num & 0xFF
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            pass
    
    # Если это десятичное число (Android ARGB)
    try:
        num = int(value)
        if num < 0:
            num = num & 0xFFFFFFFF
        a = (num >> 24) & 0xFF
        r = (num >> 16) & 0xFF
        g = (num >> 8) & 0xFF
        b = num & 0xFF
        if a < 255 and a > 0:
            return f'#{r:02x}{g:02x}{b:02x}{a:02x}'
        return f'#{r:02x}{g:02x}{b:02x}'
    except:
        pass
    
    # Если ничего не подошло, возвращаем исходное значение
    return value


def load_android_colors(attheme_path):
    """Загружает все цвета из Android темы"""
    colors = {}
    
    with open(attheme_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//') or line == 'end':
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                colors[key] = value
    
    # Второй проход для разрешения ссылок
    resolved = {}
    for key, value in colors.items():
        resolved[key] = parse_color_value(value, colors)
    
    return resolved


def adjust_brightness(color, percent):
    """Регулирует яркость цвета на заданный процент"""
    if not color or not color.startswith('#'):
        return color
    
    color = color.lstrip('#')
    
    # Обработка альфа-канала
    has_alpha = len(color) == 8
    if has_alpha:
        rgb = color[:6]
        alpha = color[6:]
    else:
        rgb = color
        alpha = ''
    
    # Конвертируем в RGB
    try:
        r = int(rgb[0:2], 16)
        g = int(rgb[2:4], 16)
        b = int(rgb[4:6], 16)
    except:
        return '#' + color
    
    # Регулируем яркость
    factor = 1 + (percent / 100)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    
    # Возвращаем hex
    result = f'#{r:02x}{g:02x}{b:02x}'
    if has_alpha:
        result += alpha
    
    return result


def create_desktop_theme(attheme_path, output_path):
    """Создает десктопную тему из Android темы"""
    
    print("Загрузка цветов из Android темы...")
    colors = load_android_colors(attheme_path)
    
    # Определяем основные цвета темы
    primary_color = colors.get('windowBackgroundWhiteBlueText', '#6750a4')
    background = colors.get('windowBackgroundWhite', '#1c1b1f')
    text_color = colors.get('windowBackgroundWhiteBlackText', '#e6e1e5')
    
    # Получаем другие ключевые цвета
    msg_in_bg = colors.get('chat_inBubble', '#2b2930')
    msg_out_bg = colors.get('chat_outBubble', primary_color)
    msg_panel_bg = colors.get('chat_messagePanelBackground', background)
    
    print(f"Основной цвет: {primary_color}")
    print(f"Фон: {background}")
    print(f"Текст: {text_color}")
    
    # Создаем содержимое colors.tdesktop-theme
    theme_content = f"""// Monet Dark Theme - Desktop Version
// Converted from Android theme
// Conversion date: 2026-01-03

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

dialogsBgActive: primaryColor;
dialogsNameFgActive: #ffffff;
dialogsChatIconFgActive: #ffffff;
dialogsDateFgActive: #ffffff;
dialogsTextFgActive: #ffffff;
dialogsTextFgServiceActive: #ffffff;
dialogsDraftFgActive: #ffffff;
dialogsVerifiedIconBgActive: #ffffff;
dialogsVerifiedIconFgActive: primaryColor;
dialogsSendingIconFgActive: #ffffff;
dialogsSentIconFgActive: #ffffff;
dialogsUnreadBgActive: #ffffff;
dialogsUnreadBgMutedActive: #ffffff;
dialogsUnreadFgActive: primaryColor;

dialogsRippleBg: primaryColor;
dialogsRippleBgActive: #ffffff80;

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
    
    # Записываем файл colors.tdesktop-theme
    colors_file = '/home/claude/colors.tdesktop-theme'
    with open(colors_file, 'w', encoding='utf-8') as f:
        f.write(theme_content)
    
    # Создаём фоновое изображение
    try:
        from PIL import Image, ImageDraw
        import math
        
        bg_file = '/home/claude/background.png'
        
        width, height = 1024, 768
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # Получаем цвета из темы
        try:
            bg_hex = background.lstrip('#')
            base_r = int(bg_hex[0:2], 16)
            base_g = int(bg_hex[2:4], 16)
            base_b = int(bg_hex[4:6], 16)
        except:
            base_r, base_g, base_b = 26, 26, 26
        
        try:
            accent_hex = primary_color.lstrip('#')
            accent_r = int(accent_hex[0:2], 16)
            accent_g = int(accent_hex[2:4], 16)
            accent_b = int(accent_hex[4:6], 16)
        except:
            accent_r, accent_g, accent_b = 182, 157, 248
        
        base_color = (base_r, base_g, base_b)
        accent_color = (accent_r, accent_g, accent_b)
        
        # Создаём тонкий градиент
        for y in range(height):
            blend = y / height
            r = int(base_color[0] * (1 - blend * 0.3) + base_color[0] * 1.3 * blend * 0.3)
            g = int(base_color[1] * (1 - blend * 0.3) + base_color[1] * 1.3 * blend * 0.3)
            b = int(base_color[2] * (1 - blend * 0.3) + base_color[2] * 1.3 * blend * 0.3)
            
            r = min(255, max(0, r))
            g = min(255, max(0, g))
            b = min(255, max(0, b))
            
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Добавляем тонкие акцентные круги
        pixels = img.load()
        
        # Большой круг в правом верхнем углу
        cx1, cy1, radius1 = width * 0.85, -height * 0.1, height * 0.6
        for y in range(height):
            for x in range(width):
                dist = math.sqrt((x - cx1)**2 + (y - cy1)**2)
                if dist < radius1:
                    alpha = (1 - dist / radius1) * 0.03
                    r, g, b = pixels[x, y]
                    r = int(r * (1 - alpha) + accent_color[0] * alpha)
                    g = int(g * (1 - alpha) + accent_color[1] * alpha)
                    b = int(b * (1 - alpha) + accent_color[2] * alpha)
                    pixels[x, y] = (r, g, b)
        
        # Маленький круг в левом нижнем углу
        cx2, cy2, radius2 = -width * 0.1, height * 1.1, height * 0.4
        for y in range(height):
            for x in range(width):
                dist = math.sqrt((x - cx2)**2 + (y - cy2)**2)
                if dist < radius2:
                    alpha = (1 - dist / radius2) * 0.02
                    r, g, b = pixels[x, y]
                    r = int(r * (1 - alpha) + accent_color[0] * alpha)
                    g = int(g * (1 - alpha) + accent_color[1] * alpha)
                    b = int(b * (1 - alpha) + accent_color[2] * alpha)
                    pixels[x, y] = (r, g, b)
        
        img.save(bg_file, optimize=True, quality=85)
        print("✓ Фоновое изображение создано")
    except Exception as e:
        print(f"⚠ Не удалось создать фоновое изображение: {e}")
        bg_file = None
    
    # Создаем ZIP архив
    print(f"Создание архива {output_path}...")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(colors_file, 'colors.tdesktop-theme')
        if bg_file and os.path.exists(bg_file):
            zipf.write(bg_file, 'background.png')
            print("✓ Фоновое изображение добавлено в архив")
    
    print(f"✓ Тема успешно создана: {output_path}")
    print(f"\nИнструкция по установке:")
    print("1. Скачайте файл Monet_Dark.tdesktop-theme")
    print("2. Откройте Telegram Desktop")
    print("3. Перетащите файл темы в окно Telegram")
    print("4. Нажмите 'Apply theme' для применения темы")


if __name__ == '__main__':
    attheme_path = '/mnt/user-data/uploads/Monet_Dark.attheme'
    output_path = '/mnt/user-data/outputs/Monet_Dark.tdesktop-theme'
    
    create_desktop_theme(attheme_path, output_path)

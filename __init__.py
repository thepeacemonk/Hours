# -*- coding: utf-8 -*-
# Hours Anki Add-on
#
# Author: PeaceMonk
# License: GNU AGPLv3
#
# This add-on displays a customizable clock widget on the deck browser screen.

import os
import json
import base64
from datetime import datetime, timedelta

from aqt import mw, gui_hooks
from aqt.qt import *
import aqt.deckbrowser

from .settings import SettingsDialog
from . import bento_integration

# --- Configuration ---
ADDON_NAME = "Hours"
ADDON_FOLDER = os.path.dirname(__file__)
CONFIG = mw.addonManager.getConfig(__name__)

# --- Helper Functions ---
def get_font_face_rules(selected_font=None):
    """Generates @font-face rules for the fonts in the web/fonts folder."""
    # Check for both 'web/fonts' and 'fonts' to be more flexible
    possible_dirs = [
        os.path.join(ADDON_FOLDER, "web", "fonts"),
        os.path.join(ADDON_FOLDER, "fonts")
    ]
    
    fonts_dir = None
    for d in possible_dirs:
        if os.path.isdir(d):
            fonts_dir = d
            break
            
    if not fonts_dir:
        return "" # No valid fonts folder found
    
    # The list of font names as they appear in the settings UI, used for matching
    known_fonts = ["Instrument", "Montserrat", "Nunito", "SpaceMono"]
    rules = ""
    
    # Look for .ttf files directly in the fonts folder
    for filename in os.listdir(fonts_dir):
        if filename.lower().endswith(".ttf"):
            basename = os.path.splitext(filename)[0]
            
            # Skip the 'System.ttf' file to avoid conflict with the system font option
            if basename.lower() == "system":
                continue

            # Find which known font family this file belongs to by checking if the
            # filename starts with one of the known names.
            font_family_name = None
            for known_name in known_fonts:
                if basename.lower().startswith(known_name.lower()):
                    font_family_name = known_name
                    break
            
            # If a matching font family is found, create the @font-face rule for it
            if font_family_name:
                if selected_font and font_family_name.lower() != selected_font.lower():
                    continue
                font_path = os.path.join(fonts_dir, filename).replace("\\", "/")
                try:
                    with open(font_path, "rb") as f:
                        encoded_font = base64.b64encode(f.read()).decode('utf-8')
                    rules += f"""
                        @font-face {{
                            font-family: '{font_family_name}';
                            src: url(data:font/truetype;charset=utf-8;base64,{encoded_font});
                        }}
                    """
                except Exception:
                    # Fails silently if a font file is corrupted or unreadable
                    pass
    return rules

def hex_to_rgba(hex_code, alpha):
    """Converts a hex color code to an rgba string."""
    hex_code = hex_code.lstrip('#')
    if len(hex_code) == 3:
        hex_code = "".join([c*2 for c in hex_code])
    if len(hex_code) != 6:
        return f"rgba(0, 0, 0, {alpha})" # Fallback for invalid hex
    try:
        r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"
    except ValueError:
        return f"rgba(0, 0, 0, {alpha})"


# --- HTML & CSS Generation ---
def generate_css(is_dark=None, config=None):
    """Generate production clock CSS with optional preview inputs."""
    if is_dark is None:
        is_dark = mw.pm.night_mode()
    conf = config if isinstance(config, dict) else CONFIG
    
    opacity = conf.get("bg_opacity", 0.85)
    font = conf.get("font", "System")
    clock_color = conf.get("clock_color", "#FFFFFF")

    # Handle system font
    if font == "System":
        font_family_str = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
    else:
        font_family_str = f"'{font}', -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif"

    # Background styles
    background_style = ""
    pseudo_element_style = ""

    if conf.get("use_bg_image", False) and conf.get("bg_image"):
        img_path = os.path.join(ADDON_FOLDER, "user_files", "watch_gallery", conf["bg_image"])
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                encoded_img = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(conf["bg_image"])[1][1:].lower()
            mime_type = f"image/{'gif' if ext == 'gif' else 'png'}"
            image_url = f"data:{mime_type};base64,{encoded_img}"

            # Create the pseudo-element style for the background image
            pseudo_element_style = f"""
                #watch-container::before {{
                    content: '';
                    position: absolute;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: url('{image_url}') center/cover;
                    opacity: {opacity};
                    border-radius: 24px;
                    z-index: 1;
                }}
            """
            # Ensure the main container itself is transparent
            background_style = "background-color: transparent;"

    elif conf.get("use_bg_gradient", False):
        start = conf.get("bg_gradient_start", "#6a11cb")
        end = conf.get("bg_gradient_end", "#2575fc")
        background_style = f"background: linear-gradient(135deg, {hex_to_rgba(start, opacity)}, {hex_to_rgba(end, opacity)});"
    elif conf.get("use_bg_color", True):
         background_style = f"background-color: {hex_to_rgba(conf.get('bg_color', '#333333'), opacity)};"

    style = conf.get("style", "Classic")
    style_css = ""
    if style == "Classic": # Centered, stacked
        style_css = """
            #watch-time { flex-direction: column; line-height: 0.9; }
            #watch-hours, #watch-minutes { font-size: 72px; }
        """
    elif style == "Flip Clock":
        bg_color_obj = QColor(conf.get('bg_color', '#333333'))
        card_bg = bg_color_obj.darker(120).name()

        style_css = f"""
            /* New animation keyframes for a simpler flip effect */
            @keyframes simple-flip {{
                0% {{
                    opacity: 1;
                    transform: translateY(0);
                }}
                49% {{
                    opacity: 0;
                    transform: translateY(-25px);
                }}
                50% {{
                    opacity: 0;
                    transform: translateY(25px);
                }}
                100% {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}

            #watch-time-container {{
                /* Remove perspective as it's not needed for 2D animation */
            }}

            #watch-time {{
                display: flex;
                gap: 8px;
            }}
            #watch-minutes-container {{
                display: flex;
                align-items: baseline;
                justify-content: center;
            }}
            #watch-ampm {{
                font-size: 24px;
                font-weight: 500;
                opacity: 0.8;
                padding-left: 8px;
            }}

            /* Simplified flip unit styling */
            .flip-unit {{
                position: relative;
                width: 85px;
                height: 90px;
                font-size: 50px;
                line-height: 90px;
                font-weight: bold;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                background-color: {card_bg};
                overflow: hidden; 
            }}

            /* Animation trigger class */
            .flip-unit.flipping {{
                animation: simple-flip 0.6s ease-in-out;
            }}
        """
    elif style == "Analog":
        second_hand_color = conf.get("second_hand_color", "#ff4d4d")
        style_css = f"""
            #watch-time-container {{
                overflow: visible;
            }}
            #analog-clock {{
                width: 150px;
                height: 150px;
                border: 4px solid {clock_color};
                border-radius: 50%;
                position: relative;
                flex-shrink: 0; /* Prevents shrinking inside flex container */
            }}
            .clock-hand {{
                position: absolute;
                bottom: 50%;
                left: 50%;
                transform-origin: bottom;
                border-radius: 2px;
            }}
            #hour-hand {{
                width: 5px;
                height: 40px;
                background-color: {clock_color};
                z-index: 3;
            }}
            #minute-hand {{
                width: 3px;
                height: 60px;
                background-color: {clock_color};
                z-index: 4;
            }}
            #second-hand {{
                width: 2px;
                height: 65px;
                background-color: {second_hand_color};
                z-index: 5;
            }}
            .center-dot {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 10px;
                height: 10px;
                background-color: {second_hand_color};
                border-radius: 50%;
                z-index: 6;
            }}
            .analog-hour-marker {{
                position: absolute;
                width: 2px;
                height: 8px;
                background-color: {clock_color};
            }}
            .analog-hour-num {{
                position: absolute;
                width: 30px;
                height: 30px;
                text-align: center;
                line-height: 30px;
                font-size: 16px;
                font-weight: bold;
                color: {clock_color};
                opacity: 0;
                transition: opacity 0.3s ease;
                z-index: 1;
            }}
            #watch-container:hover .analog-hour-num {{
                opacity: 1;
            }}
        """

    return f"""
        {get_font_face_rules(font)}
        {pseudo_element_style}
        #watch-container {{
            width: 200px;
            height: 200px;
            border-radius: 24px;
            overflow: hidden;
            position: relative;
            margin: 20px auto;
            color: {clock_color};
            font-family: {font_family_str};
            font-weight: 500;
            box-shadow: none !important;
            {background_style}
        }}
        #watch-time-container {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            position: relative;
            z-index: 2;
        }}
        #watch-time {{
            display: flex;
        }}
        {style_css}
        {bento_integration.sizing_css("#watch-container", "#watch-container", conf)}
    """

def generate_html(config=None):
    """Generate production clock markup with optional in-progress settings."""
    conf = config if isinstance(config, dict) else CONFIG
    gmt_offset_hours = conf.get("gmt_offset_hours", 0)
    # Convert hours to minutes for easier JS handling
    gmt_offset_minutes = int(gmt_offset_hours * 60)
    time_format = conf.get("time_format", "24-Hour")
    use_12_hour_js = 'true' if time_format == "12-Hour" else 'false'

    style = conf.get("style", "Classic")

    if style != "Flip Clock" and style != "Analog":
        return f"""
            <div id="watch-time-container">
                <div id="watch-time">
                    <div id="watch-hours">--</div>
                    <div id="watch-minutes-container">
                        <div id="watch-minutes">--</div>
                        <div id="watch-ampm"></div>
                    </div>
                </div>
            </div>
            <script>
                (function() {{
                    const hoursEl = document.getElementById('watch-hours');
                    const minutesEl = document.getElementById('watch-minutes');
                    const ampmEl = document.getElementById('watch-ampm');
                    const gmtOffsetMinutes = {gmt_offset_minutes};
                    const use12Hour = {use_12_hour_js};

                    function updateClock() {{
                        try {{
                            const now = new Date();
                            const utc = now.getTime() + (now.getTimezoneOffset() * 60000); // Convert to UTC milliseconds
                            const localTime = new Date(utc + (gmtOffsetMinutes * 60000)); // Apply GMT offset

                            let hours = localTime.getHours();
                            let minutes = localTime.getMinutes();
                            let ampm = '';

                            if (use12Hour) {{
                                ampm = hours >= 12 ? 'PM' : 'AM';
                                hours = hours % 12;
                                hours = hours ? hours : 12; // The hour '0' should be '12'
                            }}

                            hours = hours < 10 ? '0' + hours : hours;
                            minutes = minutes < 10 ? '0' + minutes : minutes;

                            if (hoursEl.textContent !== hours.toString()) hoursEl.textContent = hours.toString();
                            if (minutesEl.textContent !== minutes.toString()) minutesEl.textContent = minutes.toString();
                            if (use12Hour && ampmEl.textContent !== ampm) ampmEl.textContent = ampm;

                        }} catch (e) {{
                            hoursEl.textContent = 'ER'; minutesEl.textContent = 'TZ'; clearInterval(clockInterval);
                        }}
                    }}
                    updateClock();
                    const clockInterval = setInterval(updateClock, 1000);
                }})();
            </script>
        """

    elif style == "Flip Clock": # Flip Clock HTML and JS with simplified animation
        return f"""
            <div id="watch-time-container">
                <div id="watch-time">
                    <div id="flip-hours" class="flip-unit">--</div>
                    <div id="flip-minutes" class="flip-unit">--</div>
                </div>
            </div>
            <script>
                (function() {{
                    const gmtOffsetMinutes = {gmt_offset_minutes};
                    const use12Hour = {use_12_hour_js};
                    let prevHours = null, prevMinutes = null;

                    const hoursEl = document.getElementById('flip-hours');
                    const minutesEl = document.getElementById('flip-minutes');

                    function updateClock() {{
                        let hours, minutes;
                        try {{
                            const now = new Date();
                            const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
                            const localTime = new Date(utc + (gmtOffsetMinutes * 60000));

                            hours = localTime.getHours();
                            minutes = localTime.getMinutes();

                            if (use12Hour) {{
                                hours = hours % 12;
                                hours = hours ? hours : 12;
                            }}

                            hours = hours < 10 ? '0' + hours : hours;
                            minutes = minutes < 10 ? '0' + minutes : minutes;

                        }} catch(e) {{
                            hours = 'ER'; minutes = 'TZ'; clearInterval(clockInterval);
                        }}

                        if (prevHours === null) {{ // First run, set initial state
                            hoursEl.textContent = hours;
                            minutesEl.textContent = minutes;
                        }} else {{
                            // Animate hours if they changed
                            if (hours !== prevHours) {{
                                hoursEl.classList.add('flipping');
                                setTimeout(() => {{ hoursEl.textContent = hours; }}, 300); 
                                hoursEl.addEventListener('animationend', () => {{
                                    hoursEl.classList.remove('flipping');
                                }}, {{ once: true }});
                            }}
                            // Animate minutes if they changed
                            if (minutes !== prevMinutes) {{
                                minutesEl.classList.add('flipping');
                                setTimeout(() => {{ minutesEl.textContent = minutes; }}, 300);
                                minutesEl.addEventListener('animationend', () => {{
                                    minutesEl.classList.remove('flipping');
                                }}, {{ once: true }});
                            }}
                        }}

                        prevHours = hours;
                        prevMinutes = minutes;
                    }}

                    updateClock();
                    const clockInterval = setInterval(updateClock, 1000);
                }})();
            </script>
        """
    
    elif style == "Analog":
        return f"""
            <div id="watch-time-container">
                <div id="analog-clock">
                    <div class="center-dot"></div>
                    <div id="hour-hand" class="clock-hand"></div>
                    <div id="minute-hand" class="clock-hand"></div>
                    <div id="second-hand" class="clock-hand"></div>
                </div>
            </div>
            <script>
                (function() {{
                    const gmtOffsetMinutes = {gmt_offset_minutes};
                    const analogClock = document.getElementById('analog-clock');
                    const hourHand = document.getElementById('hour-hand');
                    const minuteHand = document.getElementById('minute-hand');
                    const secondHand = document.getElementById('second-hand');

                    // Generate markers and numbers dynamically
                    for (let i = 1; i <= 12; i++) {{
                        const angle = i * 30;
                        
                        const marker = document.createElement('div');
                        marker.className = 'analog-hour-marker';
                        marker.style.transform = `translate(-50%, -50%) rotate(${{angle}}deg) translateY(-67px)`;
                        marker.style.top = '50%';
                        marker.style.left = '50%';
                        analogClock.appendChild(marker);

                        const number = document.createElement('div');
                        number.className = 'analog-hour-num';
                        number.textContent = i;
                        const rad = (angle - 90) * (Math.PI / 180); // Offset by -90deg to start from top
                        const x = 90 * Math.cos(rad);
                        const y = 90 * Math.sin(rad);
                        number.style.transform = `translate(-50%, -50%) translate(${{x}}px, ${{y}}px)`;
                        number.style.top = '50%';
                        number.style.left = '50%';
                        analogClock.appendChild(number);
                    }}

                    function setClock() {{
                        let now, hours, minutes, seconds;
                        try {{
                            now = new Date();
                            const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
                            const localTime = new Date(utc + (gmtOffsetMinutes * 60000));

                            hours = localTime.getHours();
                            minutes = localTime.getMinutes();
                            seconds = localTime.getSeconds();
                            if (hours === 24) hours = 0; // Handle midnight case
                        }} catch (e) {{
                            clearInterval(clockInterval);
                            return;
                        }}

                        const secondsRatio = seconds / 60;
                        const minutesRatio = (secondsRatio + minutes) / 60;
                        const hoursRatio = (minutesRatio + hours) / 12;

                        secondHand.style.transform = `translateX(-50%) rotate(${{secondsRatio * 360}}deg)`;
                        minuteHand.style.transform = `translateX(-50%) rotate(${{minutesRatio * 360}}deg)`;
                        hourHand.style.transform = `translateX(-50%) rotate(${{hoursRatio * 360}}deg)`;
                    }}

                    setClock();
                    const clockInterval = setInterval(setClock, 1000);
                }})();
            </script>
        """

# --- Anki Integration ---
cached_html = None

def add_clock_to_deck_browser(deck_browser: aqt.deckbrowser.DeckBrowser, content: aqt.deckbrowser.DeckBrowserContent):
    """Appends the clock widget to the deck browser's stats area."""
    global cached_html

    # Prevent adding the clock multiple times during a single refresh cycle
    if "<div id='watch-container'>" in content.stats:
        return
    
    if cached_html is None:
        css = generate_css()
        html_content = generate_html()
        cached_html = f"<div id='watch-container'><style>{css}</style>{html_content}</div>"

    content.stats += cached_html

def reset_cache(*args, **kwargs):
    """Clears the cached HTML, forcing a refresh on next view."""
    global cached_html
    cached_html = None

def on_theme_change():
    """Reset cache and refresh deck browser when theme changes."""
    reset_cache()
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()



_is_settings_open = False
def debounce_settings(func):
    def wrapper(*args, **kwargs):
        global _is_settings_open
        if _is_settings_open:
            return
        _is_settings_open = True
        try:
            return func()
        finally:
            _is_settings_open = False
    return wrapper

@debounce_settings
def show_settings():
    """Show the settings dialog."""
    # Pass the add-on's global CONFIG object and package name to the dialog
    dialog = SettingsDialog(mw, config=CONFIG, addon_package=__name__)
    dialog.exec()

# --- Hooks and Menu ---
gui_hooks.deck_browser_will_render_content.append(add_clock_to_deck_browser)
gui_hooks.reviewer_will_end.append(reset_cache)
gui_hooks.sync_did_finish.append(reset_cache)
gui_hooks.theme_did_change.append(on_theme_change)

bento_integration.register_widget("Hours", settings_callback=show_settings)
bento_integration.add_menu_action("Hours Settings", show_settings)

# --- START OF FILE settings.py ---
import copy
import os
import shutil
import importlib
from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, QFormLayout,
    QColorDialog, QColor, QSlider, QSpinBox, Qt, QPixmap, QScrollArea, QLineEdit,
    pyqtSignal, QFrame, QButtonGroup, QAbstractButton, QApplication, QCheckBox,
    QDesktopServices, QGridLayout, QIcon, QFileDialog, QTimer
)
try:
    from PyQt6.QtCore import pyqtProperty, QPropertyAnimation, QEasingCurve, QRectF, QParallelAnimationGroup, QPointF, QUrl, QSize
    from PyQt6.QtGui import QPainter, QPen, QColor as QColor2, QPainterPath, QFont, QBrush
    from PyQt6.QtWidgets import QStyleOption, QStyle, QSizePolicy
except ImportError:
    from PyQt5.QtCore import pyqtProperty, QPropertyAnimation, QEasingCurve, QRectF, QParallelAnimationGroup, QPointF, QUrl, QSize
    from PyQt5.QtGui import QPainter, QPen, QColor as QColor2, QPainterPath, QFont, QBrush
    from PyQt5.QtWidgets import QStyleOption, QStyle, QSizePolicy
from aqt.utils import showInfo
from aqt.theme import theme_manager
from aqt.webview import AnkiWebView
from . import bento_integration

# --- Shared UI Components (from Berry design) ---
class AnimatedToggleButton(QAbstractButton):
    def __init__(self, parent=None, accent_color="#ff4d4d"):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accent_color = QColor(accent_color)
        self.track_color_off = QColor("#cccccc") if not theme_manager.night_mode else QColor("#555555")
        self.thumb_color = QColor("#ffffff")
        self.setFixedSize(38, 20)
        self._thumb_x_pos = 3.0
        self.animation = QPropertyAnimation(self, b"thumb_x_pos", self)
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._start_animation)

    @pyqtProperty(float)
    def thumb_x_pos(self):
        return self._thumb_x_pos

    @thumb_x_pos.setter
    def thumb_x_pos(self, value):
        self._thumb_x_pos = value
        self.update()

    def _start_animation(self, checked):
        end_pos = self.width() - self.height() + 3 if checked else 3
        self.animation.setStartValue(self.thumb_x_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height = self.height()
        radius = height / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        track_color = self.accent_color if self.isChecked() else self.track_color_off
        painter.setBrush(track_color)
        painter.drawRoundedRect(self.rect(), radius, radius)
        thumb_radius = radius - 3
        painter.setBrush(self.thumb_color)
        thumb_y = radius
        painter.drawEllipse(QPointF(self._thumb_x_pos + thumb_radius, thumb_y), thumb_radius, thumb_radius)

    def showEvent(self, event):
        super().showEvent(event)
        self._thumb_x_pos = self.width() - self.height() + 3 if self.isChecked() else 3
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._thumb_x_pos = self.width() - self.height() + 3 if self.isChecked() else 3
class ModernSlider(QSlider):
    def __init__(self, accent_color="#ff4d4d", parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.accent_color = QColor(accent_color)
        self.setMinimumHeight(24)

    def _theme_tokens(self):
        curr = self.parent()
        while curr:
            if hasattr(curr, "_theme_tokens"):
                return curr._theme_tokens()
            curr = curr.parent()
        return {
            "border": "#d1d5db" if not theme_manager.night_mode else "#444444",
            "surface": "#eaeaea" if not theme_manager.night_mode else "#2d2d2d",
        }

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        enabled = self.isEnabled()
        w = self.width()
        h = self.height()
        
        # Track parameters
        track_h = 18
        track_y = (h - track_h) // 2
        track_rx = track_h // 2
        
        min_val = self.minimum()
        max_val = self.maximum()
        val = self.value()
        
        range_val = max_val - min_val
        if range_val <= 0:
            range_val = 1
            
        handle_d = 12
        padding_x = 9
        
        x_min = padding_x
        x_max = w - padding_x
        pct = (val - min_val) / range_val
        handle_cx = x_min + pct * (x_max - x_min)
        
        # Get background color from tokens
        tokens = self._theme_tokens()
        bg_color_hex = tokens.get("surface", "#eaeaea")
        bg_color = QColor(bg_color_hex)
        
        if enabled:
            active_color = self.accent_color
        else:
            active_color = QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 76)
            bg_color.setAlpha(76)
            
        # Draw background track
        track_rect = QRectF(0, track_y, w, track_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(track_rect, track_rx, track_rx)
        
        # Draw active (red) track
        active_right = handle_cx + 10
        if active_right > w:
            active_right = w
        if active_right < track_rx * 2:
            active_right = track_rx * 2
            
        active_rect = QRectF(0, track_y, active_right, track_h)
        painter.setBrush(active_color)
        painter.drawRoundedRect(active_rect, track_rx, track_rx)
        
        # Draw handle (white circle centered at handle_cx)
        handle_cy = track_y + track_h / 2
        handle_color = QColor("#ffffff") if enabled else QColor(255, 255, 255, 120)
        painter.setBrush(handle_color)
        painter.drawEllipse(QPointF(handle_cx, handle_cy), 6, 6)

class GooeySegmentedControl(QWidget):
    def __init__(self, accent_color="#ff4d4d", parent=None):
        super().__init__(parent)
        self.setObjectName("themeToggleContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(0)
        self._accent_color = QColor(accent_color)
        self._indicator_rect = QRectF(4, 4, 0, 0)
        self.anim_group = QParallelAnimationGroup(self)
        self.anim_x = QPropertyAnimation(self, b"indicator_x")
        self.anim_width = QPropertyAnimation(self, b"indicator_width")
        self.anim_group.addAnimation(self.anim_x)
        self.anim_group.addAnimation(self.anim_width)
        self.anim_x.setEasingCurve(QEasingCurve.Type.InOutBack)
        self.anim_width.setEasingCurve(QEasingCurve.Type.InOutBack)
        self.anim_x.setDuration(400)
        self.anim_width.setDuration(400)
        self.button_group = QButtonGroup(self)
        self.button_group.buttonClicked.connect(self.animate_to)

    @pyqtProperty(float)
    def indicator_x(self):
        return self._indicator_rect.x()

    @indicator_x.setter
    def indicator_x(self, value):
        self._indicator_rect.setX(value)
        self.update()

    @pyqtProperty(float)
    def indicator_width(self):
        return self._indicator_rect.width()

    @indicator_width.setter
    def indicator_width(self, value):
        self._indicator_rect.setWidth(value)
        self.update()

    def add_button(self, btn):
        self._layout.addWidget(btn)
        self.button_group.addButton(btn)

    def current_text(self):
        btn = self.button_group.checkedButton()
        return btn.text() if btn else ""

    def animate_to(self, btn):
        if not btn: return
        target_rect = btn.geometry()
        if target_rect.width() == 0: return
        self.anim_x.setStartValue(self.indicator_x)
        self.anim_x.setEndValue(float(target_rect.x()))
        self.anim_width.setStartValue(self.indicator_width)
        self.anim_width.setEndValue(float(target_rect.width()))
        self.anim_group.start()

    def update_indicator_no_animation(self):
        checked_btn = self.button_group.checkedButton()
        if checked_btn and checked_btn.geometry().width() > 0:
            r = checked_btn.geometry()
            self._indicator_rect.setX(r.x())
            self._indicator_rect.setWidth(r.width())
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_indicator_no_animation()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            from PyQt6.QtCore import QTimer
        except ImportError:
            from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, self.update_indicator_no_animation)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        if self._indicator_rect.width() > 0:
            # The slide animation's InOutBack easing overshoots past its
            # target (that's what gives it the "gooey" bounce), which can push
            # the indicator's rounded corner past x=0 mid-animation. Clipping
            # to the container's own rounded shape (rather than the widget's
            # plain rectangular bounds) means any overshoot gets bounded by
            # the pill's curve instead of being sliced off into a flat edge.
            track_path = QPainterPath()
            track_radius = self.height() / 2.0
            track_path.addRoundedRect(QRectF(self.rect()), track_radius, track_radius)
            p.setClipPath(track_path)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._accent_color)
            checked_btn = self.button_group.checkedButton()
            h = checked_btn.geometry().height() if checked_btn else 28
            y = checked_btn.geometry().y() if checked_btn else 4
            rect = QRectF(self._indicator_rect.x(), float(y), self._indicator_rect.width(), float(h))
            p.drawRoundedRect(rect, 14.0, 14.0)

class SectionGroup(QWidget):
    def __init__(self, title="", parent=None, description=""):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 5, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 17px; margin-bottom: 2px;")
        main_layout.addWidget(title_label)
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("font-size: 11px; color: #888; margin-bottom: 5px;")
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label)
        self.content_area = QWidget()
        self.content_area.setObjectName("innerGroup")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(10)
        main_layout.addWidget(self.content_area)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

# --- Hours Custom Widgets ---

class ImagePreviewButton(QPushButton):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("galleryImageBtn")
        self.image_path = image_path
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x = (scaled_pixmap.width() - 100) / 2
        y = (scaled_pixmap.height() - 100) / 2
        cropped_pixmap = scaled_pixmap.copy(int(x), int(y), 100, 100)
        rounded = QPixmap(cropped_pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)
        path = QPainterPath()
        path.addRoundedRect(0, 0, cropped_pixmap.width(), cropped_pixmap.height(), 12, 12)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped_pixmap)
        painter.end()
        self.setIcon(QIcon(rounded))
        self.setIconSize(QSize(90, 90))


# ─── Live Preview ────────────────────────────────────────────────────────────

# Hours' widget is a single fixed-footprint container (#watch-container is
# hardcoded to 200x200px in generate_css() regardless of clock style), so
# unlike Global there's no per-view-mode natural-size dict or grid-footprint
# label needed here.
_NATURAL_W, _NATURAL_H = 200, 200


class HoursPreviewWidget(QWidget):
    """Renders a live HTML preview of the Hours clock widget.

    The clock ticks via its own embedded JS (setInterval in generate_html()),
    so once the HTML is loaded into the webview it keeps updating on its own —
    no Python-side re-render timer is needed to avoid a frozen/stale preview.
    """

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        self.preview_layout = QVBoxLayout(self)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)

        self.webview = None

        # The centering/scale math is baked into the generated HTML from Qt's
        # actual widget size (see refresh()), so it has to be regenerated
        # whenever that size changes rather than trying to adapt in JS.
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.refresh)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(120)

    def cleanup(self):
        """Release the embedded AnkiWebView before this widget is destroyed.

        AnkiWebView wraps a QWebEngineView; if it is left to be torn down
        implicitly during Python interpreter finalization (Anki quitting),
        Qt dereferences already-freed child widgets and segfaults. Cleaning
        it up explicitly on dialog close avoids that.
        """
        if getattr(self, "_resize_timer", None) is not None:
            self._resize_timer.stop()
        if getattr(self, "webview", None) is not None:
            if getattr(self, "webview", None):
                self.webview.cleanup()
            self.webview = None


    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "webview", None) is None:
            self.webview = AnkiWebView(title="hours_preview", parent=self)
            self.webview.setMinimumSize(260, 300)
            self.webview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.webview.disable_zoom()
            page = self.webview.page()
            page.setBackgroundColor(QColor(0, 0, 0, 0))
            self.preview_layout.addWidget(self.webview)
            self.refresh()

    def refresh(self):
        if not getattr(self, "webview", None):
            return
        addon_module = importlib.import_module(__package__)
        is_dark = theme_manager.night_mode

        # generate_css()/generate_html() read the add-on's module-level CONFIG
        # directly (no config/theme args), so make sure that CONFIG reflects
        # this dialog's in-progress edits before calling them.
        addon_module.CONFIG.clear()
        addon_module.CONFIG.update(self.config)

        css = addon_module.generate_css()
        html_content = addon_module.generate_html()

        # Behind the widget: Onigiri's actual deck-browser wallpaper when the
        # integration is active, otherwise the same flat color as this dialog.
        settings_bg = "#181818" if is_dark else "#f7f7f7"
        wallpaper = None
        if bento_integration.is_onigiri_detected():
            wallpaper = bento_integration.main_menu_wallpaper(is_dark)
        if not wallpaper:
            wallpaper = {"kind": "color", "color": settings_bg}

        if wallpaper["kind"] == "image":
            bg_layer_css = f"""
                background-color: {wallpaper['color']};
                background-image: url('{wallpaper['url']}');
                background-size: cover; background-position: center; background-repeat: no-repeat;
                filter: blur({wallpaper['blur_px']}px);
                opacity: {wallpaper['opacity']};
            """
        else:
            bg_layer_css = f"background-color: {wallpaper['color']}; opacity: 1;"

        # Fit-to-panel is computed entirely here in Python and baked into the
        # CSS below as literal numbers — no runtime JS measurement of the page
        # (scrollWidth/window.innerWidth/etc.) is involved.
        natural_w, natural_h = _NATURAL_W, _NATURAL_H

        panel_w = self.webview.width()
        panel_h = self.webview.height()
        if panel_w < 100 or panel_h < 100:
            panel_w, panel_h = 320, 400

        avail_w = panel_w - 40
        avail_h = panel_h - 40
        factor = min(1.0, avail_w / natural_w, avail_h / natural_h) * 0.94
        # +2px so sub-pixel rendering of the scaled content (fractional
        # `transform: scale()` output) can never end up a hair taller/wider
        # than the box it's clipped to.
        final_w = natural_w * factor + 2
        final_h = natural_h * factor + 2

        full_html = f"""
        <html><head><style>
            html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background: transparent; }}
            body {{
                position: relative;
                display: flex; align-items: center; justify-content: center;
                background: transparent;
            }}
            #onigiri-bg-container {{
                position: absolute; inset: 10px; z-index: 0;
                border-radius: 20px; overflow: hidden;
                transform: translateZ(0);
            }}
            #onigiri-bg-layer {{
                position: absolute; inset: -50px;
                {bg_layer_css}
            }}
            /* Only the box's own size (final_w/final_h) comes from Python;
               centering it is left entirely to flexbox on <body> above,
               rather than computing left/top ourselves. No overflow:hidden
               here: if the estimate falls a hair short, the card should
               spill slightly into the margin rather than have its rounded
               edge sliced flat. */
            #scale-wrapper {{
                position: relative; z-index: 1;
                width: {final_w}px; height: {final_h}px;
                flex-shrink: 0;
            }}
            #watch-container {{
                position: absolute; top: 0; left: 0;
                transform: scale({factor}); transform-origin: top left;
                margin: 0 !important;
            }}
        </style></head>
        <body>
            <div id="onigiri-bg-container">
                <div id="onigiri-bg-layer"></div>
            </div>
            <div id="scale-wrapper">
                <style>{css}</style>
                <div id="watch-container">{html_content}</div>
            </div>
        </body></html>
        """
        self.webview.setHtml(full_html)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, config=None, addon_package=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("Hours Settings")
        
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.resize(int(avail.width() * 0.5), int(avail.height() * 0.55))
        else:
            self.resize(820, 600)
        self.setMinimumSize(760, 500)

        self.addon_package = addon_package
        self.config = config
        self.addon_dir = os.path.dirname(__file__)
        self.gallery_dir = os.path.join(self.addon_dir, "user_files", "watch_gallery")
        if not os.path.exists(self.gallery_dir):
            os.makedirs(self.gallery_dir)

        self.setup_ui()
        self.refresh_gallery()
        QTimer.singleShot(0, self._refresh_preview)

        # Tear down the embedded AnkiWebView and schedule the dialog for
        # deletion when it closes, so it does not linger as a child of the
        # main window with a live QWebEngineView (which segfaults during
        # interpreter shutdown). deleteLater() is used instead of
        # WA_DeleteOnClose because this dialog is shown with exec(): a
        # WA_DeleteOnClose delete happens inside the modal loop and frees the
        # dialog while exec() is still unwinding, which itself crashes.
        self.finished.connect(self._cleanup_on_close)

    def _cleanup_on_close(self, *args):
        preview = getattr(self, "preview_widget", None)
        if preview is not None:
            preview.cleanup()
        self.deleteLater()

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            qr = self.frameGeometry()
            cp = avail.center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())

    def _theme_tokens(self):
        is_dark = theme_manager.night_mode
        accent = "#ff4d4d" # Hours accent
        if is_dark:
            return {"bg": "#181818", "panel": "#242424", "surface": "#303030", "fg": "#f4f4f5", "muted": "#c4c4c4", "border": "#454545", "accent": accent}
        return {"bg": "#f7f7f7", "panel": "#ffffff", "surface": "#f2f2f2", "fg": "#202124", "muted": "#6f7177", "border": "#dcdde1", "accent": accent}

    def setup_ui(self):
        tokens = self._theme_tokens()
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main controls container
        controls_outer = QWidget()
        controls_outer.setObjectName("controlsOuter")
        controls_outer.setMinimumWidth(460)
        controls_outer_layout = QVBoxLayout(controls_outer)
        controls_outer_layout.setContentsMargins(0, 10, 0, 0)
        controls_outer_layout.setSpacing(0)

        controls_container = QFrame()
        controls_container.setObjectName("controlsContainer")
        controls_container.setFrameShape(QFrame.Shape.NoFrame)
        controls_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        controls_container_layout = QVBoxLayout(controls_container)
        controls_container_layout.setContentsMargins(0, 0, 0, 0)
        controls_container_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("controlsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(16, 24, 16, 20)
        scroll_layout.setSpacing(20)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Style Section
        style_section = SectionGroup("Clock Style", self)
        self.style_control = GooeySegmentedControl(tokens["accent"], self)
        for s in ["Classic", "Flip Clock", "Analog"]:
            btn = QPushButton(s)
            btn.setCheckable(True)
            btn.setObjectName("themeToggleButton")
            btn.setFixedHeight(28)
            if self.config.get("style", "Classic") == s:
                btn.setChecked(True)
            self.style_control.add_button(btn)
        style_section.add_widget(self.style_control)
        scroll_layout.addWidget(style_section)

        # Font Section
        font_section = SectionGroup("Font", self)
        font_buttons_container = QWidget()
        font_buttons_container.setObjectName("FontButtonsGrid")
        font_layout = QGridLayout(font_buttons_container)
        font_layout.setContentsMargins(0, 0, 0, 0)
        font_layout.setSpacing(10)

        self.font_button_group = QButtonGroup(self)
        self.font_button_group.setExclusive(True)
        fonts = ["Instrument", "Montserrat", "Nunito", "SpaceMono", "System"]
        positions = [(i, j) for i in range(2) for j in range(3)]
        for position, name in zip(positions, fonts):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setObjectName("fontButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if self.config.get("font", "System") == name:
                btn.setChecked(True)
            self.font_button_group.addButton(btn)
            font_layout.addWidget(btn, *position)
        font_section.add_widget(font_buttons_container)
        scroll_layout.addWidget(font_section)

        # Colors Section
        colors_section = SectionGroup("Colors", self)
        colors_layout = QVBoxLayout()
        colors_layout.setContentsMargins(0, 0, 0, 0)
        colors_layout.setSpacing(10)

        # Clock/Hands Row
        clock_pill, self.clock_color_input = self._create_color_pill("Clock/Hands Color", "clock_color", "#FFFFFF")
        colors_layout.addWidget(clock_pill)

        # Second Hand Row
        second_pill, self.second_hand_color_input = self._create_color_pill("Second Hand Color", "second_hand_color", "#ff4d4d")
        colors_layout.addWidget(second_pill)

        colors_section.add_layout(colors_layout)
        scroll_layout.addWidget(colors_section)

        # Background Section
        bg_image_section = SectionGroup("Background", self)

        # Background Type Selector (Modern Segmented Control)
        self.bg_type_control = GooeySegmentedControl(tokens["accent"], self)
        
        bg_types = ["Solid", "Gradient", "Image"]
        current_type = "Solid"
        if self.config.get("use_bg_image", False):
            current_type = "Image"
        elif self.config.get("use_bg_gradient", False):
            current_type = "Gradient"
            
        for t_name in bg_types:
            btn = QPushButton(t_name)
            btn.setCheckable(True)
            btn.setObjectName("themeToggleButton")
            btn.setFixedHeight(28)
            if t_name == current_type:
                btn.setChecked(True)
            self.bg_type_control.add_button(btn)
            
        bg_image_section.add_widget(self.bg_type_control)

        # 1. Solid Color Option
        self.solid_container = QWidget()
        solid_layout = QVBoxLayout(self.solid_container)
        solid_layout.setContentsMargins(0, 5, 0, 5)
        solid_layout.setSpacing(0)
        bg_color_pill, self.bg_color_input = self._create_color_pill("Background Color", "bg_color", "#333333")
        solid_layout.addWidget(bg_color_pill)
        bg_image_section.add_widget(self.solid_container)

        # 2. Gradient Option
        self.gradient_container = QWidget()
        gradient_layout = QVBoxLayout(self.gradient_container)
        gradient_layout.setContentsMargins(0, 5, 0, 5)
        gradient_layout.setSpacing(8)

        start_pill, self.gradient_start_input = self._create_color_pill("Start Color", "bg_gradient_start", "#6a11cb")
        gradient_layout.addWidget(start_pill)

        end_pill, self.gradient_end_input = self._create_color_pill("End Color", "bg_gradient_end", "#2575fc")
        gradient_layout.addWidget(end_pill)
        bg_image_section.add_widget(self.gradient_container)

        # 3. Image Option
        self.image_container = QWidget()
        image_layout = QVBoxLayout(self.image_container)
        image_layout.setContentsMargins(0, 5, 0, 5)
        image_layout.setSpacing(10)
        
        self.gallery_container = QFrame()
        self.gallery_container.setObjectName("newColorPill")
        self.gallery_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.gallery_container.setFixedHeight(120)
        
        self.gallery_layout = QHBoxLayout(self.gallery_container)
        self.gallery_layout.setContentsMargins(10, 10, 10, 10)
        self.gallery_layout.setSpacing(10)
        self.gallery_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.gallery_container)

        image_btn_layout = QHBoxLayout()
        image_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.add_image_btn = QPushButton("Add Image")
        self.add_image_btn.clicked.connect(self.add_image)
        self.delete_image_btn = QPushButton("Delete Selected")
        self.delete_image_btn.clicked.connect(self.delete_image)
        image_btn_layout.addWidget(self.add_image_btn)
        image_btn_layout.addWidget(self.delete_image_btn)
        image_btn_layout.addStretch()
        image_layout.addLayout(image_btn_layout)
        bg_image_section.add_widget(self.image_container)

        # 4. Background Opacity (inside Background Section)
        opacity_pill = QFrame()
        opacity_pill.setObjectName("newColorPill")
        opacity_pill.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        opacity_pill.setMinimumHeight(48)
        
        opacity_layout = QHBoxLayout(opacity_pill)
        opacity_layout.setContentsMargins(15, 8, 15, 8)
        opacity_layout.setSpacing(15)

        opacity_label_title = QLabel("Opacity")
        opacity_label_title.setMinimumWidth(80)

        self.opacity_slider = ModernSlider(tokens["accent"], self)
        self.opacity_slider.setObjectName("berrySlider")
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.config.get("bg_opacity", 0.85) * 100))
        self.opacity_slider.setCursor(Qt.CursorShape.PointingHandCursor)

        self.opacity_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_label.setFixedWidth(40)
        self.opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))

        opacity_layout.addWidget(opacity_label_title)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        bg_image_section.add_widget(opacity_pill)

        scroll_layout.addWidget(bg_image_section)

        # Connect background type changes to state updating handler
        self.bg_type_control.button_group.buttonClicked.connect(self._on_bg_type_changed)
        QTimer.singleShot(0, self._on_bg_type_changed)

        # Time Settings
        time_format_section = SectionGroup("Time Format & Offset", self)
        time_format_layout = QVBoxLayout()
        time_format_layout.setContentsMargins(0, 0, 0, 0)
        time_format_layout.setSpacing(10)
        
        self.time_format_control = GooeySegmentedControl(tokens["accent"], self)
        for s in ["12-Hour", "24-Hour"]:
            btn = QPushButton(s)
            btn.setCheckable(True)
            btn.setObjectName("themeToggleButton")
            btn.setFixedHeight(28)
            if self.config.get("time_format", "24-Hour") == s:
                btn.setChecked(True)
            self.time_format_control.add_button(btn)
        time_format_layout.addWidget(self.time_format_control)
        
        # GMT Offset Row
        self.gmt_offset_value = self.config.get("gmt_offset_hours", 0)
        
        # Write temporary SVG files styled with theme colors
        fg_color = tokens.get("fg", "#111827")
        plus_svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
	<path d="M0 0h24v24H0z" fill="none" />
	<path fill="{fg_color}" d="M18 12.998h-5v5a1 1 0 0 1-2 0v-5H6a1 1 0 0 1 0-2h5v-5a1 1 0 0 1 2 0v5h5a1 1 0 0 1 0 2" />
</svg>"""

        minus_svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
	<path d="M0 0h24v24H0z" fill="none" />
	<path fill="{fg_color}" d="M18 12.998H6a1 1 0 0 1 0-2h12a1 1 0 0 1 0 2" />
</svg>"""

        temp_plus_path = os.path.join(self.addon_dir, "assets", "temp_plus.svg")
        temp_minus_path = os.path.join(self.addon_dir, "assets", "temp_minus.svg")
        try:
            with open(temp_plus_path, "w", encoding="utf-8") as f:
                f.write(plus_svg_content)
            with open(temp_minus_path, "w", encoding="utf-8") as f:
                f.write(minus_svg_content)
        except Exception:
            pass

        gmt_pill = QFrame()
        gmt_pill.setObjectName("newColorPill")
        gmt_pill.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        gmt_pill.setMinimumHeight(48)
        
        gmt_pill_layout = QHBoxLayout(gmt_pill)
        gmt_pill_layout.setContentsMargins(15, 8, 15, 8)
        
        gmt_label = QLabel("GMT Offset")
        gmt_label.setStyleSheet(f"font-weight: bold; color: {tokens['fg']};")
        gmt_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        gmt_controls = QWidget()
        gmt_controls_layout = QHBoxLayout(gmt_controls)
        gmt_controls_layout.setContentsMargins(0, 0, 0, 0)
        gmt_controls_layout.setSpacing(10)
        
        self.gmt_minus_btn = QPushButton()
        self.gmt_minus_btn.setObjectName("gmtAdjustBtn")
        self.gmt_minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gmt_minus_btn.setIcon(QIcon(temp_minus_path))
        self.gmt_minus_btn.setIconSize(QSize(16, 16))
        self.gmt_minus_btn.clicked.connect(lambda: self._adjust_gmt_offset(-1))
        
        self.gmt_value_label = QLabel()
        self.gmt_value_label.setStyleSheet(f"font-weight: bold; font-size: 13px; font-family: monospace; color: {tokens['fg']};")
        self.gmt_value_label.setFixedWidth(80)
        self.gmt_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.gmt_plus_btn = QPushButton()
        self.gmt_plus_btn.setObjectName("gmtAdjustBtn")
        self.gmt_plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gmt_plus_btn.setIcon(QIcon(temp_plus_path))
        self.gmt_plus_btn.setIconSize(QSize(16, 16))
        self.gmt_plus_btn.clicked.connect(lambda: self._adjust_gmt_offset(1))
        
        sign = "+" if self.gmt_offset_value > 0 else ""
        self.gmt_value_label.setText(f"{sign}{self.gmt_offset_value} hours" if self.gmt_offset_value != 0 else "0 hours")
        
        gmt_controls_layout.addWidget(self.gmt_minus_btn)
        gmt_controls_layout.addWidget(self.gmt_value_label)
        gmt_controls_layout.addWidget(self.gmt_plus_btn)
        
        gmt_pill_layout.addWidget(gmt_label)
        gmt_pill_layout.addWidget(gmt_controls)
        
        time_format_layout.addWidget(gmt_pill)
        time_format_section.add_layout(time_format_layout)
        scroll_layout.addWidget(time_format_section)

        integration_section, self.bento_width_spin, self.bento_height_spin = bento_integration.create_settings_group(self.config)
        scroll_layout.addWidget(integration_section)

        # Live preview: every control that save_settings() eventually reads
        # also feeds the in-progress preview as soon as it changes.
        self.style_control.button_group.buttonClicked.connect(self._refresh_preview)
        self.font_button_group.buttonClicked.connect(self._refresh_preview)
        self.time_format_control.button_group.buttonClicked.connect(self._refresh_preview)
        self.clock_color_input.textChanged.connect(self._refresh_preview)
        self.second_hand_color_input.textChanged.connect(self._refresh_preview)
        self.bg_color_input.textChanged.connect(self._refresh_preview)
        self.gradient_start_input.textChanged.connect(self._refresh_preview)
        self.gradient_end_input.textChanged.connect(self._refresh_preview)
        self.opacity_slider.valueChanged.connect(self._refresh_preview)
        self.bento_width_spin.valueChanged.connect(self._refresh_preview)
        self.bento_height_spin.valueChanged.connect(self._refresh_preview)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        scroll.viewport().setAutoFillBackground(False)
        scroll_content.setAutoFillBackground(False)
        controls_container.setAutoFillBackground(False)
        controls_container_layout.addWidget(scroll)
        controls_outer_layout.addWidget(controls_container)

        # ── Right: Preview panel ─────────────────────────────────────────
        preview_wrapper = QWidget()
        preview_wrapper.setObjectName("previewWrapper")
        preview_wrapper_layout = QVBoxLayout(preview_wrapper)
        preview_wrapper_layout.setContentsMargins(10, 24, 20, 20)
        preview_wrapper_layout.setSpacing(12)

        preview_title = QLabel("Preview")
        preview_title.setStyleSheet(f"font-size: 12px; font-weight: 700; letter-spacing: 0.6px; color: {tokens['muted']};")
        preview_wrapper_layout.addWidget(preview_title)

        self.preview_widget = HoursPreviewWidget(self._collect_config(), self)
        preview_wrapper_layout.addWidget(self.preview_widget, 1)

        content_h_layout = QHBoxLayout()
        content_h_layout.setSpacing(0)
        content_h_layout.setContentsMargins(0, 0, 0, 0)
        content_h_layout.addWidget(controls_outer, 1)
        content_h_layout.addWidget(preview_wrapper, 1)
        root_layout.addLayout(content_h_layout, 1)

        # Bottom Pill Bar
        bottom_container = QWidget()
        bottom_container.setObjectName("bottomContainer")
        bottom_container_layout = QVBoxLayout(bottom_container)
        bottom_container_layout.setContentsMargins(20, 8, 20, 20)
        
        bottom_bar = QWidget()
        bottom_bar.setObjectName("bottomPillBar")
        bottom_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bottom_bar_layout = QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(10, 10, 10, 10)
        bottom_bar_layout.setSpacing(8)

        logo_label = QLabel()
        logo_path = os.path.join(self.addon_dir, "assets", "hours_logo.svg")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(200, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setFixedSize(scaled_pixmap.size())
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bottom_bar_layout.addWidget(logo_label)

        bottom_bar_layout.addSpacing(8)
        self.donate_button = QPushButton("Donate")
        self.donate_button.setObjectName("cancelButton")
        self.donate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.report_button = QPushButton("Report Bug")
        self.report_button.setObjectName("cancelButton")
        self.report_button.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_bar_layout.addWidget(self.donate_button)
        bottom_bar_layout.addWidget(self.report_button)
        
        self.donate_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://buymeacoffee.com/peacemonk")))
        self.report_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/thepeacemonk/Onigiri")))

        bottom_bar_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("saveButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_settings)
        
        bottom_bar_layout.addWidget(self.cancel_button)
        bottom_bar_layout.addWidget(self.save_button)

        bottom_container_layout.addWidget(bottom_bar)
        root_layout.addWidget(bottom_container)

        self._apply_stylesheet()

    def _create_color_pill(self, label_text, config_key, default_val):
        pill = QFrame()
        pill.setObjectName("newColorPill")
        pill.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        pill.setMinimumHeight(48)
        pill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        
        layout = QHBoxLayout(pill)
        layout.setContentsMargins(15, 8, 15, 8)
        
        name_label = QLabel(label_text)
        name_label.setWordWrap(True)
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        hex_input = QLineEdit(self.config.get(config_key, default_val))
        hex_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hex_input.setFixedWidth(110)
        hex_input.setFixedHeight(32)
        hex_input.setCursor(Qt.CursorShape.PointingHandCursor)
        hex_input.setReadOnly(True)
        
        def update_hex_style(hex_str):
            try:
                color = QColor(hex_str)
                if not color.isValid():
                    return
                r, g, b = color.red(), color.green(), color.blue()
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                text_color = "#000000" if luminance > 0.5 else "#FFFFFF"
                border_style = "border: 1px solid #d1d5db;" if (luminance > 0.95 and not theme_manager.night_mode) or (luminance < 0.05 and theme_manager.night_mode) else "border: none;"
                
                # Convert color to rgba with 0.3 opacity for disabled state, and dim text color
                hex_input.setStyleSheet(f"""
                    QLineEdit {{
                        background-color: {color.name()};
                        color: {text_color};
                        {border_style}
                        border-radius: 10px;
                        font-family: monospace;
                        font-weight: bold;
                        font-size: 13px;
                    }}
                    QLineEdit:disabled {{
                        background-color: rgba({r}, {g}, {b}, 0.3);
                        color: rgba({0 if luminance > 0.5 else 255}, {0 if luminance > 0.5 else 255}, {0 if luminance > 0.5 else 255}, 0.3);
                        border: none;
                    }}
                """)
            except:
                pass
        
        update_hex_style(hex_input.text())
        hex_input.textChanged.connect(update_hex_style)
        
        def open_color_dialog(*args):
            current_color = hex_input.text()
            try:
                onigiri_color_picker = importlib.import_module("1011095603.onigiri_color_picker")
                OnigiriColorDialog = onigiri_color_picker.OnigiriColorDialog
                new_color_hex, ok = OnigiriColorDialog.getColor(current_color, self, anchor=hex_input)
                if ok:
                    hex_input.setText(new_color_hex)
                return
            except Exception as e:
                print(f"[Hours] Failed to load OnigiriColorDialog: {e}")

            new_color = QColorDialog.getColor(QColor(current_color), self, "Select Color")
            if new_color.isValid():
                hex_input.setText(new_color.name())
        
        pill.mousePressEvent = open_color_dialog
        hex_input.mousePressEvent = open_color_dialog
        
        layout.addWidget(name_label)
        layout.addWidget(hex_input)
        
        return pill, hex_input

    def _on_bg_type_changed(self, btn=None):
        txt = self.bg_type_control.current_text()
        self.solid_container.setEnabled(txt == "Solid")
        self.gradient_container.setEnabled(txt == "Gradient")
        self.image_container.setEnabled(txt == "Image")
        self._refresh_preview()

    def _adjust_gmt_offset(self, delta):
        new_val = self.gmt_offset_value + delta
        if -12 <= new_val <= 14:
            self.gmt_offset_value = new_val
            sign = "+" if new_val > 0 else ""
            self.gmt_value_label.setText(f"{sign}{new_val} hours" if new_val != 0 else "0 hours")
            self._refresh_preview()

    def add_image(self):
        images = [f for f in os.listdir(self.gallery_dir) if f.lower().endswith(('.png', '.gif'))]
        if len(images) >= 3:
            showInfo("You can only have up to 3 images. Please delete one first.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Add Image", "", "Images (*.png *.gif)")
        if file_path:
            filename = os.path.basename(file_path)
            shutil.copy(file_path, os.path.join(self.gallery_dir, filename))
            self.refresh_gallery()

    def delete_image(self):
        for i in range(self.gallery_layout.count()):
            widget = self.gallery_layout.itemAt(i).widget()
            if isinstance(widget, ImagePreviewButton) and widget.isChecked():
                os.remove(widget.image_path)
                if self.config.get("bg_image") == os.path.basename(widget.image_path):
                    self.config["bg_image"] = None
                break
        self.refresh_gallery()
        self._refresh_preview()

    def refresh_gallery(self):
        while self.gallery_layout.count():
            child = self.gallery_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        images = [f for f in os.listdir(self.gallery_dir) if f.lower().endswith(('.png', '.gif'))]
        if not images:
            tokens = self._theme_tokens()
            no_images_label = QLabel("No images here")
            no_images_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_images_label.setStyleSheet(f"color: {tokens['muted']}; font-size: 13px; font-style: italic;")
            self.gallery_layout.addWidget(no_images_label)
        else:
            for image_name in images:
                path = os.path.join(self.gallery_dir, image_name)
                btn = ImagePreviewButton(path)
                if self.config.get("bg_image") == image_name:
                    btn.setChecked(True)
                btn.clicked.connect(self.on_image_selected)
                self.gallery_layout.addWidget(btn)
    
    def on_image_selected(self):
        sender = self.sender()
        for i in range(self.gallery_layout.count()):
            widget = self.gallery_layout.itemAt(i).widget()
            if widget is not sender:
                widget.setChecked(False)
        self.config["bg_image"] = os.path.basename(sender.image_path) if sender.isChecked() else None
        self._refresh_preview()

    def _collect_config(self):
        """Assembles the in-progress (unsaved) config from every control,
        mirroring save_settings() below, for the live preview to render."""
        cfg = dict(self.config)
        if hasattr(self, "style_control"):
            cfg["style"] = self.style_control.current_text() or cfg.get("style", "Classic")
        if hasattr(self, "font_button_group"):
            checked = self.font_button_group.checkedButton()
            cfg["font"] = checked.text() if checked else cfg.get("font", "System")
        if hasattr(self, "time_format_control"):
            cfg["time_format"] = self.time_format_control.current_text() or cfg.get("time_format", "24-Hour")
        if hasattr(self, "gmt_offset_value"):
            cfg["gmt_offset_hours"] = self.gmt_offset_value
        if hasattr(self, "clock_color_input"):
            cfg["clock_color"] = self.clock_color_input.text()
        if hasattr(self, "second_hand_color_input"):
            cfg["second_hand_color"] = self.second_hand_color_input.text()
        if hasattr(self, "bg_color_input"):
            cfg["bg_color"] = self.bg_color_input.text()
        if hasattr(self, "gradient_start_input"):
            cfg["bg_gradient_start"] = self.gradient_start_input.text()
        if hasattr(self, "gradient_end_input"):
            cfg["bg_gradient_end"] = self.gradient_end_input.text()
        if hasattr(self, "bg_type_control"):
            bg_type = self.bg_type_control.current_text()
            cfg["use_bg_color"] = (bg_type == "Solid")
            cfg["use_bg_gradient"] = (bg_type == "Gradient")
            cfg["use_bg_image"] = (bg_type == "Image")
        if hasattr(self, "opacity_slider"):
            cfg["bg_opacity"] = self.opacity_slider.value() / 100.0
        if hasattr(self, "bento_width_spin"):
            cfg[bento_integration.WIDTH_KEY] = int(self.bento_width_spin.value())
        if hasattr(self, "bento_height_spin"):
            cfg[bento_integration.HEIGHT_KEY] = int(self.bento_height_spin.value())
        return cfg
 
    def _refresh_preview(self, *_args):
        if not hasattr(self, "preview_widget"):
            return
        self.preview_widget.config = self._collect_config()
        self.preview_widget.refresh()
 
    def save_settings(self):
        self.config["style"] = self.style_control.current_text()
        self.config["font"] = self.font_button_group.checkedButton().text() if self.font_button_group.checkedButton() else "System"
        self.config["time_format"] = self.time_format_control.current_text()
        self.config["gmt_offset_hours"] = self.gmt_offset_value
        
        self.config["clock_color"] = self.clock_color_input.text()
        self.config["second_hand_color"] = self.second_hand_color_input.text()
        self.config["bg_color"] = self.bg_color_input.text()
        self.config["bg_gradient_start"] = self.gradient_start_input.text()
        self.config["bg_gradient_end"] = self.gradient_end_input.text()
        
        bg_type = self.bg_type_control.current_text()
        self.config["use_bg_color"] = (bg_type == "Solid")
        self.config["use_bg_gradient"] = (bg_type == "Gradient")
        self.config["use_bg_image"] = (bg_type == "Image")
        
        self.config["bg_opacity"] = self.opacity_slider.value() / 100.0
        bento_integration.save_settings_group(self.config, self.bento_width_spin, self.bento_height_spin)

        selected_image = None
        for i in range(self.gallery_layout.count()):
            widget = self.gallery_layout.itemAt(i).widget()
            if isinstance(widget, ImagePreviewButton) and widget.isChecked():
                selected_image = os.path.basename(widget.image_path)
                break
        self.config["bg_image"] = selected_image
        
        mw.addonManager.writeConfig(self.addon_package, self.config)
        
        from . import reset_cache
        reset_cache()
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()
            
        self.accept()

    def _apply_stylesheet(self):
        t = self._theme_tokens()
        bg, panel, fg, muted, surface, border, accent = t["bg"], t["panel"], t["fg"], t["muted"], t["surface"], t["border"], t["accent"]
        accent_hex = accent.lstrip("#")
        accent_rgb = tuple(int(accent_hex[i:i+2], 16) for i in (0, 2, 4))
        scrollbar_thumb = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.45)"
        scrollbar_thumb_hover = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.75)"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {fg}; }}
            QFrame#controlsContainer {{
                background-color: transparent; border: none;
                border-top-left-radius: 28px; border-top-right-radius: 28px;
            }}
            QWidget#controlsOuter {{ background-color: transparent; }}
            QWidget#previewWrapper {{ background-color: transparent; border: none; }}
            QScrollArea#controlsScroll, QScrollArea#controlsScroll > QWidget {{
                background: transparent; border: none;
            }}
            QScrollArea#controlsScroll QScrollBar:vertical {{
                background: {surface};
                width: 8px;
                margin: 0px;
                border: none;
            }}
            QScrollArea#controlsScroll QScrollBar::handle:vertical {{
                background: {scrollbar_thumb};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollArea#controlsScroll QScrollBar::handle:vertical:hover {{
                background: {scrollbar_thumb_hover};
            }}
            QScrollArea#controlsScroll QScrollBar::add-line:vertical,
            QScrollArea#controlsScroll QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollArea#controlsScroll QScrollBar::add-page:vertical,
            QScrollArea#controlsScroll QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QWidget#innerGroup {{
                background-color: transparent; border: none; border-radius: 12px;
            }}
            QFrame#newColorPill {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame#newColorPill:hover {{
                background-color: {"rgba(255,255,255,0.05)" if theme_manager.night_mode else "rgba(0,0,0,0.03)"};
            }}
            QFrame#newColorPill:disabled {{
                border: 1px solid {border};
                background-color: transparent;
            }}
            QLabel, QCheckBox {{ color: {fg}; font-size: 13px; }}
            QFrame#newColorPill QLabel {{
                font-weight: bold; border: none; background: transparent; color: {fg};
            }}
            QFrame#newColorPill:disabled QLabel {{
                color: {muted};
            }}
            #themeToggleContainer {{
                background-color: {surface}; border: 1px solid {border}; border-radius: 18px;
            }}
            #themeToggleButton {{
                background-color: transparent; border: none; border-radius: 14px;
                padding: 4px 16px; font-size: 13px; font-weight: 600; color: {muted};
            }}
            #themeToggleButton:checked {{ color: #ffffff; }}
            #themeToggleButton:hover:!checked {{ color: {fg}; }}
            QPushButton#fontButton {{
                background-color: {surface}; color: {fg}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 10px; font-size: 13px;
            }}
            QPushButton#fontButton:checked {{
                background-color: {panel}; border: 1px solid {accent}; color: {fg};
            }}
            QPushButton#fontButton:hover:!checked {{
                background-color: {border};
            }}
            QSlider#berrySlider::groove:horizontal {{
                height: 18px;
                border-radius: 9px;
                background-color: {surface};
            }}
            QSlider#berrySlider::sub-page:horizontal {{
                background-color: {accent};
                border-radius: 9px;
            }}
            QSlider#berrySlider::handle:horizontal {{
                background-color: #ffffff;
                width: 12px;
                height: 12px;
                margin: 3px 3px;
                border-radius: 6px;
            }}
            QPushButton#galleryImageBtn {{
                background-color: transparent;
                border: 2px solid transparent;
                border-radius: 14px;
                padding: 4px;
                min-width: 100px;
                max-width: 100px;
                min-height: 100px;
                max-height: 100px;
            }}
            QPushButton#galleryImageBtn:checked {{
                border: 2px solid {accent};
                background-color: rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.15);
            }}
            QPushButton#galleryImageBtn:hover:!checked {{
                border: 2px solid {border};
            }}
            QPushButton#gmtAdjustBtn {{
                background-color: {surface};
                color: {fg};
                border: 1px solid {border};
                border-radius: 14px;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 0px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton#gmtAdjustBtn:hover {{
                background-color: {border};
            }}
            QPushButton {{
                background-color: {surface}; color: {fg}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 14px;
            }}
            QPushButton:hover {{ background-color: {border}; }}
            QPushButton#saveButton {{
                background-color: {accent}; color: #ffffff; border: none;
                border-radius: 18px; min-height: 36px; max-height: 36px;
                padding: 0px 14px; font-size: 13px; font-weight: bold;
            }}
            QPushButton#saveButton:hover {{ background-color: {accent}; opacity: 0.9; }}
            QPushButton#cancelButton {{
                background-color: {surface}; color: {fg}; border: 1px solid {border};
                border-radius: 18px; min-height: 36px; max-height: 36px;
                padding: 0px 14px; font-size: 13px; font-weight: bold;
            }}
            QPushButton#cancelButton:hover {{ background-color: {border}; }}
            QWidget#bottomContainer {{ background-color: transparent; }}
            QWidget#bottomPillBar {{
                background-color: {panel}; border-radius: 28px; border: 1px solid {border};
            }}
            QSpinBox, QLineEdit {{
                background-color: {panel}; color: {fg}; border: 1px solid {border};
                border-radius: 10px; padding: 5px 8px;
            }}
            QSpinBox:disabled, QLineEdit:disabled {{
                background-color: {surface}; color: {muted}; border: 1px solid {border};
            }}
            QLineEdit {{
                font-family: monospace;
                font-size: 13px;
            }}
            QWidget:disabled, QLabel:disabled {{
                color: {muted};
            }}
            QFrame#newColorPill:disabled {{
                border: 1px solid {border};
            }}
            QFrame#newColorPill:disabled QLabel {{
                color: {muted};
            }}
            QFrame#newColorPill:disabled QLineEdit {{
                background-color: {surface};
                color: {muted};
                border: none;
            }}
            QPushButton:disabled {{
                background-color: {surface};
                color: {muted};
                border: 1px solid {border};
            }}
        """)


# ── Bento WebUI settings -----------------------------------------------------
try:
    if getattr(mw, "onigiri_api", {}).get("id") != "1011095603":
        raise ImportError("Onigiri Bento API is not active")
    _bws = importlib.import_module("1011095603.api.widget_settings")
except Exception:
    _bws = None

if _bws is not None:
    class SettingsDialog(_bws.BentoSettingsDialog):
        def __init__(self, parent=None, config=None, addon_package=None):
            package = mw.addonManager.addonFromModule(addon_package or __name__)
            source = config if isinstance(config, dict) else (mw.addonManager.getConfig(package) or {})
            defaults = {
                "style": "Classic", "font": "System", "clock_color": "#FFFFFF",
                "second_hand_color": "#ff4d4d", "background_type": "Solid",
                "use_bg_color": True, "bg_color": "#333333", "use_bg_gradient": False,
                "bg_gradient_start": "#6a11cb", "bg_gradient_end": "#2575fc",
                "use_bg_image": False, "bg_image": "", "bg_gallery": [],
                "bg_opacity": .85, "time_format": "24-Hour", "gmt_offset_hours": 0,
                "manual_widget_width": 200, "manual_widget_height": 200,
            }
            current = _bws.deep_merge(defaults, source)
            current["background_type"] = (
                "Image" if current.get("use_bg_image") else
                "Gradient" if current.get("use_bg_gradient") else "Solid"
            )

            def save(updated):
                updated = copy.deepcopy(updated)
                updated.pop("background_type", None)
                source.clear(); source.update(updated)
                mw.addonManager.writeConfig(package, source)
                addon = importlib.import_module(__package__)
                addon.CONFIG.clear(); addon.CONFIG.update(copy.deepcopy(updated))
                if hasattr(addon, "reset_cache"):
                    addon.reset_cache()

            def preview(updated, _variant, theme):
                addon = importlib.import_module(__package__)
                render_config = copy.deepcopy(updated)
                render_config.pop("background_type", None)
                dark = theme == "dark"
                css = addon.generate_css(dark, render_config)
                body = f'<div id="watch-container">{addon.generate_html(render_config)}</div>'
                return _bws.preview_document(body, css, dark=dark, wallpaper=bento_integration.main_menu_wallpaper(dark))

            gallery_dir = os.path.join(os.path.dirname(__file__), "user_files", "watch_gallery")
            self.gallery_dir = gallery_dir
            os.makedirs(self.gallery_dir, exist_ok=True)
            image_names = [""]
            if os.path.isdir(gallery_dir):
                image_names += sorted(name for name in os.listdir(gallery_dir) if name.lower().endswith((".png", ".gif")))
            pages = [
                _bws.page("clock", "Clock", [
                    _bws.section("Face", [
                        _bws.field("style", "Clock style", "select", default="Classic", options=["Classic", "Flip Clock", "Analog"]),
                        _bws.field("font", "Font", "select", default="System", options=["Instrument", "Montserrat", "Nunito", "SpaceMono", "System"]),
                        _bws.field("clock_color", "Clock and hands", "color", default="#FFFFFF"),
                        _bws.field("second_hand_color", "Second hand", "color", default="#ff4d4d"),
                    ]),
                    _bws.section("Time", [
                        _bws.field("time_format", "Time format", "select", default="24-Hour", options=["12-Hour", "24-Hour"]),
                        _bws.field("gmt_offset_hours", "GMT offset", "number", default=0, minimum=-12, maximum=14, unit="hours"),
                    ]),
                ], "Clock style, typography, and timezone.", "H"),
                _bws.page("background", "Background", [
                    _bws.section("Surface", [
                        _bws.field("background_type", "Background type", "select", default="Solid", options=["Solid", "Gradient", "Image"]),
                        _bws.field("bg_color", "Solid color", "color", default="#333333", show_if={"background_type": "Solid"}),
                        _bws.field("bg_gradient_start", "Gradient start", "color", default="#6a11cb", show_if={"background_type": "Gradient"}),
                        _bws.field("bg_gradient_end", "Gradient end", "color", default="#2575fc", show_if={"background_type": "Gradient"}),
                        _bws.field("bg_image", "Gallery image", "select", default="", options=[{"value": n, "label": n or "None"} for n in image_names], show_if={"background_type": "Image"}),
                        _bws.field("add-background-image", "Add gallery image", "action", button_label="Choose PNG or GIF", show_if={"background_type": "Image"}),
                        _bws.field("delete-background-image", "Delete selected image", "action", button_label="Delete image", show_if={"background_type": "Image"}),
                        _bws.field("bg_opacity", "Opacity", "range", default=85, minimum=0, maximum=100, unit="%", scale=.01),
                    ], "Keep up to three PNG or GIF backgrounds in the widget gallery."),
                ], "Choose the real clock card background.", "◐"),
            ]
            super().__init__(
                parent, title="Hours", subtitle="A customizable clock for Anki", accent="#ff4d4d",
                pages=pages, config=current, defaults=defaults, save_callback=save,
                logo_path=os.path.join(os.path.dirname(__file__), "assets", "hours_logo.svg"),
                mini_logo_path=os.path.join(os.path.dirname(__file__), "assets", "hours_mini_logo.svg"),
                preview_callback=preview, bugs_url="https://github.com/thepeacemonk/Hours",
            )

        def normalize_patch(self, patch):
            mode = patch.pop("background_type", None)
            if mode is not None:
                self.config["background_type"] = mode
                self.config["use_bg_color"] = mode == "Solid"
                self.config["use_bg_gradient"] = mode == "Gradient"
                self.config["use_bg_image"] = mode == "Image"
            return patch

        def _refresh_gallery_options(self):
            names = [""] + sorted(
                name for name in os.listdir(self.gallery_dir)
                if name.lower().endswith((".png", ".gif"))
            )
            for page_spec in self.pages:
                for group in page_spec.get("sections", []):
                    for spec in group.get("fields", []):
                        if spec.get("path") == "bg_image":
                            spec["options"] = [
                                {"value": name, "label": name or "None"}
                                for name in names
                            ]
                            return

        def handle_action(self, action):
            if action == "add-background-image":
                images = [
                    name for name in os.listdir(self.gallery_dir)
                    if name.lower().endswith((".png", ".gif"))
                ]
                if len(images) >= 3:
                    return {
                        "ok": False,
                        "error": "The gallery can contain up to three images.",
                    }
                path, _ = QFileDialog.getOpenFileName(
                    self, "Add background image", "", "Images (*.png *.gif)"
                )
                if not path:
                    return {"ok": True}
                filename = os.path.basename(path)
                shutil.copy2(path, os.path.join(self.gallery_dir, filename))
                self.config["bg_image"] = filename
                self.config["background_type"] = "Image"
                self.config["use_bg_color"] = False
                self.config["use_bg_gradient"] = False
                self.config["use_bg_image"] = True
                self._refresh_gallery_options()
                self._save()
                return {"ok": True}

            if action == "delete-background-image":
                filename = str(self.config.get("bg_image") or "")
                if not filename:
                    return {"ok": False, "error": "Select an image first."}
                if os.path.basename(filename) != filename:
                    return {"ok": False, "error": "Invalid gallery image."}
                path = os.path.join(self.gallery_dir, filename)
                if os.path.isfile(path):
                    os.remove(path)
                self.config["bg_image"] = ""
                self._refresh_gallery_options()
                self._save()
                return {"ok": True}

            return super().handle_action(action)

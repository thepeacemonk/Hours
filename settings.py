# -*- coding: utf-8 -*-
# Hours Anki Add-on - Settings
#
# Author: PeaceMonk
# License: GNU AGPLv3

import os
import shutil
from zoneinfo import available_timezones

from aqt import mw
from aqt.qt import *
from PyQt6.QtWidgets import QScrollArea, QStackedWidget, QFrame, QButtonGroup, QGridLayout
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from aqt.theme import theme_manager
from PyQt6.QtCore import pyqtSignal as Signal, pyqtProperty, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QColor, QPainter, QPixmap, QPainterPath, QBrush

# --- Custom Widgets ---

class ColorButton(QPushButton):
    """A circular button that displays a color and opens a color picker when clicked."""
    color_changed = Signal(str)

    def __init__(self, initial_color="#FFFFFF", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(28, 28)  # Ensure the button is a square
        self._color = QColor(initial_color)
        self.clicked.connect(self.on_click)

    def on_click(self):
        new_color = QColorDialog.getColor(self._color, self, "Select Color")
        if new_color.isValid():
            self.set_color(new_color.name())

    def set_color(self, color_hex):
        self._color = QColor(color_hex)
        self.update()
        self.color_changed.emit(self.get_color())

    def get_color(self):
        return self._color.name()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect)

class ImagePreviewButton(QPushButton):
    """A button that displays a thumbnail for an image in the gallery."""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_path = image_path
        
        pixmap = QPixmap(image_path)
        
        scaled_pixmap = pixmap.scaled(
            100, 100, 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
            Qt.TransformationMode.SmoothTransformation
        )
        
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

class SegmentedControl(QWidget):
    """A custom widget that functions like a radio button group."""
    current_changed = Signal(str)

    def __init__(self, options=None, parent=None):
        super().__init__(parent)
        self._options = options if options else []
        self._buttons = []
        self._current_selection = ""

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        for option in self._options:
            button = QPushButton(option)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(self._on_button_clicked)
            self._buttons.append(button)
            layout.addWidget(button)

    def _on_button_clicked(self):
        sender = self.sender()
        if sender.isChecked():
            self._current_selection = sender.text()
            for button in self._buttons:
                if button is not sender:
                    button.setChecked(False)
            self.current_changed.emit(self._current_selection)
    
    def current_text(self):
        """Returns the text of the currently selected button."""
        return self._current_selection

    def set_current(self, text):
        for button in self._buttons:
            if button.text().lower() == text.lower():
                button.setChecked(True)
                self._current_selection = button.text()
                break

class AnimatedToggleButton(QAbstractButton):
    """ A custom animated toggle switch. """
    def __init__(self, parent=None, accent_color="#007bff"):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.accent_color = QColor(accent_color)
        self.setFixedSize(44, 24)
        
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
        thumb_size = self.height() - 4
        end_pos = self.width() - thumb_size - 2 if checked else 2
        self.animation.setStartValue(self.thumb_x_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        height = self.height()
        radius = height / 2.0
        
        track_color_off = QColor("#555555") if mw.pm.night_mode() else QColor("#cccccc")
        thumb_color = QColor("#ffffff")
        
        painter.setPen(Qt.PenStyle.NoPen)
        track_color = self.accent_color if self.isChecked() else track_color_off
        painter.setBrush(track_color)
        painter.drawRoundedRect(self.rect(), radius, radius)

        thumb_radius = radius - 2
        painter.setBrush(thumb_color)
        
        thumb_y = radius
        thumb_x = self._thumb_x_pos + thumb_radius
        
        painter.drawEllipse(QPointF(thumb_x, thumb_y), thumb_radius, thumb_radius)

    def _set_initial_pos(self):
        thumb_size = self.height() - 4
        self._thumb_x_pos = self.width() - thumb_size - 2 if self.isChecked() else 2
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._set_initial_pos()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._set_initial_pos()

class SectionGroup(QWidget):
    """ A simple container widget with a title. """
    def __init__(self, title, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 15, 0, 15)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        main_layout.addWidget(title_label)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 5, 0, 0)
        main_layout.addLayout(self.content_layout)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)


# --- Main Settings Dialog ---

class SettingsDialog(QDialog):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.addon_name = "Hours"
        self.config = config
        self.setWindowTitle("Hours Settings")
        
        self.addon_dir = os.path.dirname(__file__)
        self.gallery_dir = os.path.join(self.addon_dir, "user_files", "watch_gallery")
        if not os.path.exists(self.gallery_dir):
            os.makedirs(self.gallery_dir)

        self.main_layout = QVBoxLayout(self)
        self.setup_ui()
        self.apply_styles()
        self.resize(450, 650)

    def on_donate_clicked(self):
        url = QUrl("https://buymeacoffee.com/peacemonk")
        QDesktopServices.openUrl(url)

    def on_report_clicked(self):
        url = QUrl("https://github.com/thepeacemonk/Onigiri")
        QDesktopServices.openUrl(url)

    def setup_ui(self):
        # --- Header Section ---
        header_container = QVBoxLayout()
        header_container.setSpacing(15)
        header_container.setContentsMargins(0, 0, 0, 10)

        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(self.addon_dir, "user_files", "media", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation))
        logo_label.setObjectName("LogoImage")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_container.addWidget(logo_label)

        # --- Buttons ---
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)

        # Row 1: Donate, Report
        row1_layout = QHBoxLayout()
        self.donate_btn = QPushButton("Donate")
        self.donate_btn.setObjectName("NavButton")
        self.donate_btn.clicked.connect(self.on_donate_clicked)

        self.report_btn = QPushButton("Report")
        self.report_btn.setObjectName("NavButton")
        self.report_btn.clicked.connect(self.on_report_clicked)

        row1_layout.addStretch()
        row1_layout.addWidget(self.donate_btn)
        row1_layout.addWidget(self.report_btn)
        row1_layout.addStretch()
        buttons_layout.addLayout(row1_layout)

        # Row 2: Customize, Settings
        row2_layout = QHBoxLayout()
        self.customize_btn = QPushButton("Customize")
        self.customize_btn.setObjectName("NavButton")
        self.customize_btn.setCheckable(True)
        self.customize_btn.setChecked(True)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setObjectName("NavButton")
        self.settings_btn.setCheckable(True)

        row2_layout.addStretch()
        row2_layout.addWidget(self.customize_btn)
        row2_layout.addWidget(self.settings_btn)
        row2_layout.addStretch()
        buttons_layout.addLayout(row2_layout)
        
        # Button Group for navigation
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.customize_btn)
        self.nav_button_group.addButton(self.settings_btn)

        # Connections for page switching
        self.customize_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.settings_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        header_container.addLayout(buttons_layout)
        self.main_layout.addLayout(header_container)
        self.main_layout.addSpacing(10)

        # --- Stacked Widget for Pages ---
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # --- Page 1: Customize ---
        customize_scroll_area = QScrollArea()
        customize_scroll_area.setWidgetResizable(True)
        customize_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        customize_page_content = QWidget()
        customize_page_content.setObjectName("PageContent")
        customize_scroll_area.setWidget(customize_page_content)
        
        horizontal_wrapper_layout = QHBoxLayout(customize_page_content)
        horizontal_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        sections_container_widget = QWidget()
        customize_content_layout = QVBoxLayout(sections_container_widget)
        customize_content_layout.setContentsMargins(0, 0, 0, 0)
        customize_content_layout.setSpacing(0)
        
        style_section = SectionGroup("Clock Style")
        self.style_control = SegmentedControl(["Classic", "Flip Clock", "Analog"])
        self.style_control.set_current(self.config.get("style", "Classic"))
        style_section.add_widget(self.style_control)
        customize_content_layout.addWidget(style_section)

        font_section = SectionGroup("Font")
        # A container widget to hold the grid of font buttons
        font_buttons_container = QWidget()
        font_buttons_container.setObjectName("FontButtonsGrid")
        
        font_layout = QGridLayout(font_buttons_container)
        font_layout.setContentsMargins(0, 0, 0, 0)
        font_layout.setSpacing(10)

        self.font_button_group = QButtonGroup(self)
        self.font_button_group.setExclusive(True)
        
        fonts = ["Instrument", "Montserrat", "Nunito", "SpaceMono", "System"]
        # Arrange buttons in a grid with 3 columns
        positions = [(i, j) for i in range(2) for j in range(3)] 
        
        for position, name in zip(positions, fonts):
            button = QPushButton(name)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if self.config.get("font", "Instrument") == name:
                button.setChecked(True)
                
            self.font_button_group.addButton(button)
            font_layout.addWidget(button, *position)

        font_section.add_widget(font_buttons_container)
        customize_content_layout.addWidget(font_section)

        colors_section = SectionGroup("Colors")
        colors_form = QFormLayout()
        self.clock_color_btn = ColorButton(self.config.get("clock_color", "#FFFFFF"))
        colors_form.addRow("Clock/Hands Color:", self.clock_color_btn)
        self.second_hand_color_btn = ColorButton(self.config.get("second_hand_color", "#ff4d4d"))
        colors_form.addRow("Second Hand Color (Analog):", self.second_hand_color_btn)
        self.bg_color_btn = ColorButton(self.config.get("bg_color", "#333333"))
        self.use_bg_color_check = QCheckBox("Use Solid Color")
        self.use_bg_color_check.setChecked(self.config.get("use_bg_color", True))
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(self.bg_color_btn)
        bg_color_layout.addWidget(self.use_bg_color_check)
        colors_form.addRow("Background Color:", bg_color_layout)
        self.gradient_start_btn = ColorButton(self.config.get("bg_gradient_start", "#6a11cb"))
        self.gradient_end_btn = ColorButton(self.config.get("bg_gradient_end", "#2575fc"))
        self.use_gradient_check = QCheckBox("Use Gradient")
        self.use_gradient_check.setChecked(self.config.get("use_bg_gradient", False))
        gradient_layout = QHBoxLayout()
        gradient_layout.addWidget(self.gradient_start_btn)
        gradient_layout.addWidget(QLabel("to"))
        gradient_layout.addWidget(self.gradient_end_btn)
        gradient_layout.addWidget(self.use_gradient_check)
        colors_form.addRow("Background Gradient:", gradient_layout)
        colors_section.add_layout(colors_form)
        customize_content_layout.addWidget(colors_section)

        bg_image_section = SectionGroup("Background Image")
        self.use_bg_image_check = QCheckBox("Use Image")
        self.use_bg_image_check.setChecked(self.config.get("use_bg_image", False))
        bg_image_section.add_widget(self.use_bg_image_check)
        self.gallery_widget = QWidget()
        self.gallery_layout = QGridLayout(self.gallery_widget)
        bg_image_section.add_widget(self.gallery_widget)
        self.add_image_btn = QPushButton("Add Image")
        self.add_image_btn.clicked.connect(self.add_image)
        self.delete_image_btn = QPushButton("Delete Selected")
        self.delete_image_btn.clicked.connect(self.delete_image)
        image_btn_layout = QHBoxLayout()
        image_btn_layout.addWidget(self.add_image_btn)
        image_btn_layout.addWidget(self.delete_image_btn)
        bg_image_section.add_layout(image_btn_layout)
        customize_content_layout.addWidget(bg_image_section)

        opacity_section = SectionGroup("Background Opacity")
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.config.get("bg_opacity", 0.85) * 100))
        self.opacity_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_label.setMinimumWidth(40)
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        opacity_section.add_layout(opacity_layout)
        customize_content_layout.addWidget(opacity_section)

        customize_content_layout.addStretch()
        
        horizontal_wrapper_layout.addWidget(sections_container_widget)
        horizontal_wrapper_layout.addStretch()

        # --- Page 2: Time Settings ---
        time_settings_page_widget = QWidget()
        time_settings_page_widget.setObjectName("PageContent")
        time_content_layout = QVBoxLayout(time_settings_page_widget)
        time_content_layout.setContentsMargins(0, 0, 0, 0)
        time_content_layout.setSpacing(0)

        time_format_section = SectionGroup("Time Format")
        self.time_format_control = SegmentedControl(["12-Hour", "24-Hour"])
        self.time_format_control.set_current(self.config.get("time_format", "24-Hour"))
        time_format_section.add_widget(self.time_format_control)
        time_content_layout.addWidget(time_format_section)
        
        tz_section = SectionGroup("Timezone")
        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems(sorted(list(available_timezones())))
        self.timezone_combo.setCurrentText(self.config.get("timezone", "UTC"))
        tz_section.add_widget(self.timezone_combo)
        time_content_layout.addWidget(tz_section)
        
        time_content_layout.addStretch()

        # --- Add pages to stacked widget ---
        self.stacked_widget.addWidget(customize_scroll_area)
        self.stacked_widget.addWidget(time_settings_page_widget)

        # --- Bottom Button Bar ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)

        self.refresh_gallery()

    def apply_styles(self):
        """Applies a theme-aware stylesheet to the dialog."""
        if mw.pm.night_mode():
            # Dark Mode
            stylesheet = """
                QDialog { background-color: #2F2F2F; }
                #PageContent { background: #2F2F2F; }
                QLabel, QCheckBox { color: #E0E0E0; }
                #SectionTitle { color: #FFFFFF; font-size: 20px; font-weight: 500; }
                QComboBox { 
                    background-color: #424242; color: #E0E0E0; 
                    border: 1px solid #555555; border-radius: 4px; padding: 4px; 
                }
                QPushButton { 
                    background-color: #555555; color: #E0E0E0; 
                    border: 1px solid #666666; border-radius: 4px; padding: 6px 12px;
                }
                QPushButton:hover { background-color: #666666; }
                
                #LogoImage {
                    background-color: transparent;
                }
                QPushButton#NavButton {
                    background-color: #4a4a4a;
                    color: #E0E0E0;
                    border: none;
                    border-radius: 16px;
                    font-weight: bold;
                    padding: 8px 24px;
                    min-width: 90px;
                }
                QPushButton#NavButton:hover {
                    background-color: #5a5a5a;
                }
                QPushButton#NavButton:checked {
                    background-color: #e88b8b;
                    color: #212121;
                }

                ColorButton, ImagePreviewButton { border-radius: 8px; }
                ImagePreviewButton { background-color: #424242; }
                ImagePreviewButton:checked { border: 2px solid #339FFF; }
                
                SegmentedControl QPushButton, #FontButtonsGrid QPushButton {
                    padding: 6px 16px; font-size: 14px; border-radius: 8px;
                    background-color: #555555; color: #E0E0E0;
                    border: 1px solid transparent;
                }
                SegmentedControl QPushButton:hover, #FontButtonsGrid QPushButton:hover { background-color: #666666; }
                SegmentedControl QPushButton:checked, #FontButtonsGrid QPushButton:checked {
                    background-color: #424242; border: 1px solid #339FFF;
                }
            """
        else:
            # Light Mode
            stylesheet = """
                QDialog { background-color: #F5F5F5; }
                #PageContent { background: #F5F5F5; }
                QLabel, QCheckBox { color: #212121; }
                #SectionTitle { color: #000000; font-size: 20px; font-weight: 500; }
                QComboBox { 
                    background-color: #FFFFFF; color: #212121; 
                    border: 1px solid #C5C5C5; border-radius: 4px; padding: 4px; 
                }
                QPushButton { 
                    background-color: #E0E0E0; color: #212121; 
                    border: 1px solid #C5C5C5; border-radius: 4px; padding: 6px 12px;
                }
                QPushButton:hover { background-color: #D5D5D5; }
                
                #LogoImage {
                    background-color: transparent;
                }
                
                QPushButton#NavButton {
                    background-color: #F0F0F0;
                    color: #333333;
                    border: none;
                    border-radius: 16px;
                    font-weight: bold;
                    padding: 8px 24px;
                    min-width: 90px;
                }
                QPushButton#NavButton:hover {
                    background-color: #E0E0E0;
                }
                QPushButton#NavButton:checked {
                    background-color: #e88b8b;
                    color: #333333;
                }

                ColorButton, ImagePreviewButton { border-radius: 8px; }
                ImagePreviewButton { background-color: #EEEEEE; }
                ImagePreviewButton:checked { border: 2px solid #007AFF; }

                SegmentedControl QPushButton, #FontButtonsGrid QPushButton {
                    background-color: #E0E0E0; color: #555; border-radius: 8px;
                    border: 1px solid transparent; padding: 6px 16px; font-size: 14px;
                }
                SegmentedControl QPushButton:hover, #FontButtonsGrid QPushButton:hover { background-color: #D5D5D5; }
                SegmentedControl QPushButton:checked, #FontButtonsGrid QPushButton:checked {
                    background-color: #FFFFFF; color: #000; border: 1px solid #007AFF;
                }
            """
        self.setStyleSheet(stylesheet)

    def add_image(self):
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

    def refresh_gallery(self):
        while self.gallery_layout.count():
            child = self.gallery_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        images = [f for f in os.listdir(self.gallery_dir) if f.lower().endswith(('.png', '.gif'))]
        row, col = 0, 0
        for image_name in images:
            path = os.path.join(self.gallery_dir, image_name)
            btn = ImagePreviewButton(path)
            if self.config.get("bg_image") == image_name:
                btn.setChecked(True)
            
            btn.clicked.connect(self.on_image_selected)
            self.gallery_layout.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1
    
    def on_image_selected(self):
        sender = self.sender()
        for i in range(self.gallery_layout.count()):
            widget = self.gallery_layout.itemAt(i).widget()
            if widget is not sender:
                widget.setChecked(False)
        self.config["bg_image"] = os.path.basename(sender.image_path) if sender.isChecked() else None

    def save_settings(self):
        self.config["style"] = self.style_control.current_text()
        self.config["font"] = self.font_button_group.checkedButton().text()
        self.config["time_format"] = self.time_format_control.current_text()
        self.config["timezone"] = self.timezone_combo.currentText()
        
        self.config["clock_color"] = self.clock_color_btn.get_color()
        self.config["second_hand_color"] = self.second_hand_color_btn.get_color()
        self.config["bg_color"] = self.bg_color_btn.get_color()
        self.config["bg_gradient_start"] = self.gradient_start_btn.get_color()
        self.config["bg_gradient_end"] = self.gradient_end_btn.get_color()
        
        self.config["use_bg_color"] = self.use_bg_color_check.isChecked()
        self.config["use_bg_gradient"] = self.use_gradient_check.isChecked()
        self.config["use_bg_image"] = self.use_bg_image_check.isChecked()
        
        self.config["bg_opacity"] = self.opacity_slider.value() / 100.0

        selected_image = None
        for i in range(self.gallery_layout.count()):
            widget = self.gallery_layout.itemAt(i).widget()
            if isinstance(widget, ImagePreviewButton) and widget.isChecked():
                selected_image = os.path.basename(widget.image_path)
                break
        self.config["bg_image"] = selected_image
        
        mw.addonManager.writeConfig(self.addon_name, self.config)
        
        from . import reset_cache
        reset_cache()
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()
            
        self.accept()


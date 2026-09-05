import sys
import time
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QPoint
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtGui import QColor, QFont, QCursor
from speech import speak

class Communicator(QObject):
    update_signal = pyqtSignal(dict)

class TrafficLightButton(QPushButton):
    def __init__(self, color_normal, color_hover, symbol, tooltip_text="", parent=None):
        super().__init__(parent)
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.symbol = symbol
        self.setToolTip(tooltip_text)
        self.setFixedSize(12, 12)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setText("")
        self._update_style(False)

    def _update_style(self, hovered):
        border_col = "rgba(0, 0, 0, 0.15)"
        txt_col = "#4a0000" if "FF5F56" in self.color_normal else "#4a3b00" if "FFBD2E" in self.color_normal else "#003b0c"
        if hovered:
            self.setText(self.symbol)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.color_hover};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    color: {txt_col};
                    font-size: 8px;
                    font-weight: bold;
                    padding-bottom: 1px;
                }}
            """)
        else:
            self.setText("")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.color_normal};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                }}
            """)

    def enterEvent(self, event):
        self._update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(False)
        super().leaveEvent(event)

class LearningCardHUD(QWidget):
    def __init__(self):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)

        # Configure Universal Font Fallback (Segoe UI + Microsoft YaHei UI + Lucida Sans Unicode + Segoe UI Emoji)
        app_font = QFont()
        app_font.setFamilies(["Segoe UI", "Microsoft YaHei UI", "Lucida Sans Unicode", "Segoe UI Emoji"])
        self.app.setFont(app_font)

        super().__init__()
        
        self.is_dark_mode = True
        self.is_collapsed = False
        self.auto_speak = False
        self.current_english = ""
        self.last_update_time = time.time()
        self.drag_position = QPoint()
        
        self.comm = Communicator()
        self.comm.update_signal.connect(self._apply_card_data)

        self._init_window()
        self._build_apple_ui()
        self._setup_animations()
        self.apply_theme()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        screen = self.app.primaryScreen().geometry()
        self.card_width = 460
        self.card_x = screen.width() - self.card_width - 30
        self.card_y = 50
        self.setGeometry(self.card_x, self.card_y, self.card_width, 220)

    def _build_apple_ui(self):
        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(16, 16, 16, 16)
        self.master_layout.setSpacing(0)

        # Frosted Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("AppleCard")

        # Soft Ambient Shadow
        self.shadow = QGraphicsDropShadowEffect(self.card)
        self.shadow.setBlurRadius(32)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(10)
        self.card.setGraphicsEffect(self.shadow)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(18, 14, 18, 16)
        self.card_layout.setSpacing(8)

        # ── 1. macOS Header ──
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(8)

        # Traffic Lights
        self.btn_red = TrafficLightButton("#FF5F56", "#FF5F56", "×", "关闭伴侣", self)
        self.btn_red.clicked.connect(self.close)

        self.btn_yellow = TrafficLightButton("#FFBD2E", "#FFBD2E", "–", "折叠为灵动岛", self)
        self.btn_yellow.clicked.connect(self.toggle_collapse)

        self.btn_green = TrafficLightButton("#27C93F", "#27C93F", "+", "切换自动朗读", self)
        self.btn_green.clicked.connect(self.toggle_auto_speak)

        self.header_layout.addWidget(self.btn_red)
        self.header_layout.addWidget(self.btn_yellow)
        self.header_layout.addWidget(self.btn_green)
        self.header_layout.addSpacing(6)

        # Title
        self.title_label = QLabel("英语影子伴侣", self)
        self.header_layout.addWidget(self.title_label)

        # Green Dot Indicator (CSS-styled, immune to missing glyphs)
        self.status_container = QFrame(self)
        self.status_container.setStyleSheet("""
            QFrame {
                background: rgba(48, 209, 88, 0.15);
                border-radius: 8px;
            }
        """)
        self.status_sub_layout = QHBoxLayout(self.status_container)
        self.status_sub_layout.setContentsMargins(6, 2, 8, 2)
        self.status_sub_layout.setSpacing(5)

        self.dot = QFrame(self)
        self.dot.setFixedSize(6, 6)
        self.dot.setStyleSheet("background: #30D158; border-radius: 3px;")
        self.status_sub_layout.addWidget(self.dot)

        self.status_text = QLabel("正在监听", self)
        self.status_text.setStyleSheet("""
            QLabel {
                color: #30D158;
                font-family: "Segoe UI", "Microsoft YaHei UI";
                font-size: 10px;
                font-weight: 600;
                background: transparent;
            }
        """)
        self.status_sub_layout.addWidget(self.status_text)
        self.header_layout.addWidget(self.status_container)

        self.header_layout.addStretch()

        # Theme Toggle Button (Light/Dark Switcher)
        self.btn_theme = QPushButton("☀️ 浅色", self)
        self.btn_theme.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_theme.clicked.connect(self.toggle_theme)
        self.header_layout.addWidget(self.btn_theme)

        # Audio Toggle Capsule Pill
        self.capsule_audio = QPushButton("自动发音: 关", self)
        self.capsule_audio.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.capsule_audio.clicked.connect(self.toggle_auto_speak)
        self.header_layout.addWidget(self.capsule_audio)

        self.card_layout.addLayout(self.header_layout)

        # Subtle Separator
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        self.card_layout.addWidget(self.sep)

        # ── 2. Content Container ──
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 2, 0, 0)
        self.content_layout.setSpacing(8)

        # Chinese Original
        self.zh_label = QLabel("在任意软件中打字，此处将同步呈现地道英译与重点词", self)
        self.zh_label.setWordWrap(True)
        self.content_layout.addWidget(self.zh_label)

        # English Translation Row
        self.en_row = QHBoxLayout()
        self.en_row.setSpacing(10)

        self.en_label = QLabel("Type naturally in Chinese to learn authentic English on the fly!", self)
        self.en_label.setWordWrap(True)
        self.en_row.addWidget(self.en_label, stretch=1)

        # Action Buttons
        self.actions_layout = QVBoxLayout()
        self.actions_layout.setSpacing(4)

        self.btn_speak = QPushButton("朗读", self)
        self.btn_speak.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_speak.clicked.connect(self.play_audio)
        self.actions_layout.addWidget(self.btn_speak)

        self.btn_copy = QPushButton("复制", self)
        self.btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_copy.clicked.connect(self.copy_english)
        self.actions_layout.addWidget(self.btn_copy)

        self.en_row.addLayout(self.actions_layout)
        self.content_layout.addLayout(self.en_row)

        # ── 3. Vocabulary Section ──
        self.vocab_section = QWidget(self)
        self.vocab_section_layout = QVBoxLayout(self.vocab_section)
        self.vocab_section_layout.setContentsMargins(0, 2, 0, 0)
        self.vocab_section_layout.setSpacing(6)

        self.vocab_header = QLabel("KEY EXPRESSIONS · 核心词汇", self)
        self.vocab_header.setStyleSheet("""
            QLabel {
                color: #FF9F0A;
                font-family: "Segoe UI", "Microsoft YaHei UI";
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
        """)
        self.vocab_section_layout.addWidget(self.vocab_header)

        # Chips Layout
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setSpacing(6)

        self.chip_labels = []
        for i in range(3):
            btn_chip = QPushButton("", self)
            btn_chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_chip.clicked.connect(lambda _, b=btn_chip: self._on_chip_clicked(b))
            self.chips_layout.addWidget(btn_chip)
            self.chip_labels.append(btn_chip)

        self.chip_labels[0].setText("on the fly · 随打随学")
        self.chip_labels[1].setText("naturally · 自然地")
        self.chip_labels[2].hide()

        self.chips_layout.addStretch()
        self.vocab_section_layout.addLayout(self.chips_layout)
        self.content_layout.addWidget(self.vocab_section)

        # ── 4. Footnote ──
        self.footer_label = QLabel("可任意拖拽 · 连按两次 Ctrl 或按 F8 学习当前句", self)
        self.content_layout.addWidget(self.footer_label)

        self.card_layout.addWidget(self.content_widget)
        self.master_layout.addWidget(self.card)

    def apply_theme(self):
        """Apply Apple Dark or Light Liquid Glass theme dynamically."""
        if self.is_dark_mode:
            # ── Dark Mode (Apple Dark Liquid Glass) ──
            self.card.setStyleSheet("""
                QFrame#AppleCard {
                    background: rgba(28, 28, 32, 0.94);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 20px;
                }
            """)
            self.shadow.setColor(QColor(0, 0, 0, 160))
            self.title_label.setStyleSheet("""
                QLabel {
                    color: #F5F5F7;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            self.btn_theme.setText("☀️ 浅色")
            self.btn_theme.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #8E8E93;
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 10px;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 10px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.14);
                    color: #FFFFFF;
                }
            """)
            self.sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
            self.zh_label.setStyleSheet("""
                QLabel {
                    color: #98989D;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 12px;
                    line-height: 1.4;
                }
            """)
            self.en_label.setStyleSheet("""
                QLabel {
                    color: #0A84FF;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 15px;
                    font-weight: 600;
                    letter-spacing: -0.2px;
                }
            """)
            self.btn_speak.setStyleSheet("""
                QPushButton {
                    background: rgba(10, 132, 255, 0.16);
                    color: #0A84FF;
                    border: 1px solid rgba(10, 132, 255, 0.35);
                    border-radius: 11px;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 11px;
                    font-weight: 600;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background: rgba(10, 132, 255, 0.28);
                    color: #64D2FF;
                }
            """)
            self.btn_copy.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #C7C7CC;
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 11px;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 11px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.16);
                    color: #FFFFFF;
                }
            """)
            for chip in self.chip_labels:
                chip.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.06);
                        color: #E5E5EA;
                        border: 1px solid rgba(255, 255, 255, 0.09);
                        border-radius: 9px;
                        font-family: "Segoe UI", "Microsoft YaHei UI";
                        font-size: 11px;
                        padding: 4px 9px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.14);
                        color: #FFFFFF;
                        border: 1px solid rgba(255, 255, 255, 0.18);
                    }
                """)
            self.footer_label.setStyleSheet("""
                QLabel {
                    color: #636366;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 10px;
                }
            """)
            if not self.auto_speak:
                self.capsule_audio.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #8E8E93;
                        border: 1px solid rgba(255, 255, 255, 0.10);
                        border-radius: 10px;
                        font-size: 10px;
                        padding: 2px 8px;
                    }
                """)
        else:
            # ── Light Mode (Apple Light Liquid Glass) ──
            self.card.setStyleSheet("""
                QFrame#AppleCard {
                    background: rgba(248, 248, 250, 0.96);
                    border: 1px solid rgba(0, 0, 0, 0.12);
                    border-radius: 20px;
                }
            """)
            self.shadow.setColor(QColor(0, 0, 0, 70))
            self.title_label.setStyleSheet("""
                QLabel {
                    color: #1D1D1F;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 12px;
                    font-weight: 600;
                }
            """)
            self.btn_theme.setText("🌙 深色")
            self.btn_theme.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 0, 0, 0.06);
                    color: #6E6E73;
                    border: 1px solid rgba(0, 0, 0, 0.09);
                    border-radius: 10px;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 10px;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 0.10);
                    color: #1D1D1F;
                }
            """)
            self.sep.setStyleSheet("background-color: rgba(0, 0, 0, 0.08); max-height: 1px;")
            self.zh_label.setStyleSheet("""
                QLabel {
                    color: #6E6E73;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 12px;
                    line-height: 1.4;
                }
            """)
            self.en_label.setStyleSheet("""
                QLabel {
                    color: #0071E3;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 15px;
                    font-weight: 600;
                    letter-spacing: -0.2px;
                }
            """)
            self.btn_speak.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 113, 227, 0.12);
                    color: #0071E3;
                    border: 1px solid rgba(0, 113, 227, 0.28);
                    border-radius: 11px;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 11px;
                    font-weight: 600;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background: rgba(0, 113, 227, 0.22);
                    color: #005bb5;
                }
            """)
            self.btn_copy.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 0, 0, 0.06);
                    color: #3A3A3C;
                    border: 1px solid rgba(0, 0, 0, 0.09);
                    border-radius: 11px;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 11px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 0.12);
                    color: #1D1D1F;
                }
            """)
            for chip in self.chip_labels:
                chip.setStyleSheet("""
                    QPushButton {
                        background: rgba(0, 0, 0, 0.04);
                        color: #1D1D1F;
                        border: 1px solid rgba(0, 0, 0, 0.08);
                        border-radius: 9px;
                        font-family: "Segoe UI", "Microsoft YaHei UI";
                        font-size: 11px;
                        padding: 4px 9px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background: rgba(0, 0, 0, 0.08);
                        color: #000000;
                        border: 1px solid rgba(0, 0, 0, 0.15);
                    }
                """)
            self.footer_label.setStyleSheet("""
                QLabel {
                    color: #86868B;
                    font-family: "Segoe UI", "Microsoft YaHei UI";
                    font-size: 10px;
                }
            """)
            if not self.auto_speak:
                self.capsule_audio.setStyleSheet("""
                    QPushButton {
                        background: rgba(0, 0, 0, 0.06);
                        color: #6E6E73;
                        border: 1px solid rgba(0, 0, 0, 0.09);
                        border-radius: 10px;
                        font-size: 10px;
                        padding: 2px 8px;
                    }
                """)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def _setup_animations(self):
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(350)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.dim_timer = QTimer(self)
        self.dim_timer.setInterval(1500)
        self.dim_timer.timeout.connect(self._check_auto_dim)
        self.dim_timer.start()

    def _check_auto_dim(self):
        if time.time() - self.last_update_time > 8:
            if self.windowOpacity() > 0.72:
                self.fade_anim.stop()
                self.fade_anim.setStartValue(self.windowOpacity())
                self.fade_anim.setEndValue(0.70)
                self.fade_anim.start()

    def enterEvent(self, event):
        self.last_update_time = time.time()
        self.fade_anim.stop()
        self.fade_anim.setStartValue(self.windowOpacity())
        self.fade_anim.setEndValue(0.98)
        self.fade_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._check_auto_dim()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.card_x = new_pos.x()
            self.card_y = new_pos.y()
            event.accept()

    def toggle_collapse(self):
        if not self.is_collapsed:
            self.content_widget.hide()
            self.sep.hide()
            self.capsule_audio.hide()
            self.btn_theme.hide()
            bg_col = "rgba(22, 22, 24, 0.94)" if self.is_dark_mode else "rgba(240, 240, 242, 0.96)"
            border_col = "rgba(255, 255, 255, 0.16)" if self.is_dark_mode else "rgba(0, 0, 0, 0.14)"
            self.card.setStyleSheet(f"""
                QFrame#AppleCard {{
                    background: {bg_col};
                    border: 1px solid {border_col};
                    border-radius: 18px;
                }}
            """)
            self.resize(220, 70)
            self.is_collapsed = True
        else:
            self.content_widget.show()
            self.sep.show()
            self.capsule_audio.show()
            self.btn_theme.show()
            self.is_collapsed = False
            self.apply_theme()
            self.adjustSize()

    def toggle_auto_speak(self):
        self.auto_speak = not self.auto_speak
        if self.auto_speak:
            self.capsule_audio.setText("自动发音: 开")
            self.capsule_audio.setStyleSheet("""
                QPushButton {
                    background: rgba(48, 209, 88, 0.20);
                    color: #30D158;
                    border: 1px solid rgba(48, 209, 88, 0.40);
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 2px 8px;
                }
            """)
        else:
            self.capsule_audio.setText("自动发音: 关")
            self.apply_theme()

    def play_audio(self):
        if self.current_english:
            speak(self.current_english)

    def _on_chip_clicked(self, btn):
        txt = btn.text().split("·")[0].strip()
        if txt:
            speak(txt)

    def copy_english(self):
        if self.current_english:
            cb = QApplication.clipboard()
            cb.setText(self.current_english)
            old_txt = self.btn_copy.text()
            self.btn_copy.setText("✓ 已复制")
            self.btn_copy.setStyleSheet("""
                QPushButton {
                    background: rgba(48, 209, 88, 0.22);
                    color: #30D158;
                    border: 1px solid rgba(48, 209, 88, 0.5);
                    border-radius: 11px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 4px 12px;
                }
            """)
            QTimer.singleShot(1400, lambda: self._reset_copy_btn(old_txt))

    def _reset_copy_btn(self, orig_txt):
        self.btn_copy.setText(orig_txt)
        self.apply_theme()

    def update_card(self, data: dict):
        self.comm.update_signal.emit(data)

    def _apply_card_data(self, data: dict):
        if not data:
            return

        self.last_update_time = time.time()
        self.setWindowOpacity(0.98)

        if self.is_collapsed:
            self.toggle_collapse()

        zh = data.get("chinese", "")
        self.zh_label.setText(f"{zh}")

        en = data.get("english", "")
        self.current_english = en
        self.en_label.setText(en)

        kws = data.get("keywords", [])
        for i in range(len(self.chip_labels)):
            if i < len(kws):
                item = kws[i]
                w = item.get("word", "")
                m = item.get("meaning", "")
                txt = f"{w} · {m}"
                self.chip_labels[i].setText(txt)
                self.chip_labels[i].show()
            else:
                self.chip_labels[i].hide()

        self.adjustSize()

        if self.auto_speak and en:
            speak(en)

    def run(self):
        self.show()
        self.app.exec()

if __name__ == "__main__":
    hud = LearningCardHUD()
    hud.run()

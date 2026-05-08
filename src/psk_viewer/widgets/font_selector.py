from qtpy.QtCore import QCoreApplication, Qt, Signal, Slot
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QFontDialog, QHBoxLayout, QLabel, QPushButton, QWidget

__all__ = ["FontSelector"]

_translate = QCoreApplication.translate


class FontSelector(QWidget):
    fontSelected: Signal = Signal(QFont, name="fontSelected")

    def __init__(self, parent: QWidget, color: QFont) -> None:
        super().__init__(parent)

        self.font: QFont = color

        self.font_dialog: QFontDialog = QFontDialog(self)
        self.font_dialog.fontSelected.connect(self.on_font_changed)

        self.font_name: QLabel = QLabel(self)
        self.font_name.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.browse_button: QPushButton = QPushButton(
            self.font_dialog.windowTitle(), self
        )

        layout: QHBoxLayout = QHBoxLayout()
        layout.addWidget(self.font_name, 1)
        layout.addWidget(self.browse_button, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._show_font_name()

        self.browse_button.clicked.connect(self.on_button_clicked)

    @Slot()
    def on_button_clicked(self) -> None:
        self.font_dialog.setCurrentFont(self.font)
        self.font_dialog.exec()

    @Slot(QFont)
    def on_font_changed(self, font: QFont) -> None:
        self.font = font
        self._show_font_name()
        self.fontSelected.emit(font)

    def _show_font_name(self) -> None:
        self.font_name.setText(
            " ".join(
                (
                    self.font.family(),
                    self.locale().toString(self.font.pointSizeF()),
                    _translate("unit", "pt"),
                )
            )
        )
        font: QFont = QFont(self.font)
        font.setPointSizeF(self.font_name.font().pointSizeF())
        self.font_name.setFont(font)

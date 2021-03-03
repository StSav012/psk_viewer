# -*- coding: utf-8 -*-

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QColorDialog, QPushButton

__all__ = ['ColorSelector']


class ColorSelector(QPushButton):
    colorSelected = pyqtSignal(QColor, name='colorSelected')

    def __init__(self, *args, **kwargs):
        self.color: QColor = QColor.fromRgb(0)

        index: int = 0
        while index < len(args):
            arg = args[index]
            if isinstance(arg, QColor):
                self.color = arg
                args = args[:index] + args[index + 1:]
            else:
                index += 1
        self.color = kwargs.pop('color', self.color)

        super().__init__(*args, **kwargs)

        self.setAutoFillBackground(True)
        self.paint_putton()

        self.setText(self.color.name())

        self.color_dialog: QColorDialog = QColorDialog(self)
        self.color_dialog.colorSelected.connect(self.on_color_changed)

        self.clicked.connect(self.on_button_clicked)

    def on_button_clicked(self):
        self.color_dialog.setCurrentColor(self.color)
        self.color_dialog.exec()

    def on_color_changed(self, color: QColor):
        self.color = color
        self.setText(self.color.name())
        self.paint_putton()
        self.colorSelected.emit(color)

    def paint_putton(self):
        pal: QPalette = self.palette()
        pal.setColor(QPalette.Button, self.color)
        pal.setColor(QPalette.ButtonText, QColor('white' if self.color.lightnessF() < 0.5 else 'black'))
        self.setPalette(pal)
        self.update()

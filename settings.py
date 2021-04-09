# -*- coding: utf-8 -*-
import os
from typing import List, Type

import pyqtgraph as pg
from PyQt5.QtCore import QCoreApplication, QSettings
from PyQt5.QtGui import QColor

try:
    from typing import Final
except ImportError:
    class _Final:
        @staticmethod
        def __getitem__(item: Type):
            return item


    Final = _Final()

__all__ = ['Settings']


class Settings(QSettings):
    """ convenient internal representation of the application settings """
    LINE_ENDS: Final[List[str]] = [r'Line Feed (\n)', r'Carriage Return (\r)', r'CR+LF (\r\n)', r'LF+CR (\n\r)']
    _LINE_ENDS: Final[List[str]] = ['\n', '\r', '\r\n', '\n\r']
    CSV_SEPARATORS: Final[List[str]] = [r'comma (,)', r'tab (\t)', r'semicolon (;)', r'space ( )']
    _CSV_SEPARATORS: Final[List[str]] = [',', '\t', ';', ' ']

    def __init__(self, *args):
        super().__init__(*args)
        self.display_processing: bool = True

    @property
    def dialog(self):
        _translate = QCoreApplication.translate
        opts = {
            'suffix': _translate('unit', 'Hz'),
            'siPrefix': True,
            'decimals': 0,
            'dec': True,
            'compactHeight': False,
            'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'
        }
        return {
            'Processing': {
                'Jump:': (opts, 'jump',)
            } if self.display_processing else {},
            'Line': {
                'Color:': ('line_color',)
            },
            'Export': {
                'Line ending:': (self.LINE_ENDS, self._LINE_ENDS, 'line_end'),
                'CSV separator:': (self.CSV_SEPARATORS, self._CSV_SEPARATORS, 'csv_separator'),
            }
        }

    @property
    def line_end(self) -> str:
        self.beginGroup('export')
        v: int = self.value('lineEnd', self._LINE_ENDS.index(os.linesep), int)
        self.endGroup()
        return self._LINE_ENDS[v]

    @line_end.setter
    def line_end(self, new_value: str):
        self.beginGroup('export')
        self.setValue('lineEnd', self._LINE_ENDS.index(new_value))
        self.endGroup()

    @property
    def csv_separator(self) -> str:
        self.beginGroup('export')
        v: int = self.value('csvSeparator', self._CSV_SEPARATORS.index('\t'), int)
        self.endGroup()
        return self._CSV_SEPARATORS[v]

    @csv_separator.setter
    def csv_separator(self, new_value: str):
        self.beginGroup('export')
        self.setValue('csvSeparator', self._CSV_SEPARATORS.index(new_value))
        self.endGroup()

    @property
    def line_color(self) -> QColor:
        self.beginGroup('plotLine')
        v: QColor = self.value('color', pg.intColor(5), QColor)
        self.endGroup()
        return v

    @line_color.setter
    def line_color(self, new_value: QColor):
        self.beginGroup('plotLine')
        self.setValue('color', new_value)
        self.endGroup()

    @property
    def jump(self) -> float:
        self.beginGroup('processing')
        v: float = self.value('jump', 600e3, float)
        self.endGroup()
        return v

    @jump.setter
    def jump(self, new_value: float):
        self.beginGroup('processing')
        self.setValue('jump', new_value)
        self.endGroup()

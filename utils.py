# -*- coding: utf-8 -*-

import os
import sys
from typing import Union, Tuple, List

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPalette, QPixmap


# https://www.reddit.com/r/learnpython/comments/4kjie3/how_to_include_gui_images_with_pyinstaller/d3gjmom
def resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(getattr(sys, '_MEIPASS'), relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


IMAGE_EXT: str = '.svg'


def load_icon(filename: str) -> QIcon:
    is_dark: bool = QPalette().color(QPalette.Window).lightness() < 128
    icon: QIcon = QIcon()
    icon.addPixmap(QPixmap(resource_path(os.path.join('img', 'dark' if is_dark else 'light', filename + IMAGE_EXT))),
                   QIcon.Normal, QIcon.Off)
    return icon


def copy_to_clipboard(plain_text: str, rich_text: str = '', text_type: Union[Qt.TextFormat, str] = Qt.PlainText):
    from PyQt5.QtGui import QClipboard
    from PyQt5.QtCore import QMimeData
    from PyQt5.QtWidgets import QApplication

    clipboard: QClipboard = QApplication.clipboard()
    mime_data: QMimeData = QMimeData()
    if isinstance(text_type, str):
        mime_data.setData(text_type, plain_text.encode())
    elif text_type == Qt.RichText:
        mime_data.setHtml(rich_text)
        mime_data.setText(plain_text)
    else:
        mime_data.setText(plain_text)
    clipboard.setMimeData(mime_data, QClipboard.Clipboard)


def load_data_fs(filename: str) -> Tuple[np.ndarray, np.ndarray]:
    if filename.casefold().endswith(('.fmd', '.frd')):
        fn: str = os.path.splitext(filename)[0]
    else:
        fn: str = filename
    min_frequency: float = np.nan
    max_frequency: float = np.nan
    if os.path.exists(fn + '.fmd'):
        with open(fn + '.fmd', 'rt') as fin:
            line: str
            for line in fin:
                if line and not line.startswith('*'):
                    t = list(map(lambda w: w.strip(), line.split(':', maxsplit=1)))
                    if len(t) > 1:
                        if t[0].lower() == 'FStart [GHz]'.lower():
                            min_frequency = float(t[1]) * 1e6
                        elif t[0].lower() == 'FStop [GHz]'.lower():
                            max_frequency = float(t[1]) * 1e6
    else:
        return np.empty(0), np.empty(0)
    if not np.isnan(min_frequency) and not np.isnan(max_frequency) and os.path.exists(fn + '.frd'):
        y: np.ndarray = np.loadtxt(fn + '.frd', usecols=(0,))
        x: np.ndarray = np.linspace(min_frequency, max_frequency,
                                    num=y.size, endpoint=False)
        return x, y
    return np.empty(0), np.empty(0)


def load_data_scandat(filename: str) -> Tuple[np.ndarray, np.ndarray]:
    with open(filename, 'rt') as f_in:
        lines: List[str] = f_in.readlines()

    min_frequency: float
    frequency_step: float
    x: np.ndarray
    y: np.ndarray

    if lines[0].startswith('*****'):
        min_frequency = float(lines.index(next(filter(lambda line: line.startswith('F(start) [MHz]:'),
                                                      lines))) + 1) * 1e3
        frequency_step = float(lines.index(next(filter(lambda line: line.startswith('F(stept) [MHz]:'),
                                                       lines))) + 1) * 1e3
        lines = lines[lines.index(next(filter(lambda line: line.startswith('Finish'),
                                              lines))) + 1:-2]
        y = np.array([float(line.split()[0]) for line in lines])
    elif lines[0].startswith('   Spectrometer(PhSw)-2014   '):
        min_frequency = float(lines[14]) * 1e3
        frequency_step = float(lines[16]) * 1e3
        lines = lines[32:-2]
        y = np.array([float(line) for line in lines[::2]])
    elif lines[0].startswith('   Spectrometer(PhSw)   '):
        min_frequency = float(lines[12]) * 1e3
        frequency_step = float(lines[14]) * 1e3
        lines = lines[30:-1]
        y = np.array([float(line.split()[0]) for line in lines])
    else:
        min_frequency = float(lines[13]) * 1e3
        frequency_step = float(lines[15]) * 1e3
        lines = lines[32:]
        y = np.array([float(line) for line in lines[::2]])
    x = np.arange(y.size, dtype=float) * frequency_step + min_frequency
    return x, y

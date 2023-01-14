# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
from typing import Final

import numpy as np
from numpy.typing import NDArray
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QColor, QIcon, QPalette, QPixmap
from qtpy.QtWidgets import QInputDialog, QWidget

_translate = QCoreApplication.translate

VOLTAGE_GAIN: Final[float] = 5.0


# https://www.reddit.com/r/learnpython/comments/4kjie3/how_to_include_gui_images_with_pyinstaller/d3gjmom
def resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(getattr(sys, '_MEIPASS'), relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


IMAGE_EXT: str = '.svg'


def load_icon(filename: str) -> QIcon:
    is_dark: bool = QPalette().color(QPalette.ColorRole.Window).lightness() < 128
    pixmap: QPixmap = QPixmap()
    file_path: str = resource_path(os.path.join('img', filename + IMAGE_EXT))
    if not os.path.exists(file_path):
        return QIcon()
    with open(file_path, 'rb') as f_in:
        data: bytes = (f_in.read()
                       .replace(b'"grey"', b'"#b2b2b2"' if is_dark else b'"#4d4d4d"')
                       .replace(b'"background"', b'"#000"' if is_dark else b'"#fff"')
                       .replace(b'"foreground"', b'"#fff"' if is_dark else b'"#000"')
                       )
        pixmap.loadFromData(data)
    return QIcon(pixmap)


def mix_colors(color_1: QColor, color_2: QColor, ratio_1: float = 0.5) -> QColor:
    return QColor(
        int(round(color_2.red() * (1. - ratio_1) + color_1.red() * ratio_1)),
        int(round(color_2.green() * (1. - ratio_1) + color_1.green() * ratio_1)),
        int(round(color_2.blue() * (1. - ratio_1) + color_1.blue() * ratio_1)),
        int(round(color_2.alpha() * (1. - ratio_1) + color_1.alpha() * ratio_1)))


def superscript_number(number: str) -> str:
    ss_dict = {
        '0': '⁰',
        '1': '¹',
        '2': '²',
        '3': '³',
        '4': '⁴',
        '5': '⁵',
        '6': '⁶',
        '7': '⁷',
        '8': '⁸',
        '9': '⁹',
        '-': '⁻',
        '−': '⁻'
    }
    for d in ss_dict:
        number = number.replace(d, ss_dict[d])
    return number


def superscript_tag(html: str) -> str:
    """ replace numbers within <sup></sup> with their Unicode superscript analogs """
    text: str = html
    j: int = 0
    while j >= 0:
        i: int = text.casefold().find('<sup>', j)
        if i == -1:
            return text
        j = text.casefold().find('</sup>', i)
        if j == -1:
            return text
        text = text[:i] + superscript_number(text[i + 5:j]) + text[j + 6:]
        j -= 5
    return text


def copy_to_clipboard(plain_text: str, rich_text: str = '',
                      text_type: Qt.TextFormat | str = Qt.TextFormat.PlainText) -> None:
    from qtpy.QtGui import QClipboard
    from qtpy.QtCore import QMimeData
    from qtpy.QtWidgets import QApplication

    clipboard: QClipboard = QApplication.clipboard()
    mime_data: QMimeData = QMimeData()
    if isinstance(text_type, str):
        mime_data.setData(text_type, plain_text.encode())
    elif text_type == Qt.TextFormat.RichText:
        mime_data.setHtml(rich_text)
        mime_data.setText(plain_text)
    else:
        mime_data.setText(plain_text)
    clipboard.setMimeData(mime_data, QClipboard.Mode.Clipboard)


def load_data_fs(filename: str) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    fn: str
    if filename.casefold().endswith(('.fmd', '.frd')):
        fn = os.path.splitext(filename)[0]
    else:
        fn = filename
    min_frequency: float = np.nan
    max_frequency: float = np.nan
    if os.path.exists(fn + '.fmd'):
        with open(fn + '.fmd', 'rt') as f_in:
            line: str
            for line in f_in:
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
        y: NDArray[np.float64] = np.loadtxt(fn + '.frd', usecols=(0,))
        x: NDArray[np.float64] = np.linspace(min_frequency, max_frequency,
                                             num=y.size, endpoint=False)
        return x, y
    return np.empty(0), np.empty(0)


def load_data_scandat(filename: str, parent: QWidget) \
        -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], float]:
    with open(filename, 'rt') as f_in:
        lines: list[str] = f_in.readlines()

    min_frequency: float
    frequency_step: float
    frequency_jump: float
    x: NDArray[np.float64]
    y: NDArray[np.float64]
    bias_offset: float
    bias: NDArray[np.float64]
    cell_length: float

    if lines[0].startswith('*****'):
        min_frequency = float(lines[lines.index(next(filter(lambda line: line.startswith('F(start) [MHz]:'),
                                                            lines))) + 1]) * 1e3
        frequency_step = float(lines[lines.index(next(filter(lambda line: line.startswith('F(stept) [MHz]:'),
                                                             lines))) + 1]) * 1e3
        frequency_jump = float(lines[lines.index(next(filter(lambda line: line.startswith('F(jump) [MHz]:'),
                                                             lines))) + 1]) * 1e3
        bias_offset = float(lines[lines.index(next(filter(lambda line: line.startswith('U - shift:'), lines))) + 1])
        cell_length = float(lines[lines.index(next(filter(lambda line: line.startswith('Length of Cell:'),
                                                          lines))) + 1])
        lines = lines[lines.index(next(filter(lambda line: line.startswith('Finish'),
                                              lines))) + 1:-2]
        y = np.array([float(line.split()[0]) for line in lines]) * 1e-3
        bias = np.array([bias_offset - float(line.split()[1]) for line in lines])
    elif lines[0].startswith('   Spectrometer(PhSw)-2014   '):
        min_frequency = float(lines[14]) * 1e3
        frequency_step = float(lines[16]) * 1e3
        frequency_jump = float(lines[2]) * 1e3
        cell_length = float(lines[25])
        bias_offset = float(lines[26])
        lines = lines[32:]
        if lines[-1] == '0':
            lines = lines[:-2]
        y = np.array([float(line) for line in lines[::2]]) * 1e-3
        bias = np.array([bias_offset - float(line) for line in lines[1::2]])
    elif lines[0].startswith('   Spectrometer(PhSw)   '):
        min_frequency = float(lines[12]) * 1e3
        frequency_step = float(lines[14]) * 1e3
        frequency_jump = float(lines[2]) * 1e3
        cell_length = float(lines[23])
        bias_offset = float(lines[24])
        lines = lines[30:]
        if lines[-1].split()[-1] == '0':
            lines = lines[:-1]
        y = np.array([float(line.split()[0]) for line in lines]) * 1e-3
        bias = np.array([bias_offset - float(line.split()[1]) for line in lines])
    else:
        min_frequency = float(lines[13]) * 1e3
        frequency_step = float(lines[15]) * 1e3
        frequency_jump = float(lines[2]) * 1e3
        cell_length = float(lines[24])
        bias_offset = float(lines[25])
        lines = lines[31:]
        y = np.array([float(line) for line in lines[::2]]) * 1e-3
        bias = np.array([bias_offset - float(line) for line in lines[1::2]])
    x = np.arange(y.size, dtype=float) * frequency_step + min_frequency
    ok: bool = False
    while cell_length <= 0.0 or not ok:
        cell_length, ok = QInputDialog.getDouble(parent,
                                                 parent.windowTitle() if parent is not None else '',
                                                 _translate('dialog prompt',
                                                            'Encountered invalid value of the cell length: {} cm\n'
                                                            'Enter a correct value [cm]:').format(cell_length),
                                                 100.0,
                                                 0.1,
                                                 1000.0,
                                                 1,
                                                 Qt.WindowType.Dialog,
                                                 0.1
                                                 )
    return x, y, y / bias / cell_length / VOLTAGE_GAIN, frequency_jump


def load_data_csv(filename: str) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], float]:
    fn: str
    if filename.casefold().endswith(('.csv', '.conf')):
        fn = os.path.splitext(filename)[0]
    else:
        fn = filename
    if os.path.exists(fn + '.csv') and os.path.exists(fn + '.conf'):
        with open(fn + '.csv', 'rt') as f_in:
            lines: list[str] = list(filter(lambda line: line[0].isdigit(), f_in.readlines()))
        x: NDArray[np.float64] = np.array([float(line.split()[1]) for line in lines]) * 1e6
        y: NDArray[np.float64] = np.array([float(line.split()[2]) for line in lines]) * 1e-3
        g: NDArray[np.float64] = np.array([float(line.split()[4]) for line in lines])
        with open(fn + '.conf', 'rt') as f_in:
            frequency_jump: float = float(next(
                filter(lambda line: line.startswith('F(jump) [MHz]:'), f_in.readlines())
            ).split()[-1]) * 1e3
        return x, y, g, frequency_jump
    return np.empty(0), np.empty(0), np.empty(0), np.nan


def ensure_extension(fn: str, ext: str) -> str:
    filename_parts: tuple[str, str] = os.path.splitext(fn)
    if filename_parts[1].casefold() != ext:
        fn += ext
    return fn

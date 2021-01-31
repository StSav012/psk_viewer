# -*- coding: utf-8 -*-

import os
import sys

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



#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import platform
import sys
from contextlib import suppress
from pathlib import Path
from typing import Final, Sequence

__author__: Final[str] = 'StSav012'
__original_name__: Final[str] = 'psk_viewer'


def _version_tuple(version_string: str) -> tuple[int | str, ...]:
    result: tuple[int | str, ...] = tuple()
    part: str
    for part in version_string.split('.'):
        try:
            result += (int(part),)
        except ValueError:
            result += (part,)
    return result


qt_list: Sequence[str]
uname: platform.uname_result = platform.uname()
if ((uname.system == 'Windows'
     and _version_tuple(uname.version) < _version_tuple('10.0.19044'))  # Windows 10 21H2 or later required
        or uname.machine not in ('x86_64', 'AMD64')):
    qt_list = ('PyQt5',)  # Qt6 does not support the OSes
else:
    qt_list = ('PyQt6', 'PySide6', 'PyQt5')
if sys.version_info < (3, 11):  # PySide2 does not support Python 3.11 and newer
    qt_list = *qt_list, 'PySide2'

REQUIREMENTS: Final[list[str | Sequence[str]]] = ['qtpy',
                                                  [qt + '.QtCore' for qt in qt_list],
                                                  'pandas',
                                                  'pyqtgraph',
                                                  'scipy']


if __name__ == '__main__':
    def update() -> None:
        """ Download newer files from GitHub and replace the existing ones """
        with suppress(BaseException):  # ignore really all exceptions, for there are dozens of the sources
            import updater

            updater.update(__author__, __original_name__)


    def is_package_importable(package_name: str) -> bool:
        try:
            __import__(package_name, locals=locals(), globals=globals())
        except (ModuleNotFoundError, ):
            return False
        return True


    def make_old_qt_compatible_again() -> None:
        from qtpy import QT6, PYQT5
        from qtpy.QtCore import QLibraryInfo, Qt
        from qtpy.QtWidgets import QAbstractSpinBox, QApplication, QDialog

        if not QT6 and not PYQT5:
            QApplication.exec = QApplication.exec_
            QDialog.exec = QDialog.exec_

        if QT6:
            QLibraryInfo.LibraryLocation = QLibraryInfo.LibraryPath
        else:
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

        from pyqtgraph import __version__

        if _version_tuple(__version__) < _version_tuple('0.13.2'):
            import pyqtgraph as pg

            pg.SpinBox.setMaximumHeight = lambda self, max_h: QAbstractSpinBox.setMaximumHeight(self, round(max_h))


    if (not hasattr(sys, '_MEI''PASS')   # if not embedded into a PyInstaller executable
            and not Path('.git').exists()):
        update()

    if not hasattr(sys, '_MEI''PASS'):   # if not embedded into a PyInstaller executable
        def ensure_package(package_name: str | Sequence[str]) -> bool:
            """
            Install packages if missing

            :param package_name: a package name or a sequence of the names of alternative packages;
                                 if none of the packages installed beforehand, install the first one given
            :returns bool: True if a package is importable, False when an attempt to install the package made
            """

            if not package_name:
                raise ValueError('No package name(s) given')

            if isinstance(package_name, str) and is_package_importable(package_name):
                return True

            if not isinstance(package_name, str) and isinstance(package_name, Sequence):
                for _package_name in package_name:
                    if is_package_importable(_package_name):
                        return True

            if not sys.executable:
                # sys.executable can be empty if argv[0] has been changed and Python is
                # unable to retrieve the real program name
                return False

            import subprocess

            if not isinstance(package_name, str) and isinstance(package_name, Sequence):
                package_name = package_name[0]
            if not getattr(ensure_package, 'pip_updated', False):
                import ensurepip

                ensurepip.bootstrap(upgrade=True, user=True)
                ensure_package.pip_updated = True
            if '.' in package_name:  # take only the root part of the package path
                package_name = package_name.split('.', maxsplit=1)[0]
            subprocess.check_call((sys.executable, '-m', 'pip', 'install', package_name))
            return False


        for package in REQUIREMENTS:
            ensure_package(package)

    from qtpy.QtCore import QLibraryInfo, QLocale, QTranslator
    from qtpy.QtWidgets import QApplication

    from utils import resource_path
    from backend import App

    make_old_qt_compatible_again()

    app: QApplication = QApplication(sys.argv)

    languages: set[str] = set(QLocale().uiLanguages() + [QLocale().bcp47Name(), QLocale().name()])
    language: str
    qt_translator: QTranslator = QTranslator()
    for language in languages:
        if qt_translator.load('qt_' + language,
                              QLibraryInfo.location(QLibraryInfo.LibraryLocation.TranslationsPath)):
            app.installTranslator(qt_translator)
            break
    qtbase_translator: QTranslator = QTranslator()
    for language in languages:
        if qtbase_translator.load('qtbase_' + language,
                                  QLibraryInfo.location(QLibraryInfo.LibraryLocation.TranslationsPath)):
            app.installTranslator(qtbase_translator)
            break
    my_translator: QTranslator = QTranslator()
    for language in languages:
        if my_translator.load(language, resource_path('translations')):
            app.installTranslator(my_translator)
            break

    windows: list[App] = []
    for a in sys.argv[1:] or ['']:
        window: App = App(a)
        window.show()
        windows.append(window)
    app.exec()

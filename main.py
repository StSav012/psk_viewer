#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import Final, List, Set

__author__: Final[str] = 'StSav012'
__original_name__: Final[str] = 'psk_viewer'

REQUIREMENTS: Final[List[str]] = ['PySide6', 'pyqtgraph', 'scipy', 'pandas', 'openpyxl']

if __name__ == '__main__':

    if not hasattr(sys, '_MEIPASS') and not Path('.git').exists():
        try:
            import updater

            updater.update(__author__, __original_name__)
        except (OSError, ModuleNotFoundError):
            pass

    if not hasattr(sys, '_MEIPASS'):  # if not embedded into an executable
        import platform

        _PYSIDE6_RELEASE_PAGE: Final[str] = 'https://download.qt.io/official_releases/QtForPython/pyside6/'
        pip_updated: bool = False
        for package in REQUIREMENTS:
            try:
                __import__(package)
            except (ImportError, ModuleNotFoundError) as ex:
                if str(ex).startswith('libOpenGL.so.0'):
                    print('Ensure that `libopengl0` is installed')
                    exit(0)

                import subprocess

                if not pip_updated:
                    if subprocess.check_call((sys.executable, '-m', 'pip', 'install', '-U', 'pip')):
                        raise ex
                    pip_updated = True
                if package == 'PySide6' and platform.win32_ver()[0] and int(platform.win32_ver()[0]) < 10:
                    package = _PYSIDE6_RELEASE_PAGE + 'shiboken6-6.1.3-6.1.3-cp36.cp37.cp38.cp39-none-win_amd64.whl'
                    if subprocess.check_call((sys.executable, '-m', 'pip', 'install', package)):
                        raise ex
                    package = _PYSIDE6_RELEASE_PAGE + 'PySide6-6.1.3-6.1.3-cp36.cp37.cp38.cp39-none-win_amd64.whl'
                if subprocess.check_call((sys.executable, '-m', 'pip', 'install', package)):
                    raise ex

    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator, Qt
    from PySide6.QtWidgets import QApplication

    from utils import resource_path
    from backend import App

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app: QApplication = QApplication(sys.argv)

    languages: Set[str] = set(QLocale().uiLanguages() + [QLocale().bcp47Name(), QLocale().name()])
    language: str
    qt_translator: QTranslator = QTranslator()
    for language in languages:
        if qt_translator.load('qt_' + language,
                              QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(qt_translator)
            break
    qtbase_translator: QTranslator = QTranslator()
    for language in languages:
        if qtbase_translator.load('qtbase_' + language,
                                  QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
            app.installTranslator(qtbase_translator)
            break
    my_translator: QTranslator = QTranslator()
    for language in languages:
        if my_translator.load(language, resource_path('translations')):
            app.installTranslator(my_translator)
            break

    windows: List[App] = []
    for a in sys.argv[1:] or ['']:
        window: App = App(a)
        window.show()
        windows.append(window)
    app.exec()

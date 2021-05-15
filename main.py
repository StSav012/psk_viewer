#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from typing import Final, List, Set

__author__: Final[str] = 'StSav012'
__original_name__: Final[str] = 'psk_viewer'

REQUIREMENTS: Final[List[str]] = ['PyQt5', 'pyqtgraph', 'scipy', 'pandas', 'openpyxl']

if __name__ == '__main__':

    if not hasattr(sys, '_MEIPASS') and not Path('.git').exists():
        try:
            import updater

            updater.update(__author__, __original_name__)
        except (OSError, ModuleNotFoundError):
            pass

    if not hasattr(sys, '_MEIPASS'):  # if not embedded into an executable
        import importlib

        for package in REQUIREMENTS:
            try:
                importlib.import_module(package)
            except (ImportError, ModuleNotFoundError) as ex:
                import subprocess

                if subprocess.check_call([sys.executable, '-m', 'pip', 'install', package]):
                    raise ex

    from PyQt5.QtCore import QLibraryInfo, QLocale, QTranslator
    from PyQt5.QtWidgets import QApplication

    from utils import resource_path
    from backend import App

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
        if my_translator.load(QLocale.system().bcp47Name(), resource_path('translations')):
            app.installTranslator(my_translator)
            break

    windows: List[App] = []
    for a in sys.argv[1:] or ['']:
        window: App = App(a)
        window.show()
        windows.append(window)
    app.exec_()

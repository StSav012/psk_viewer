#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
from typing import List, Type, Set

try:
    from typing import Final
except ImportError:
    class _Final:
        @staticmethod
        def __getitem__(item: Type):
            return item


    Final = _Final()


REQUIREMENTS: Final[List[str]] = ['PyQt5', 'pyqtgraph', 'scipy', 'pandas']

if __name__ == '__main__':

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

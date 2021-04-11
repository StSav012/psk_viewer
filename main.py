#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
from typing import List, Type

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

    qt_translator: QTranslator = QTranslator()
    qt_translator.load("qt_" + QLocale.system().bcp47Name(),
                       QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qt_translator)
    qtbase_translator: QTranslator = QTranslator()
    qtbase_translator.load("qtbase_" + QLocale.system().bcp47Name(),
                           QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtbase_translator)
    my_translator: QTranslator = QTranslator()
    my_translator.load(QLocale.system().bcp47Name(), resource_path('translations'))
    app.installTranslator(my_translator)

    windows: List[App] = []
    for a in sys.argv[1:]:
        window: App = App(a)
        window.show()
        windows.append(window)
    app.exec_()

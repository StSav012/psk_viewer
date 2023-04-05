#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Final

__author__: Final[str] = 'StSav012'
__original_name__: Final[str] = 'psk_viewer'

del Final

if __name__ == '__main__':
    def main() -> None:
        import argparse
        import platform
        import sys
        from contextlib import suppress
        from pathlib import Path
        from types import ModuleType
        from typing import Callable, Final, NamedTuple, Sequence

        def _version_tuple(version_string: str) -> tuple[int | str, ...]:
            result: tuple[int | str, ...] = tuple()
            part: str
            for part in version_string.split('.'):
                try:
                    result += (int(part),)
                except ValueError:
                    result += (part,)
            return result

        class PackageRequirement(NamedTuple):
            package_name: str
            import_name: str
            min_version: str = ''
            version_call: Callable[[ModuleType], str] = lambda module: getattr(module, '__version__', '')

            def __str__(self) -> str:
                if self.min_version:
                    return self.package_name + '>=' + self.min_version
                return self.package_name

        qt_list: list[PackageRequirement]
        uname: platform.uname_result = platform.uname()
        if ((uname.system == 'Windows'
             and _version_tuple(uname.version) < _version_tuple('10.0.19044'))  # Windows 10 21H2 or later required
                or uname.machine not in ('x86_64', 'AMD64')):
            # Qt6 does not support the OSes
            qt_list = [PackageRequirement(package_name='PyQt5', import_name='PyQt5.QtCore')]
        else:
            qt_list = [
                PackageRequirement(package_name='PySide6-Essentials', import_name='PySide6.QtCore'),
                PackageRequirement(package_name='PyQt6', import_name='PyQt6.QtCore'),
                PackageRequirement(package_name='PyQt5', import_name='PyQt5.QtCore'),
            ]
        if sys.version_info < (3, 11):  # PySide2 from pypi is not available for Python 3.11 and newer
            qt_list.append(PackageRequirement(package_name='PySide2', import_name='PySide2.QtCore'))

        requirements: Final[list[PackageRequirement | Sequence[PackageRequirement]]] = [
            PackageRequirement(package_name='qtpy', import_name='qtpy', min_version='2.3.1'),
            qt_list,
            PackageRequirement(package_name='pandas', import_name='pandas'),
            PackageRequirement(package_name='pyqtgraph', import_name='pyqtgraph', min_version='0.13.2'),
            PackageRequirement(package_name='scipy', import_name='scipy')
        ]

        def update() -> None:
            """ Download newer files from GitHub and replace the existing ones """
            with suppress(BaseException):  # ignore really all exceptions, for there are dozens of the sources
                import updater

                updater.update(__author__, __original_name__)

        def is_package_importable(package_requirement: PackageRequirement) -> bool:
            try:
                module: ModuleType = __import__(package_requirement.import_name, locals=locals(), globals=globals())
            except (ModuleNotFoundError,):
                return False
            else:
                if (package_requirement.min_version
                        and (_version_tuple(package_requirement.version_call(module))
                             < _version_tuple(package_requirement.min_version))):
                    return False
            return True

        def ensure_package(package_requirement: PackageRequirement | Sequence[PackageRequirement],
                           upgrade_pip: bool = False) -> bool:
            """
            Install packages if missing

            :param package_requirement: a package name or a sequence of the names of alternative packages;
                                 if none of the packages installed beforehand, install the first one given
            :param upgrade_pip: upgrade `pip` before installing the package (if necessary)
            :returns bool: True if a package is importable, False when an attempt to install the package made
            """

            if not package_requirement:
                raise ValueError('No package requirements given')

            if not sys.executable:
                return False  # nothing to do

            if isinstance(package_requirement, PackageRequirement) and is_package_importable(package_requirement):
                return True

            if not isinstance(package_requirement, PackageRequirement) and isinstance(package_requirement, Sequence):
                for _package_requirement in package_requirement:
                    if is_package_importable(_package_requirement):
                        return True

            import subprocess

            if isinstance(package_requirement, Sequence):
                package_requirement = package_requirement[0]
            if upgrade_pip:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-U', 'pip'])
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-U', str(package_requirement)])
            return False

        def make_old_qt_compatible_again() -> None:
            from qtpy import QT6, PYSIDE2, __version__
            from qtpy.QtCore import QLibraryInfo, Qt
            from qtpy.QtWidgets import QApplication, QDialog

            if PYSIDE2:
                QApplication.exec = QApplication.exec_
                QDialog.exec = QDialog.exec_

            if _version_tuple(__version__) < _version_tuple('2.3.1') and QT6:
                QLibraryInfo.LibraryLocation = QLibraryInfo.LibraryPath
            if not QT6:
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
                QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

            from pyqtgraph import __version__

            if _version_tuple(__version__) < _version_tuple('0.13.2'):
                import pyqtgraph as pg
                from qtpy.QtWidgets import QAbstractSpinBox

                pg.SpinBox.setMaximumHeight = lambda self, max_h: QAbstractSpinBox.setMaximumHeight(self, round(max_h))

        update_by_default: bool = (uname.system == 'Windows'
                                   and not hasattr(sys, '_MEI''PASS')
                                   and not Path('.git').exists())
        ap: argparse.ArgumentParser = argparse.ArgumentParser(
            allow_abbrev=True,
            description='IPM RAS PSK and FS spectrometer files viewer.\n'
                        f'Find more at https://github.com/{__author__}/{__original_name__}.')
        ap.add_argument('file', type=str, nargs=argparse.ZERO_OR_MORE, default=[''])
        if not hasattr(sys, '_MEI''PASS'):  # if not embedded into an executable
            ap_group = ap.add_argument_group(title='Service options')
            if not update_by_default:
                ap_group.add_argument('-U', '--update', '--upgrade',
                                      action='store_true', dest='update',
                                      help='update the code from the repo before executing the main code')
            else:
                ap_group.add_argument('--no-update', '--no-upgrade',
                                      action='store_false', dest='update',
                                      help='don\'t update the code from the GitHub repo before executing the main code')
            ap_group.add_argument('-r', '--ensure-requirements',
                                  action='store_true',
                                  help='install the required packages using `pip` (might fail)')

        args: argparse.Namespace = ap.parse_intermixed_args()
        if not hasattr(sys, '_MEI''PASS'):  # if not embedded into an executable
            if args.update:
                update()
            if args.ensure_requirements:
                pip_updated: bool = False
                package: PackageRequirement
                for package in requirements:
                    pip_updated = not ensure_package(package, upgrade_pip=not pip_updated)

        try:
            from qtpy.QtCore import QLibraryInfo, QLocale, QTranslator
            from qtpy.QtWidgets import QApplication

            from utils import resource_path
            from backend import App

        except Exception as ex:
            import tkinter.messagebox
            import traceback

            traceback.print_exception(ex)
            if isinstance(ex, SyntaxError):
                tkinter.messagebox.showerror(title='Syntax Error',
                                             message=('Python ' + platform.python_version() + ' is not supported.\n' +
                                                      'Get a newer Python!'))
            elif isinstance(ex, ImportError):
                tkinter.messagebox.showerror(title='Package Missing',
                                             message=('Module ' + repr(ex.name) +
                                                      ' is either missing from the system ' +
                                                      'or cannot be loaded for another reason.\n' +
                                                      'Try to install or reinstall it.'))
            else:
                tkinter.messagebox.showerror(title='Error', message=str(ex))

        else:
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
            for a in args.file:
                window: App = App(a)
                window.show()
                windows.append(window)
            app.exec()


    main()

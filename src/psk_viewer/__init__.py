#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

if sys.version_info < (3, 8):
    message = ('The Python version ' + '.'.join(map(str, sys.version_info[:3])) + ' is not supported.\n' +
               'Use Python 3.8 or newer.')
    print(message, file=sys.stderr)

    try:
        import tkinter
        import tkinter.messagebox
    except ModuleNotFoundError:
        pass
    else:
        _root = tkinter.Tk()
        _root.withdraw()
        tkinter.messagebox.showerror(title='Outdated Python', message=message)
        _root.destroy()
    exit(1)

from typing import AnyStr, Final

__author__: Final[str] = 'StSav012'
__original_name__: Final[str] = 'psk_viewer'

try:
    from ._version import __version__
except ImportError:
    __version__ = ''


def _version_tuple(version_string: AnyStr) -> tuple[int | AnyStr, ...]:
    result: tuple[int | AnyStr, ...] = tuple()
    part: AnyStr
    for part in version_string.split('.' if isinstance(version_string, str) else b'.'):
        try:
            result += (int(part),)
        except ValueError:
            result += (part,)
    return result


def _warn_about_outdated_package(package_name: str, package_version: str, release_time: datetime) -> None:
    """ Display a warning about an outdated package a year after the package released """
    if datetime.utcnow().replace(tzinfo=timezone(timedelta())) - release_time > timedelta(days=366):
        import tkinter.messagebox
        tkinter.messagebox.showwarning(
            title='Package Outdated',
            message=f'Please update {package_name} package to {package_version} or newer')


def _make_old_qt_compatible_again() -> None:
    from qtpy import QT6, PYSIDE2
    from qtpy.QtCore import QLibraryInfo, Qt
    from qtpy.QtWidgets import QApplication, QDialog

    def to_iso_format(s: str) -> str:
        if sys.version_info < (3, 11):
            import re
            from typing import Callable

            if s.endswith('Z'):
                # '2011-11-04T00:05:23Z'
                s = s[:-1] + '+00:00'

            def from_iso_datetime(m: re.Match[str]) -> str:
                groups: dict[str, str] = m.groupdict('')
                date: str = f"{m['year']}-{m['month']}-{m['day']}"
                time: str = \
                    f"{groups['hour']:0>2}:{groups['minute']:0>2}:{groups['second']:0>2}.{groups['fraction']:0<6}"
                return date + 'T' + time + groups['offset']

            def from_iso_calendar(m: re.Match[str]) -> str:
                from datetime import date

                groups: dict[str, str] = m.groupdict('')
                date: str = \
                    date.fromisocalendar(year=int(m['year']), week=int(m['week']), day=int(m['dof'])).isoformat()
                time: str = \
                    f"{groups['hour']:0>2}:{groups['minute']:0>2}:{groups['second']:0>2}.{groups['fraction']:0<6}"
                return date + 'T' + time + groups['offset']

            patterns: dict[str, Callable[[re.Match[str]], str]] = {
                # '20111104', '20111104T000523283'
                r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'
                r'(.(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})(?P<fraction>\d+)?)?'
                r'(?P<offset>[+\-].+)?': from_iso_datetime,
                # '2011-11-04', '2011-11-04T00:05:23.283', '2011-11-04T00:05:23.283+00:00'
                r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
                r'(.(?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})(\.(?P<fraction>\d+))?)?'
                r'(?P<offset>[+\-].+)?': from_iso_datetime,
                # '2011-W01-2T00:05:23.283'
                r'(?P<year>\d{4})-W(?P<week>\d{1,2})-(?P<dof>\d{1,2})'
                r'(.(?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})(\.(?P<fraction>\d+))?)?'
                r'(?P<offset>[+\-].+)?': from_iso_calendar,
                # '2011W0102T000523283'
                r'(?P<year>\d{4})-W(?P<week>\d{2})-(?P<dof>\d{2})'
                r'(.(?P<hour>\d{1,2})(?P<minute>\d{1,2})(?P<second>\d{1,2})(?P<fraction>\d+)?)?'
                r'(?P<offset>[+\-].+)?': from_iso_calendar,
            }
            match: re.Match[str] | None
            for p in patterns:
                match = re.fullmatch(p, s)
                if match is not None:
                    s = patterns[p](match)
                    break

        return s

    if PYSIDE2:
        QApplication.exec = QApplication.exec_
        QDialog.exec = QDialog.exec_

    if not QT6:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    from qtpy import __version__

    if _version_tuple(__version__) < _version_tuple('2.3.1'):
        _warn_about_outdated_package(package_name='QtPy', package_version='2.3.1',
                                     release_time=datetime.fromisoformat(to_iso_format('2023-03-28T23:06:05Z')))
        if QT6:
            QLibraryInfo.LibraryLocation = QLibraryInfo.LibraryPath
    if _version_tuple(__version__) < _version_tuple('2.4.0'):
        # 2.4.0 is not released yet, so no warning until there is the release time
        if not QT6:
            QLibraryInfo.path = lambda *args, **kwargs: QLibraryInfo.location(*args, **kwargs)
            QLibraryInfo.LibraryPath = QLibraryInfo.LibraryLocation

    from pyqtgraph import __version__

    if _version_tuple(__version__) < _version_tuple('0.13.2'):
        _warn_about_outdated_package(package_name='pyqtgraph', package_version='0.13.2',
                                     release_time=datetime.fromisoformat('2023-03-04T05:08:12Z'))

        import pyqtgraph as pg
        from qtpy.QtWidgets import QAbstractSpinBox

        pg.SpinBox.setMaximumHeight = lambda self, max_h: QAbstractSpinBox.setMaximumHeight(self, round(max_h))
    if _version_tuple(__version__) < _version_tuple('0.13.3'):
        _warn_about_outdated_package(package_name='pyqtgraph', package_version='0.13.3',
                                     release_time=datetime.fromisoformat('2023-04-14T21:24:10Z'))

        from qtpy.QtCore import qVersion

        if _version_tuple(qVersion()) >= _version_tuple('6.5.0'):
            raise RuntimeWarning('Qt6 6.5.0 or newer breaks the plotting in PyQtGraph 0.13.2 and older. '
                                 'Either update PyQtGraph or install an older version of Qt.')


def main() -> int:
    import argparse
    import platform

    ap: argparse.ArgumentParser = argparse.ArgumentParser(
        allow_abbrev=True,
        description='IPM RAS PSK and FS spectrometer files viewer.\n'
                    f'Find more at https://github.com/{__author__}/{__original_name__}.')
    ap.add_argument('file', type=str, nargs=argparse.ZERO_OR_MORE, default=[''])
    args: argparse.Namespace = ap.parse_intermixed_args()

    try:
        from qtpy.QtCore import QLibraryInfo, QLocale, QTranslator
        from qtpy.QtWidgets import QApplication

        _make_old_qt_compatible_again()

        from .utils import resource_path
        from .app import App

    except Exception as ex:
        import traceback
        from contextlib import suppress

        traceback.print_exc()

        with suppress(ModuleNotFoundError):
            import tkinter
            import tkinter.messagebox

            error_message: str
            if isinstance(ex, SyntaxError):
                error_message = ('Python ' + platform.python_version() + ' is not supported.\n' +
                                 'Get a newer Python!')
            elif isinstance(ex, ImportError):
                error_message = ('Module ' + repr(ex.name) +
                                 ' is either missing from the system or cannot be loaded for another reason.\n' +
                                 'Try to install or reinstall it.')
            else:
                error_message = str(ex)

            try:
                import tkinter
                import tkinter.messagebox
            except ModuleNotFoundError:
                input(error_message)
            else:
                print(error_message, file=sys.stderr)

                root: tkinter.Tk = tkinter.Tk()
                root.withdraw()
                if isinstance(ex, SyntaxError):
                    tkinter.messagebox.showerror(title='Syntax Error', message=error_message)
                elif isinstance(ex, ImportError):
                    tkinter.messagebox.showerror(title='Package Missing', message=error_message)
                else:
                    tkinter.messagebox.showerror(title='Error', message=error_message)
                root.destroy()
        return 1

    else:
        app: QApplication = QApplication(sys.argv)

        languages: set[str] = set(QLocale().uiLanguages() + [QLocale().bcp47Name(), QLocale().name()])
        language: str
        qt_translator: QTranslator = QTranslator()
        for language in languages:
            if qt_translator.load('qt_' + language,
                                  QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
                QApplication.installTranslator(qt_translator)
                break
        qtbase_translator: QTranslator = QTranslator()
        for language in languages:
            if qtbase_translator.load('qtbase_' + language,
                                      QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
                QApplication.installTranslator(qtbase_translator)
                break
        my_translator: QTranslator = QTranslator()
        for language in languages:
            if my_translator.load(language, resource_path('translations')):
                QApplication.installTranslator(my_translator)
                break

        windows: list[App] = []
        for a in args.file:
            window: App = App(a)
            window.show()
            windows.append(window)
        return app.exec()

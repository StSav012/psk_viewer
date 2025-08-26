#!/usr/bin/env python3

import enum
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AnyStr, Final

__author__: Final[str] = "StSav012"
__original_name__: Final[str] = "psk_viewer"

try:
    from ._version import __version__
except ImportError:
    __version__ = ""


def _version_tuple(version_string: AnyStr) -> tuple[int | AnyStr, ...]:
    result: tuple[int | AnyStr, ...] = tuple()
    part: AnyStr
    for part in version_string.split("." if isinstance(version_string, str) else b"."):
        try:
            result += (int(part),)
        except ValueError:
            # follow `pkg_resources` version 0.6a9: remove dashes to sort letters after digits
            result += (
                (part.replace("-", ""),)
                if isinstance(part, str)
                else (part.replace(b"-", b""),)
            )
    return result


def _warn_about_outdated_package(
    package_name: str, package_version: str, release_time: datetime
) -> None:
    """Display a warning about an outdated package a year after the package released."""
    if datetime.now().replace(tzinfo=timezone(timedelta())) - release_time > timedelta(
        days=366
    ):
        import tkinter.messagebox

        tkinter.messagebox.showwarning(
            title="Package Outdated",
            message=f"Please update {package_name} package to {package_version} or newer",
        )


def _make_old_qt_compatible_again() -> None:
    from typing import Callable

    from qtpy import PYQT_VERSION, PYSIDE2, QT6
    from qtpy.QtCore import QLibraryInfo, Qt, qVersion
    from qtpy.QtWidgets import QApplication, QDialog

    def to_iso_format(s: str) -> str:
        if sys.version_info < (3, 11, 0):
            import re

            if s.endswith("Z"):
                # '2011-11-04T00:05:23Z'
                s = s[:-1] + "+00:00"

            def from_iso_datetime(m: re.Match[str]) -> str:
                groups: dict[str, str] = m.groupdict("")
                date: str = f"{m['year']}-{m['month']}-{m['day']}"
                time: str = ":".join(
                    (
                        f"{groups['hour']:0>2}",
                        f"{groups['minute']:0>2}",
                        f"{groups['second']:0>2}.{groups['fraction']:0<6}",
                    )
                )
                return date + "T" + time + groups["offset"]

            def from_iso_calendar(m: re.Match[str]) -> str:
                from datetime import date

                groups: dict[str, str] = m.groupdict("")
                date: str = date.fromisocalendar(
                    year=int(m["year"]), week=int(m["week"]), day=int(m["dof"])
                ).isoformat()
                time: str = ":".join(
                    (
                        f"{groups['hour']:0>2}",
                        f"{groups['minute']:0>2}",
                        f"{groups['second']:0>2}.{groups['fraction']:0<6}",
                    )
                )
                return date + "T" + time + groups["offset"]

            patterns: dict[str, Callable[[re.Match[str]], str]] = {
                # '20111104', '20111104T000523283'
                r"(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})"
                r"(.(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})(?P<fraction>\d+)?)?"
                r"(?P<offset>[+\-].+)?": from_iso_datetime,
                # '2011-11-04', '2011-11-04T00:05:23.283', '2011-11-04T00:05:23.283+00:00'
                r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
                r"(.(?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})(\.(?P<fraction>\d+))?)?"
                r"(?P<offset>[+\-].+)?": from_iso_datetime,
                # '2011-W01-2T00:05:23.283'
                r"(?P<year>\d{4})-W(?P<week>\d{1,2})-(?P<dof>\d{1,2})"
                r"(.(?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})(\.(?P<fraction>\d+))?)?"
                r"(?P<offset>[+\-].+)?": from_iso_calendar,
                # '2011W0102T000523283'
                r"(?P<year>\d{4})-W(?P<week>\d{2})-(?P<dof>\d{2})"
                r"(.(?P<hour>\d{1,2})(?P<minute>\d{1,2})(?P<second>\d{1,2})(?P<fraction>\d+)?)?"
                r"(?P<offset>[+\-].+)?": from_iso_calendar,
            }
            match: re.Match[str] | None
            for p in patterns:
                match = re.fullmatch(p, s)
                if match is not None:
                    s = patterns[p](match)
                    break

        return s

    if not QT6:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

        Qt.ColorScheme = enum.IntEnum("ColorScheme", ["Unknown", "Light", "Dark"])

    if PYQT_VERSION is not None:
        # i.e., PyQt*
        from typing import Callable

        from qtpy import QtCore

        class Slot:
            def __init__(self, *_: type) -> None:
                pass

            def __call__(self, fn: Callable) -> Callable:
                return fn

        QtCore.Slot = Slot

    if PYSIDE2:
        from qtpy.QtCore import Signal
        from qtpy.QtGui import QStyleHints

        QStyleHints.colorSchemeChanged = Signal(
            Qt.ColorScheme, name="colorSchemeChanged"
        )

    from qtpy import __version__

    if _version_tuple(__version__) < _version_tuple("2.3.1"):
        _warn_about_outdated_package(
            package_name="QtPy",
            package_version="2.3.1",
            release_time=datetime.fromisoformat(to_iso_format("2023-03-28T23:06:05Z")),
        )
        if QT6:
            QLibraryInfo.LibraryLocation = QLibraryInfo.LibraryPath
    if _version_tuple(__version__) < _version_tuple("2.4.0"):
        _warn_about_outdated_package(
            package_name="QtPy",
            package_version="2.4.0",
            release_time=datetime.fromisoformat(to_iso_format("2023-08-29T16:24:56Z")),
        )
        if PYSIDE2:
            QApplication.exec = QApplication.exec_
            QDialog.exec = QDialog.exec_

        if not QT6:
            QLibraryInfo.path = lambda *args, **kwargs: QLibraryInfo.location(
                *args, **kwargs
            )
            QLibraryInfo.LibraryPath = QLibraryInfo.LibraryLocation

        if _version_tuple(qVersion()) < _version_tuple("6.3"):
            from functools import partialmethod

            from qtpy.QtCore import QObject
            from qtpy.QtGui import QIcon, QKeySequence
            from qtpy.QtWidgets import QAction, QMenu, QToolBar, QWidget

            def add_action(
                self: QWidget,
                *args: object,
                old_add_action: (
                    Callable[[QWidget, str], QAction]
                    | Callable[[QWidget, str, QObject, bytes], QAction]
                    | Callable[[QWidget, QIcon, str, QObject], QAction]
                    | Callable[[QWidget, str, QObject, bytes, QKeySequence], QAction]
                    | Callable[
                        [QWidget, QIcon, str, QObject, bytes, QKeySequence], QAction
                    ]
                    | Callable[[QWidget, object, ...], QAction | None]
                ),
            ) -> QAction:
                action: QAction
                icon: QIcon
                text: str
                shortcut: QKeySequence | QKeySequence.StandardKey | str | int
                receiver: QObject
                member: bytes
                if all(
                    isinstance(arg, t)
                    for arg, t in zip(
                        args,
                        [
                            str,
                            (QKeySequence, QKeySequence.StandardKey, str, int),
                            QObject,
                            bytes,
                        ],
                    )
                ):
                    if len(args) == 2:
                        text, shortcut = args
                        action = old_add_action(self, text)
                        action.setShortcut(shortcut)
                    elif len(args) == 3:
                        text, shortcut, receiver = args
                        action = old_add_action(self, text, receiver)
                        action.setShortcut(shortcut)
                    elif len(args) == 4:
                        text, shortcut, receiver, member = args
                        action = old_add_action(self, text, receiver, member, shortcut)
                    else:
                        return old_add_action(self, *args)
                    return action
                if all(
                    isinstance(arg, t)
                    for arg, t in zip(
                        args,
                        [
                            QIcon,
                            str,
                            (QKeySequence, QKeySequence.StandardKey, str, int),
                            QObject,
                            bytes,
                        ],
                    )
                ):
                    if len(args) == 3:
                        icon, text, shortcut = args
                        action = old_add_action(self, icon, text)
                        action.setShortcut(QKeySequence(shortcut))
                    elif len(args) == 4:
                        icon, text, shortcut, receiver = args
                        action = old_add_action(self, icon, text, receiver)
                        action.setShortcut(QKeySequence(shortcut))
                    elif len(args) == 5:
                        icon, text, shortcut, receiver, member = args
                        action = old_add_action(
                            self, icon, text, receiver, member, QKeySequence(shortcut)
                        )
                    else:
                        return old_add_action(self, *args)
                    return action
                return old_add_action(self, *args)

            QMenu.addAction = partialmethod(add_action, old_add_action=QMenu.addAction)
            QToolBar.addAction = partialmethod(
                add_action, old_add_action=QToolBar.addAction
            )

    from pyqtgraph import __version__

    if _version_tuple(__version__) < _version_tuple("0.13.2"):
        _warn_about_outdated_package(
            package_name="pyqtgraph",
            package_version="0.13.2",
            release_time=datetime.fromisoformat("2023-03-04T05:08:12Z"),
        )

        import pyqtgraph as pg
        from qtpy.QtWidgets import QAbstractSpinBox

        pg.SpinBox.setMaximumHeight = (
            lambda self, max_h: QAbstractSpinBox.setMaximumHeight(self, round(max_h))
        )
    if _version_tuple(__version__) < _version_tuple("0.13.3"):
        _warn_about_outdated_package(
            package_name="pyqtgraph",
            package_version="0.13.3",
            release_time=datetime.fromisoformat("2023-04-14T21:24:10Z"),
        )

        from qtpy.QtCore import qVersion

        if _version_tuple(qVersion()) >= _version_tuple("6.5.0"):
            raise RuntimeWarning(
                " ".join(
                    (
                        "Qt6 6.5.0 or newer breaks the plotting in PyQtGraph 0.13.2 and older.",
                        "Either update PyQtGraph or install an older version of Qt.",
                    )
                )
            )


def main() -> int:
    import argparse
    import platform

    ap: argparse.ArgumentParser = argparse.ArgumentParser(
        allow_abbrev=True,
        description="IPM RAS PSK and FS spectrometer files viewer.\n"
        f"Find more at https://github.com/{__author__}/{__original_name__}.",
    )
    ap.add_argument("file", type=Path, nargs=argparse.ZERO_OR_MORE, default=[None])
    args: argparse.Namespace = ap.parse_intermixed_args()

    try:
        from qtpy.QtWidgets import QApplication

        _make_old_qt_compatible_again()

        from .app import App

    except Exception as ex:
        import traceback

        traceback.print_exc()

        error_message: str
        if isinstance(ex, SyntaxError):
            error_message = (
                "Python "
                + platform.python_version()
                + " is not supported.\n"
                + "Get a newer Python!"
            )
        elif isinstance(ex, ImportError):
            if ex.name:
                error_message = (
                    f"Module {ex.name!r} is either missing from the system or cannot be loaded for another reason."
                    "\n"
                    "Try to install or reinstall it."
                )
            else:
                error_message = str(ex)
        else:
            error_message = str(ex)

        try:
            import tkinter
            import tkinter.messagebox
        except (ImportError, ModuleNotFoundError):
            input(error_message)
        else:
            print(error_message, file=sys.stderr)

            try:
                root: tkinter.Tk = tkinter.Tk()
            except tkinter.TclError:
                pass
            else:
                root.withdraw()
                if isinstance(ex, SyntaxError):
                    tkinter.messagebox.showerror(
                        title="Syntax Error", message=error_message
                    )
                elif isinstance(ex, ImportError):
                    tkinter.messagebox.showerror(
                        title="Package Missing", message=error_message
                    )
                else:
                    tkinter.messagebox.showerror(title="Error", message=error_message)
                root.destroy()

        return 1

    else:
        app: QApplication = QApplication(sys.argv)
        windows: list[App] = []
        for a in args.file:
            window: App = App(a)
            window.show()
            windows.append(window)
        return app.exec()

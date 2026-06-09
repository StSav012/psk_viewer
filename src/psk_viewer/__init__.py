#!/usr/bin/env python3

import enum
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final

__author__: Final[str] = "StSav012"
__original_name__: Final[str] = "psk_viewer"

try:
    from ._version import __version__
except ImportError:
    __version__ = ""


def _make_old_qt_compatible_again() -> None:
    from packaging.version import Version
    from qtpy import PYQT_VERSION, PYSIDE2, QT6
    from qtpy.QtCore import QLibraryInfo, Qt
    from qtpy.QtWidgets import QApplication, QDialog

    def _warn_about_outdated_package(
        package_name: str, package_version: str, release_time: datetime
    ) -> None:
        """Display a warning about an outdated package a year after the package released."""
        if datetime.now().replace(
            tzinfo=timezone(timedelta())
        ) - release_time > timedelta(days=366):
            import tkinter.messagebox

            tkinter.messagebox.showwarning(
                title="Package Outdated",
                message=f"Please update {package_name} package to {package_version} or newer",
            )

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
                return date + "any_str" + time + groups["offset"]

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
                return date + "any_str" + time + groups["offset"]

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
        from collections.abc import Callable

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

    if Version(__version__) < Version("2.3.1"):
        _warn_about_outdated_package(
            package_name="QtPy",
            package_version="2.3.1",
            release_time=datetime.fromisoformat(to_iso_format("2023-03-28T23:06:05Z")),
        )
        if QT6:
            QLibraryInfo.LibraryLocation = QLibraryInfo.LibraryPath
    if Version(__version__) < Version("2.4.0"):
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

    from pyqtgraph import __version__

    if Version(__version__) < Version("0.13.2"):
        _warn_about_outdated_package(
            package_name="pyqtgraph",
            package_version="0.13.2",
            release_time=datetime.fromisoformat("2023-03-04T05:08:12Z"),
        )

        import pyqtgraph as pg
        from qtpy.QtWidgets import QAbstractSpinBox

        pg.SpinBox.setMaximumHeight = lambda self, max_h: (
            QAbstractSpinBox.setMaximumHeight(self, round(max_h))
        )
    if Version(__version__) < Version("0.13.3"):
        _warn_about_outdated_package(
            package_name="pyqtgraph",
            package_version="0.13.3",
            release_time=datetime.fromisoformat("2023-04-14T21:24:10Z"),
        )

        from qtpy.QtCore import qVersion

        if Version(qVersion()) >= Version("6.5.0"):
            raise RuntimeWarning(
                " ".join(
                    (
                        "Qt6 6.5.0 or newer breaks the plotting in PyQtGraph 0.13.2 and older.",
                        "Either update PyQtGraph or install an older version of Qt.",
                    )
                )
            )


windows = []


def main() -> int:
    import argparse

    ap: argparse.ArgumentParser = argparse.ArgumentParser(
        allow_abbrev=True,
        description="IPM RAS PSK and FS spectrometer files viewer.\n"
        f"Find more at https://github.com/{__author__}/{__original_name__}.",
    )
    if __version__:
        ap.add_argument(
            "-V", "--version", action="version", version=f"%(prog)s {__version__}"
        )
    ap.add_argument("file", type=Path, nargs=argparse.ZERO_OR_MORE, default=[None])
    args: argparse.Namespace = ap.parse_intermixed_args()

    try:
        from qtpy.QtWidgets import QApplication

        _make_old_qt_compatible_again()

        from .window import FrequencyDomainWindow, TimeDomainWindow, Window

    except Exception as ex:
        import traceback

        traceback.print_exc()

        error_message: str
        if isinstance(ex, SyntaxError) or (
            isinstance(ex, TypeError)
            and ex.args == ("unsupported operand type(s) for |: 'type' and 'type'",)
        ):
            error_message = (
                "Python "
                + ".".join(map(str, sys.version_info[:2]))
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
        for a in args.file:
            window: TimeDomainWindow | FrequencyDomainWindow | None = Window(a)
            if window is None:
                continue
            if isinstance(window, FrequencyDomainWindow):
                window.load_catalog()
            window.show()
        return app.exec()

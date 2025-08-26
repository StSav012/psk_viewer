from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from os import PathLike, linesep
from pathlib import Path
from typing import NamedTuple, cast

import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QByteArray, QCoreApplication, QObject, QSettings
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QWidget

__all__ = ["Settings"]

_translate = QCoreApplication.translate


class Settings(QSettings):
    """convenient internal representation of the application settings."""

    class CallbackOnly(NamedTuple):
        callback: str

    class PathCallbackOnly(NamedTuple):
        callback: str

    class SpinboxAndCallback(NamedTuple):
        spinbox_opts: dict[str, bool | int | float | str]
        callback: str

    class ComboboxAndCallback(NamedTuple):
        combobox_data: dict[str, str]
        callback: str

    class EditableComboboxAndCallback(NamedTuple):
        combobox_items: Sequence[str]
        callback: str

    def __init__(self, organization: str, application: str, parent: QObject) -> None:
        super().__init__(organization, application, parent)
        self.display_processing: bool = True

        self._line_ends: dict[str, str] = {
            "\n": _translate("line end", r"line feed (\n, U+000A)"),
            "\r": _translate("line end", r"carriage return (\r, U+000D)"),
            "\r\n": _translate("line end", r"CR+LF (\r\n)"),
            "\n\r": _translate("line end", r"LF+CR (\n\r)"),
            "\x85": _translate("line end", "next line (U+0085)"),
            "\u2028": _translate("line end", "line separator (U+2028)"),
            "\u2029": _translate("line end", "paragraph separator (U+2029)"),
        }
        if linesep not in self._line_ends:
            self._line_ends[linesep] = _translate("line end", "system ({0})").format(
                repr(linesep)[1:-1]
            )
        self._csv_separators: dict[str, str] = {
            ",": _translate("csv separator", r"comma (,)"),
            "\t": _translate("csv separator", r"tab (\t)"),
            ";": _translate("csv separator", r"semicolon (;)"),
            " ": _translate("csv separator", r"space ( )"),
        }

    @property
    def dialog(
        self,
    ) -> dict[
        str | tuple[str, tuple[str, ...]],
        dict[
            str,
            CallbackOnly
            | PathCallbackOnly
            | SpinboxAndCallback
            | ComboboxAndCallback
            | EditableComboboxAndCallback,
        ],
    ]:
        self._line_ends = {
            "\n": _translate("line end", r"line feed (\n, U+000A)"),
            "\r": _translate("line end", r"carriage return (\r, U+000D)"),
            "\r\n": _translate("line end", r"CR+LF (\r\n)"),
            "\n\r": _translate("line end", r"LF+CR (\n\r)"),
            "\x85": _translate("line end", "next line (U+0085)"),
            "\u2028": _translate("line end", "line separator (U+2028)"),
            "\u2029": _translate("line end", "paragraph separator (U+2029)"),
        }
        if linesep not in self._line_ends:
            self._line_ends[linesep] = _translate("line end", "system ({0})").format(
                repr(linesep)[1:-1]
            )
        self._csv_separators = {
            ",": _translate("csv separator", r"comma (,)"),
            "\t": _translate("csv separator", r"tab (\t)"),
            ";": _translate("csv separator", r"semicolon (;)"),
            " ": _translate("csv separator", r"space ( )"),
        }

        jump_opts: dict[str, bool | int | float | str] = {
            "suffix": _translate("unit", "Hz"),
            "siPrefix": True,
            "decimals": 0,
            "dec": True,
            "compactHeight": False,
            "format": "{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
        }
        line_opts: dict[str, bool | int | float | str] = {
            "suffix": _translate("unit", "px"),
            "siPrefix": False,
            "decimals": 1,
            "dec": False,
            "step": 0.1,
            "compactHeight": False,
            "format": "{value:.{decimals}f}{suffixGap}{suffix}",
        }
        return {
            (self.tr("Processing"), ("mdi6.calculator-variant",)): (
                {
                    self.tr("Jump:"): Settings.SpinboxAndCallback(
                        jump_opts, Settings.jump.fget.__name__
                    )
                }
                if self.display_processing
                else {}
            ),
            (self.tr("Crosshair"), ("mdi6.crosshairs",)): {
                self.tr("Show crosshair lines"): Settings.CallbackOnly(
                    Settings.show_crosshair.fget.__name__
                ),
                self.tr("Show coordinates"): Settings.CallbackOnly(
                    Settings.show_coordinates_at_crosshair.fget.__name__
                ),
                self.tr("Color:"): Settings.CallbackOnly(
                    Settings.crosshair_lines_color.fget.__name__
                ),
                self.tr("Thickness:"): Settings.SpinboxAndCallback(
                    line_opts, Settings.crosshair_lines_thickness.fget.__name__
                ),
            },
            (self.tr("Line"), ("mdi6.brush",)): {
                self.tr("Color:"): Settings.CallbackOnly(
                    Settings.line_color.fget.__name__
                ),
                self.tr("Ghost Color:"): Settings.CallbackOnly(
                    Settings.ghost_line_color.fget.__name__
                ),
                self.tr("Thickness:"): Settings.SpinboxAndCallback(
                    line_opts, Settings.line_thickness.fget.__name__
                ),
            },
            # NB: there should be the same icon as in the toolbar
            (self.tr("Marks"), ("mdi6.format-color-highlight",)): {
                self.tr("Copy frequency to clipboard"): Settings.CallbackOnly(
                    Settings.copy_frequency.fget.__name__
                ),
                self.tr("Fancy exponents in the table"): Settings.CallbackOnly(
                    Settings.fancy_table_numbers.fget.__name__
                ),
                self.tr("Show log₁₀ absorption"): Settings.CallbackOnly(
                    Settings.log10_gamma.fget.__name__
                ),
                self.tr("Fill color:"): Settings.CallbackOnly(
                    Settings.mark_brush.fget.__name__
                ),
                self.tr("Border color:"): Settings.CallbackOnly(
                    Settings.mark_pen.fget.__name__
                ),
                self.tr("Size:"): Settings.SpinboxAndCallback(
                    line_opts, Settings.mark_size.fget.__name__
                ),
                self.tr("Border thickness:"): Settings.SpinboxAndCallback(
                    line_opts, Settings.mark_pen_thickness.fget.__name__
                ),
            },
            (self.tr("Export"), ("mdi6.file-export",)): {
                self.tr("Line ending:"): Settings.ComboboxAndCallback(
                    self._line_ends, Settings.line_end.fget.__name__
                ),
                self.tr("CSV separator:"): Settings.ComboboxAndCallback(
                    self._csv_separators, Settings.csv_separator.fget.__name__
                ),
            },
            (self.tr("View"), ("mdi6.binoculars",)): {
                self.tr("Translation file:"): Settings.PathCallbackOnly(
                    Settings.translation_path.fget.__name__
                ),
            },
        }

    @contextmanager
    def section(self, section: str) -> Iterator[None]:
        try:
            self.beginGroup(section)
            yield None
        finally:
            self.endGroup()

    @property
    def line_end(self) -> str:
        with self.section("export"):
            v: str = cast(str, self.value("lineEnd", linesep, str))
        if v not in self._line_ends:
            v = linesep
        return v

    @line_end.setter
    def line_end(self, new_value: str) -> None:
        if new_value not in self._line_ends:
            return
        with self.section("export"):
            self.setValue("lineEnd", new_value)

    @property
    def csv_separator(self) -> str:
        with self.section("export"):
            v: str = cast(str, self.value("csvSeparator", "\t", str))
        if v not in self._csv_separators:
            v = "\t"
        return v

    @csv_separator.setter
    def csv_separator(self, new_value: str) -> None:
        if new_value not in self._csv_separators:
            return
        with self.section("export"):
            self.setValue("csvSeparator", new_value)

    @property
    def line_color(self) -> QColor:
        with self.section("plotLine"):
            return cast(QColor, self.value("color", pg.intColor(5)))

    @line_color.setter
    def line_color(self, new_value: QColor) -> None:
        with self.section("plotLine"):
            self.setValue("color", new_value)

    @property
    def ghost_line_color(self) -> QColor:
        with self.section("ghostLine"):
            return cast(QColor, self.value("color", pg.mkColor("#888")))

    @ghost_line_color.setter
    def ghost_line_color(self, new_value: QColor) -> None:
        with self.section("ghostLine"):
            self.setValue("color", new_value)

    @property
    def line_thickness(self) -> float:
        with self.section("plotLine"):
            return cast(float, self.value("thickness", 2.0, float))

    @line_thickness.setter
    def line_thickness(self, new_value: float) -> None:
        with self.section("plotLine"):
            self.setValue("thickness", new_value)

    @property
    def copy_frequency(self) -> bool:
        with self.section("marks"):
            return cast(bool, self.value("copyFrequency", False, bool))

    @copy_frequency.setter
    def copy_frequency(self, new_value: bool) -> None:
        with self.section("marks"):
            self.setValue("copyFrequency", new_value)

    @property
    def mark_brush(self) -> QColor:
        with self.section("marks"):
            return cast(QColor, self.value("color", self.line_color))

    @mark_brush.setter
    def mark_brush(self, new_value: QColor) -> None:
        with self.section("marks"):
            self.setValue("color", new_value)

    @property
    def mark_pen(self) -> QColor:
        with self.section("marks"):
            return cast(QColor, self.value("borderColor", self.mark_brush))

    @mark_pen.setter
    def mark_pen(self, new_value: QColor) -> None:
        with self.section("marks"):
            self.setValue("borderColor", new_value)

    @property
    def mark_size(self) -> float:
        with self.section("marks"):
            return cast(float, self.value("size", 10.0, float))

    @mark_size.setter
    def mark_size(self, new_value: float) -> None:
        with self.section("marks"):
            self.setValue("size", new_value)

    @property
    def mark_pen_thickness(self) -> float:
        with self.section("marks"):
            return cast(float, self.value("borderThickness", 1.0, float))

    @mark_pen_thickness.setter
    def mark_pen_thickness(self, new_value: float) -> None:
        with self.section("marks"):
            self.setValue("borderThickness", new_value)

    @property
    def jump(self) -> float:
        with self.section("processing"):
            return cast(float, self.value("jump", 600e3, float))

    @jump.setter
    def jump(self, new_value: float) -> None:
        with self.section("processing"):
            self.setValue("jump", new_value)

    @property
    def show_crosshair(self) -> bool:
        with self.section("crosshair"):
            return cast(bool, self.value("show", True, bool))

    @show_crosshair.setter
    def show_crosshair(self, new_value: bool) -> None:
        with self.section("crosshair"):
            self.setValue("show", new_value)

    @property
    def show_coordinates_at_crosshair(self) -> bool:
        with self.section("crosshair"):
            return cast(bool, self.value("showCoordinates", True, bool))

    @show_coordinates_at_crosshair.setter
    def show_coordinates_at_crosshair(self, new_value: bool) -> None:
        with self.section("crosshair"):
            self.setValue("showCoordinates", new_value)

    @property
    def crosshair_lines_color(self) -> QColor:
        with self.section("crosshair"):
            return cast(QColor, self.value("color", pg.intColor(1)))

    @crosshair_lines_color.setter
    def crosshair_lines_color(self, new_value: QColor) -> None:
        with self.section("crosshair"):
            self.setValue("color", new_value)

    @property
    def crosshair_lines_thickness(self) -> float:
        with self.section("crosshair"):
            return cast(float, self.value("thickness", 2.0, float))

    @crosshair_lines_thickness.setter
    def crosshair_lines_thickness(self, new_value: float) -> None:
        with self.section("crosshair"):
            self.setValue("thickness", new_value)

    @property
    def fancy_table_numbers(self) -> bool:
        with self.section("marks"):
            return cast(bool, self.value("fancyFormat", True, bool))

    @fancy_table_numbers.setter
    def fancy_table_numbers(self, new_value: bool) -> None:
        with self.section("marks"):
            self.setValue("fancyFormat", new_value)

    @property
    def log10_gamma(self) -> bool:
        with self.section("marks"):
            return cast(bool, self.value("log10gamma", True, bool))

    @log10_gamma.setter
    def log10_gamma(self, new_value: bool) -> None:
        with self.section("marks"):
            self.setValue("log10gamma", new_value)

    @property
    def translation_path(self) -> Path | None:
        with self.section("translation"):
            v: str = cast(str, self.value("filePath", "", str))
        return Path(v) if v else None

    @translation_path.setter
    def translation_path(self, new_value: str | PathLike[str] | None) -> None:
        with self.section("translation"):
            self.setValue("filePath", str(new_value) if new_value is not None else "")

    @property
    def opened_file_name(self) -> Path | None:
        with self.section("location"):
            v: str = cast(str, self.value("open", "", str))
        return Path(v) if v else None

    @opened_file_name.setter
    def opened_file_name(self, filename: str | PathLike[str] | None) -> None:
        with self.section("location"):
            self.setValue("open", str(filename or ""))

    @property
    def saved_file_name(self) -> Path | None:
        with self.section("location"):
            v: str = cast(str, self.value("save", "", str))
        return Path(v) if v else None

    @saved_file_name.setter
    def saved_file_name(self, filename: str | PathLike[str] | None) -> None:
        with self.section("location"):
            self.setValue("save", str(filename or ""))

    def save(self, o: QWidget) -> None:
        name: str = o.objectName()
        if not name:
            raise AttributeError(f"No name given for {o}")
        with suppress(AttributeError), self.section("state"):
            # noinspection PyUnresolvedReferences
            self.setValue(name, o.saveState())
        with suppress(AttributeError), self.section("geometry"):
            # noinspection PyUnresolvedReferences
            self.setValue(name, o.saveGeometry())

    def restore(self, o: QWidget) -> None:
        name: str = o.objectName()
        if not name:
            raise AttributeError(f"No name given for {o}")
        with suppress(AttributeError), self.section("state"):
            # noinspection PyUnresolvedReferences
            o.restoreState(self.value(name, QByteArray()))
        with suppress(AttributeError), self.section("geometry"):
            # noinspection PyUnresolvedReferences
            o.restoreGeometry(self.value(name, QByteArray()))

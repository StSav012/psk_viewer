# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple, Sequence, cast

import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QCoreApplication, QObject, QSettings
from qtpy.QtGui import QColor

__all__ = ["Settings"]

_translate = QCoreApplication.translate


class Settings(QSettings):
    """convenient internal representation of the application settings"""

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
        if os.linesep not in self._line_ends:
            self._line_ends[os.linesep] = _translate("line end", "system ({0})").format(
                repr(os.linesep)[1:-1]
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
            (
                CallbackOnly
                | PathCallbackOnly
                | SpinboxAndCallback
                | ComboboxAndCallback
                | EditableComboboxAndCallback
            ),
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
        if os.linesep not in self._line_ends:
            self._line_ends[os.linesep] = _translate("line end", "system ({0})").format(
                repr(os.linesep)[1:-1]
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

    @property
    def line_end(self) -> str:
        self.beginGroup("export")
        v: str = cast(str, self.value("lineEnd", os.linesep, str))
        self.endGroup()
        if v not in self._line_ends:
            v = os.linesep
        return v

    @line_end.setter
    def line_end(self, new_value: str) -> None:
        if new_value not in self._line_ends:
            return
        self.beginGroup("export")
        self.setValue("lineEnd", new_value)
        self.endGroup()

    @property
    def csv_separator(self) -> str:
        self.beginGroup("export")
        v: str = cast(str, self.value("csvSeparator", "\t", str))
        self.endGroup()
        if v not in self._csv_separators:
            v = "\t"
        return v

    @csv_separator.setter
    def csv_separator(self, new_value: str) -> None:
        if new_value not in self._csv_separators:
            return
        self.beginGroup("export")
        self.setValue("csvSeparator", new_value)
        self.endGroup()

    @property
    def line_color(self) -> QColor:
        self.beginGroup("plotLine")
        v: QColor = cast(QColor, self.value("color", pg.intColor(5)))
        self.endGroup()
        return v

    @line_color.setter
    def line_color(self, new_value: QColor) -> None:
        self.beginGroup("plotLine")
        self.setValue("color", new_value)
        self.endGroup()

    @property
    def ghost_line_color(self) -> QColor:
        self.beginGroup("ghostLine")
        v: QColor = cast(QColor, self.value("color", pg.mkColor("#888")))
        self.endGroup()
        return v

    @ghost_line_color.setter
    def ghost_line_color(self, new_value: QColor) -> None:
        self.beginGroup("ghostLine")
        self.setValue("color", new_value)
        self.endGroup()

    @property
    def line_thickness(self) -> float:
        self.beginGroup("plotLine")
        v: float = cast(float, self.value("thickness", 2.0, float))
        self.endGroup()
        return v

    @line_thickness.setter
    def line_thickness(self, new_value: float) -> None:
        self.beginGroup("plotLine")
        self.setValue("thickness", new_value)
        self.endGroup()

    @property
    def copy_frequency(self) -> bool:
        self.beginGroup("marks")
        v: bool = cast(bool, self.value("copyFrequency", False, bool))
        self.endGroup()
        return v

    @copy_frequency.setter
    def copy_frequency(self, new_value: bool) -> None:
        self.beginGroup("marks")
        self.setValue("copyFrequency", new_value)
        self.endGroup()

    @property
    def mark_brush(self) -> QColor:
        self.beginGroup("marks")
        v: QColor = cast(QColor, self.value("color", self.line_color))
        self.endGroup()
        return v

    @mark_brush.setter
    def mark_brush(self, new_value: QColor) -> None:
        self.beginGroup("marks")
        self.setValue("color", new_value)
        self.endGroup()

    @property
    def mark_pen(self) -> QColor:
        self.beginGroup("marks")
        v: QColor = cast(QColor, self.value("borderColor", self.mark_brush))
        self.endGroup()
        return v

    @mark_pen.setter
    def mark_pen(self, new_value: QColor) -> None:
        self.beginGroup("marks")
        self.setValue("borderColor", new_value)
        self.endGroup()

    @property
    def mark_size(self) -> float:
        self.beginGroup("marks")
        v: float = cast(float, self.value("size", 10.0, float))
        self.endGroup()
        return v

    @mark_size.setter
    def mark_size(self, new_value: float) -> None:
        self.beginGroup("marks")
        self.setValue("size", new_value)
        self.endGroup()

    @property
    def mark_pen_thickness(self) -> float:
        self.beginGroup("marks")
        v: float = cast(float, self.value("borderThickness", 1.0, float))
        self.endGroup()
        return v

    @mark_pen_thickness.setter
    def mark_pen_thickness(self, new_value: float) -> None:
        self.beginGroup("marks")
        self.setValue("borderThickness", new_value)
        self.endGroup()

    @property
    def jump(self) -> float:
        self.beginGroup("processing")
        v: float = cast(float, self.value("jump", 600e3, float))
        self.endGroup()
        return v

    @jump.setter
    def jump(self, new_value: float) -> None:
        self.beginGroup("processing")
        self.setValue("jump", new_value)
        self.endGroup()

    @property
    def show_crosshair(self) -> bool:
        self.beginGroup("crosshair")
        v: bool = cast(bool, self.value("show", True, bool))
        self.endGroup()
        return v

    @show_crosshair.setter
    def show_crosshair(self, new_value: bool) -> None:
        self.beginGroup("crosshair")
        self.setValue("show", new_value)
        self.endGroup()

    @property
    def show_coordinates_at_crosshair(self) -> bool:
        self.beginGroup("crosshair")
        v: bool = cast(bool, self.value("showCoordinates", True, bool))
        self.endGroup()
        return v

    @show_coordinates_at_crosshair.setter
    def show_coordinates_at_crosshair(self, new_value: bool) -> None:
        self.beginGroup("crosshair")
        self.setValue("showCoordinates", new_value)
        self.endGroup()

    @property
    def crosshair_lines_color(self) -> QColor:
        self.beginGroup("crosshair")
        v: QColor = cast(QColor, self.value("color", pg.intColor(1)))
        self.endGroup()
        return v

    @crosshair_lines_color.setter
    def crosshair_lines_color(self, new_value: QColor) -> None:
        self.beginGroup("crosshair")
        self.setValue("color", new_value)
        self.endGroup()

    @property
    def crosshair_lines_thickness(self) -> float:
        self.beginGroup("crosshair")
        v: float = cast(float, self.value("thickness", 2.0, float))
        self.endGroup()
        return v

    @crosshair_lines_thickness.setter
    def crosshair_lines_thickness(self, new_value: float) -> None:
        self.beginGroup("crosshair")
        self.setValue("thickness", new_value)
        self.endGroup()

    @property
    def fancy_table_numbers(self) -> bool:
        self.beginGroup("marks")
        v: bool = cast(bool, self.value("fancyFormat", True, bool))
        self.endGroup()
        return v

    @fancy_table_numbers.setter
    def fancy_table_numbers(self, new_value: bool) -> None:
        self.beginGroup("marks")
        self.setValue("fancyFormat", new_value)
        self.endGroup()

    @property
    def log10_gamma(self) -> bool:
        self.beginGroup("marks")
        v: bool = cast(bool, self.value("log10gamma", True, bool))
        self.endGroup()
        return v

    @log10_gamma.setter
    def log10_gamma(self, new_value: bool) -> None:
        self.beginGroup("marks")
        self.setValue("log10gamma", new_value)
        self.endGroup()

    @property
    def translation_path(self) -> Path | None:
        self.beginGroup("translation")
        v: str = cast(str, self.value("filePath", "", str))
        self.endGroup()
        return Path(v) if v else None

    @translation_path.setter
    def translation_path(self, new_value: str | os.PathLike[str] | None) -> None:
        self.beginGroup("translation")
        self.setValue("filePath", str(new_value) if new_value is not None else "")
        self.endGroup()

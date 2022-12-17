# -*- coding: utf-8 -*-
from __future__ import annotations

import pyqtgraph as pg  # type: ignore
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
                            QVBoxLayout, QWidget)

from colorselector import ColorSelector
from settings import Settings

__all__ = ['Preferences']


class Preferences(QDialog):
    """ GUI preferences dialog """

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings: Settings = settings
        self.setModal(True)
        self.setWindowTitle(self.tr('Preferences'))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        check_box: QCheckBox
        combo_box: QComboBox
        spin_box: pg.SpinBox
        color_selector: ColorSelector

        layout: QVBoxLayout = QVBoxLayout(self)
        key: str
        value: dict[str, (tuple[str]
                          | tuple[dict[str, bool | int | float | str], str]
                          | tuple[list[str], list[str], str])]
        for key, value in self.settings.dialog.items():
            if not (isinstance(value, dict) and value):
                continue
            box: QGroupBox = QGroupBox(key, self)
            box_layout: QFormLayout = QFormLayout(box)
            key2: str
            value2: tuple[str] | tuple[dict[str, bool | int | float | str], str] | tuple[list[str], list[str], str]
            for key2, value2 in value.items():
                if not (isinstance(value2, tuple) and isinstance(value2[-1], str) and value2[-1]):
                    continue  # a callback name should be the last in the tuple
                if len(value2) == 1:
                    if isinstance(getattr(self.settings, value2[-1]), bool):
                        check_box = QCheckBox(self.tr(key2), box)
                        setattr(check_box, 'callback', value2[-1])
                        check_box.setChecked(getattr(self.settings, value2[-1]))
                        check_box.toggled.connect(lambda *args, sender=check_box: self._on_event(*args, sender))
                        box_layout.addWidget(check_box)
                    elif isinstance(getattr(self.settings, value2[-1]), QColor):
                        color_selector = ColorSelector(box, getattr(self.settings, value2[-1]))
                        setattr(color_selector, 'callback', value2[-1])
                        color_selector.colorSelected.connect(
                            lambda *args, sender=color_selector: self._on_event(*args, sender))
                        box_layout.addRow(key2, color_selector)
                    # no else
                elif len(value2) == 2:
                    value3: dict[str, bool | int | float | str]
                    value3 = value2[0]
                    if isinstance(getattr(self.settings, value2[-1]), float) and isinstance(value3, dict):
                        spin_box = pg.SpinBox(box, getattr(self.settings, value2[-1]))
                        spin_box.setOpts(**value3)
                        setattr(spin_box, 'callback', value2[-1])
                        spin_box.valueChanged.connect(lambda *args, sender=spin_box: self._on_event(*args, sender))
                        box_layout.addRow(key2, spin_box)
                    # no else
                elif len(value2) == 3:
                    value3a: list[str]
                    value3b: list[str]
                    value3a = value2[0]
                    value3b = value2[1]
                    if isinstance(value3a, (list, tuple)) and isinstance(value3b, (list, tuple)):
                        combo_box = QComboBox(box)
                        setattr(combo_box, 'callback', value2[-1])
                        for index, item in enumerate(value3a):
                            combo_box.addItem(self.tr(item), value3b[index])
                        combo_box.setCurrentIndex(value3b.index(getattr(self.settings, value2[-1])))
                        combo_box.currentIndexChanged.connect(
                            lambda *args, sender=combo_box: self._on_combo_box_current_index_changed(*args, sender))
                        box_layout.addRow(self.tr(key2), combo_box)
                    # no else
                # no else
            layout.addWidget(box)
        buttons: QDialogButtonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # https://forum.qt.io/post/671245
    def _on_event(self, x: bool | float | QColor, sender: QWidget) -> None:
        setattr(self.settings, getattr(sender, 'callback'), x)

    def _on_combo_box_current_index_changed(self, _: int, sender: QComboBox) -> None:
        setattr(self.settings, getattr(sender, 'callback'), sender.currentData())

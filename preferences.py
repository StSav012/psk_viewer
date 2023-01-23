# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import cast

import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QByteArray, Qt
from qtpy.QtGui import QCloseEvent, QColor
from qtpy.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QListWidget,
                            QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from colorselector import ColorSelector
from settings import Settings

__all__ = ['Preferences']


class PreferencesPage(QWidget):
    """ A page of the Preferences dialog """

    def __init__(self, value: dict[str, (tuple[str]
                                         | tuple[dict[str, bool | int | float | str], str]
                                         | tuple[list[str], list[str], str])],
                 settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings: Settings = settings

        if not (isinstance(value, dict) and value):
            raise TypeError(f'Invalid type: {type(value)}')
        layout: QFormLayout = QFormLayout(self)
        key2: str
        value2: tuple[str] | tuple[dict[str, bool | int | float | str], str] | tuple[list[str], list[str], str]
        for key2, value2 in value.items():
            if not (isinstance(value2, tuple) and isinstance(value2[-1], str) and value2[-1]):
                continue  # a callback name should be the last in the tuple
            if len(value2) == 1:
                if isinstance(getattr(self.settings, value2[-1]), bool):
                    check_box = QCheckBox(self.tr(key2), self)
                    setattr(check_box, 'callback', value2[-1])
                    check_box.setChecked(getattr(self.settings, value2[-1]))
                    check_box.toggled.connect(lambda *args, sender=check_box: self._on_event(*args, sender))
                    layout.addWidget(check_box)
                elif isinstance(getattr(self.settings, value2[-1]), QColor):
                    color_selector = ColorSelector(self, getattr(self.settings, value2[-1]))
                    setattr(color_selector, 'callback', value2[-1])
                    color_selector.colorSelected.connect(
                        lambda *args, sender=color_selector: self._on_event(*args, sender))
                    layout.addRow(key2, color_selector)
                # no else
            elif len(value2) == 2:
                value3: dict[str, bool | int | float | str] = value2[0]
                if isinstance(getattr(self.settings, value2[-1]), float) and isinstance(value3, dict):
                    spin_box = pg.SpinBox(self, getattr(self.settings, value2[-1]))
                    spin_box.setOpts(**value3)
                    setattr(spin_box, 'callback', value2[-1])
                    spin_box.valueChanged.connect(lambda *args, sender=spin_box: self._on_event(*args, sender))
                    layout.addRow(key2, spin_box)
                # no else
            elif len(value2) == 3:
                value3a: list[str] = value2[0]
                value3b: list[str] = value2[1]
                if isinstance(value3a, (list, tuple)) and isinstance(value3b, (list, tuple)):
                    combo_box = QComboBox(self)
                    setattr(combo_box, 'callback', value2[-1])
                    for index, item in enumerate(value3a):
                        combo_box.addItem(self.tr(item), value3b[index])
                    combo_box.setCurrentIndex(value3b.index(getattr(self.settings, value2[-1])))
                    combo_box.currentIndexChanged.connect(
                        lambda *args, sender=combo_box: self._on_combo_box_current_index_changed(*args, sender))
                    layout.addRow(self.tr(key2), combo_box)
                # no else
            # no else

    # https://forum.qt.io/post/671245
    def _on_event(self, x: bool | float | QColor, sender: QWidget) -> None:
        setattr(self.settings, getattr(sender, 'callback'), x)

    def _on_combo_box_current_index_changed(self, _: int, sender: QComboBox) -> None:
        setattr(self.settings, getattr(sender, 'callback'), sender.currentData())


class PreferencesBody(QScrollArea):
    """ The main area of the GUI preferences dialog """

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings: Settings = settings

        widget: QWidget = QWidget(self)
        self.setWidget(widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameStyle(0)

        check_box: QCheckBox
        combo_box: QComboBox
        spin_box: pg.SpinBox
        color_selector: ColorSelector

        layout: QHBoxLayout = QHBoxLayout(widget)
        content: QListWidget = QListWidget(widget)
        stack: QStackedWidget = QStackedWidget(widget)
        key: str
        value: dict[str, (tuple[str]
                          | tuple[dict[str, bool | int | float | str], str]
                          | tuple[list[str], list[str], str])]
        for key, value in self.settings.dialog.items():
            if not (isinstance(value, dict) and value):
                continue
            content.addItem(key)
            box: PreferencesPage = PreferencesPage(value, settings, self)
            stack.addWidget(box)
        content.setMinimumWidth(content.sizeHintForColumn(0) + 2 * content.frameWidth())
        layout.addWidget(content)
        layout.addWidget(stack)

        if content.count() > 0:
            content.setCurrentRow(0)  # select the first page

        content.currentRowChanged.connect(stack.setCurrentIndex)


class Preferences(QDialog):
    """ GUI preferences dialog """

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings: Settings = settings
        self.setModal(True)
        self.setWindowTitle(self.tr('Preferences'))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.addWidget(PreferencesBody(settings=settings, parent=parent))
        buttons: QDialogButtonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.settings.beginGroup('PreferencesDialog')
        self.restoreGeometry(cast(QByteArray, self.settings.value('windowGeometry', QByteArray())))
        self.settings.endGroup()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.beginGroup('PreferencesDialog')
        self.settings.setValue('windowGeometry', self.saveGeometry())
        self.settings.endGroup()

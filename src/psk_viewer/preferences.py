# -*- coding: utf-8 -*-
from __future__ import annotations

from functools import partial
from typing import cast

import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QByteArray, Qt
from qtpy.QtGui import QCloseEvent, QColor
from qtpy.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QListWidget,
                            QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from .colorselector import ColorSelector
from .settings import Settings

__all__ = ['Preferences']


class PreferencesPage(QWidget):
    """ A page of the Preferences dialog """

    def __init__(self, value: dict[str, (Settings.CallbackOnly
                                         | Settings.SpinboxAndCallback
                                         | Settings.ComboboxAndCallback)],
                 settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings: Settings = settings

        if not (isinstance(value, dict) and value):
            raise TypeError(f'Invalid type: {type(value)}')
        layout: QFormLayout = QFormLayout(self)
        key2: str
        value2: Settings.CallbackOnly | Settings.SpinboxAndCallback | Settings.ComboboxAndCallback

        for key2, value2 in value.items():
            if isinstance(value2, Settings.CallbackOnly):
                if isinstance(getattr(self.settings, value2.callback), bool):
                    check_box: QCheckBox = QCheckBox(self.tr(key2), self)
                    setattr(check_box, 'callback', value2.callback)
                    check_box.setChecked(getattr(self.settings, value2.callback))
                    check_box.toggled.connect(partial(self._on_event, sender=check_box))
                    layout.addWidget(check_box)
                elif isinstance(getattr(self.settings, value2.callback), QColor):
                    color_selector: ColorSelector = ColorSelector(self, getattr(self.settings, value2.callback))
                    setattr(color_selector, 'callback', value2.callback)
                    color_selector.colorSelected.connect(partial(self._on_event, sender=color_selector))
                    layout.addRow(key2, color_selector)
                # no else
            elif isinstance(value2, Settings.SpinboxAndCallback):
                spin_box: pg.SpinBox = pg.SpinBox(self, getattr(self.settings, value2.callback))
                spin_box.setOpts(**value2.spinbox_opts)
                setattr(spin_box, 'callback', value2.callback)
                spin_box.valueChanged.connect(partial(self._on_event, sender=spin_box))
                layout.addRow(key2, spin_box)
            elif isinstance(value2, Settings.ComboboxAndCallback):
                combo_box: QComboBox = QComboBox(self)
                setattr(combo_box, 'callback', value2.callback)
                for index, (data, item) in enumerate(value2.combobox_data.items()):
                    combo_box.addItem(self.tr(item), data)
                combo_box.setCurrentText(value2.combobox_data[getattr(self.settings, value2.callback)])
                combo_box.currentIndexChanged.connect(
                    partial(self._on_combo_box_current_index_changed, sender=combo_box))
                layout.addRow(self.tr(key2), combo_box)
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

        layout: QHBoxLayout = QHBoxLayout(widget)
        content: QListWidget = QListWidget(widget)
        stack: QStackedWidget = QStackedWidget(widget)
        key: str
        value: dict[str, (Settings.CallbackOnly
                          | Settings.SpinboxAndCallback
                          | Settings.ComboboxAndCallback)]
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

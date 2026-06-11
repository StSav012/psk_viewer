from functools import partial
from logging import Logger, getLogger
from pathlib import Path
from typing import Any, Protocol, TypeGuard, cast

import pyqtgraph as pg  # type: ignore
from qtawesome import icon
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QColor, QFont
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..settings import Settings
from ..utils import the
from .colorselector import ColorSelector
from .font_selector import FontSelector
from .open_file_path_entry import OpenFilePathEntry, OpenFilePathsEntry

__all__ = ["Preferences"]


class HasLogger(Protocol):
    logger: Logger
    __call__ = ...


def has_logger(cls: type) -> TypeGuard[HasLogger]:
    return hasattr(cls, "logger")


def with_logger(cls: type) -> HasLogger:
    cls.logger = getLogger(cls.__name__)
    if has_logger(cls):
        return cls
    raise RuntimeError


@with_logger
class PreferencePage(QScrollArea):
    """A page of the Preferences dialog."""

    def __init__(
        self,
        *,
        settings: Settings,
        parent: QWidget | None = None,
        **value: (
            Settings.CallbackOnly
            | Settings.PathCallbackOnly
            | Settings.PathsCallbackOnly
            | Settings.SpinboxAndCallback
            | Settings.ComboboxAndCallback
            | Settings.EditableComboboxAndCallback
        ),
    ) -> None:
        super().__init__(parent)

        widget: QWidget = QWidget(self)
        self.setWidget(widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameStyle(0)

        self._changed_settings: dict[str, Any] = {}

        # https://forum.qt.io/post/671245
        def _on_event(x: object, *, callback: str) -> None:
            self._changed_settings[callback] = x

        def _on_combo_box_current_index_changed(
            _: int, *, sender: QComboBox, callback: str
        ) -> None:
            self._changed_settings[callback] = sender.currentData()

        def fill_widget(
            w: QWidget,
            **items: (
                Settings.CallbackOnly
                | Settings.PathCallbackOnly
                | Settings.SpinboxAndCallback
                | Settings.ComboboxAndCallback
                | Settings.EditableComboboxAndCallback
            ),
        ) -> None:
            layout: QFormLayout = QFormLayout()
            w.setLayout(layout)
            label: str
            item: (
                Settings.CallbackOnly
                | Settings.PathCallbackOnly
                | Settings.SpinboxAndCallback
                | Settings.ComboboxAndCallback
                | Settings.EditableComboboxAndCallback
            )

            check_box: QCheckBox
            path_entry: OpenFilePathEntry
            paths_entry: OpenFilePathsEntry
            spin_box: pg.SpinBox
            combo_box: QComboBox
            color_selector: ColorSelector
            font_selector: FontSelector
            group_box: QGroupBox

            for label, item in items.items():
                current_value: Any = getattr(settings, item.callback)
                if isinstance(item, Settings.CallbackOnly):
                    if isinstance(current_value, bool):
                        if not item.children:
                            check_box = QCheckBox(label, w)
                            check_box.setChecked(current_value)
                            check_box.toggled.connect(
                                partial(_on_event, callback=item.callback)
                            )
                            layout.addWidget(check_box)
                        else:
                            group_box = QGroupBox(w)
                            group_box.setTitle(label)
                            group_box.setCheckable(True)
                            group_box.setChecked(current_value)
                            fill_widget(group_box, **item.children)
                            group_box.toggled.connect(
                                partial(_on_event, callback=item.callback)
                            )
                            layout.addRow(group_box)
                    elif isinstance(current_value, Path):
                        if item.children:
                            PreferencePage.logger.error(
                                f"Label {label} with type {item.callback!r} cannot have children"
                            )
                        path_entry = OpenFilePathEntry(current_value, w)
                        path_entry.changed.connect(
                            partial(_on_event, callback=item.callback)
                        )
                        layout.addRow(label, path_entry)
                    elif isinstance(current_value, QColor):
                        if item.children:
                            PreferencePage.logger.error(
                                f"Label {label} with type {item.callback!r} cannot have children"
                            )
                        color_selector = ColorSelector(
                            w, getattr(settings, item.callback)
                        )
                        color_selector.colorSelected.connect(
                            partial(_on_event, callback=item.callback)
                        )
                        layout.addRow(label, color_selector)
                    elif isinstance(current_value, QFont):
                        if item.children:
                            PreferencePage.logger.error(
                                f"Label {label} with type {item.callback!r} cannot have children"
                            )
                        font_selector = FontSelector(w, current_value)
                        font_selector.fontSelected.connect(
                            partial(_on_event, callback=item.callback)
                        )
                        layout.addRow(label, font_selector)
                    else:
                        PreferencePage.logger.error(
                            f"The type of {item.callback!r} is not supported"
                        )
                elif isinstance(item, Settings.PathCallbackOnly):
                    if isinstance(current_value, (Path, type(None))):
                        path_entry = OpenFilePathEntry(current_value, w)
                        if item.name_filters:
                            path_entry.set_name_filters(item.name_filters)
                        path_entry.changed.connect(
                            partial(_on_event, callback=item.callback)
                        )
                        layout.addRow(label, path_entry)
                    else:
                        PreferencePage.logger.error(
                            f"The type of {item.callback!r} is not supported"
                        )
                elif isinstance(item, Settings.PathsCallbackOnly):
                    if isinstance(current_value, list):
                        paths_entry = OpenFilePathsEntry(current_value, w)
                        if item.name_filters:
                            paths_entry.set_name_filters(item.name_filters)
                        paths_entry.changed.connect(
                            partial(_on_event, callback=item.callback)
                        )
                        layout.addRow(label, paths_entry)
                    else:
                        PreferencePage.logger.error(
                            f"The type of {item.callback!r} is not supported"
                        )
                elif isinstance(item, Settings.SpinboxAndCallback):
                    spin_box = pg.SpinBox(w, getattr(settings, item.callback))
                    spin_box.setOpts(**item.spinbox_opts)
                    spin_box.valueChanged.connect(
                        partial(_on_event, callback=item.callback)
                    )
                    layout.addRow(label, spin_box)
                elif isinstance(item, Settings.ComboboxAndCallback):
                    combo_box = QComboBox(w)
                    for cb_data, cb_item in item.combobox_data.items():
                        combo_box.addItem(cb_item, cb_data)
                    combo_box.setCurrentText(
                        item.combobox_data[getattr(settings, item.callback)]
                    )
                    combo_box.currentIndexChanged.connect(
                        partial(
                            _on_combo_box_current_index_changed,
                            sender=combo_box,
                            callback=item.callback,
                        )
                    )
                    layout.addRow(label, combo_box)
                elif isinstance(item, Settings.EditableComboboxAndCallback):
                    if isinstance(current_value, str):
                        current_text: str = current_value
                    else:
                        PreferencePage.logger.error(
                            f"The type of {item.callback!r} is not supported"
                        )
                        continue
                    combo_box = QComboBox(w)
                    combo_box.addItems(item.combobox_items)
                    if current_text in item.combobox_items:
                        combo_box.setCurrentIndex(
                            item.combobox_items.index(current_text)
                        )
                    else:
                        combo_box.insertItem(0, current_text)
                        combo_box.setCurrentIndex(0)
                    combo_box.setEditable(True)
                    combo_box.currentTextChanged.connect(
                        partial(_on_event, callback=item.callback)
                    )
                    layout.addRow(label, combo_box)
                else:
                    PreferencePage.logger.error(f"{item!r} is not supported")

        fill_widget(widget, **value)

    @property
    def changed_settings(self) -> dict[str, Any]:
        return self._changed_settings.copy()


@with_logger
class PreferencesBody(QSplitter):
    """The main area of the GUI preferences dialog."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesBody")

        self.setOrientation(Qt.Orientation.Horizontal)
        self.setChildrenCollapsible(False)
        self._content: QListWidget
        content: QListWidget
        content = self._content = QListWidget(self)
        self._stack: QStackedWidget = QStackedWidget(self)
        key: (
            str
            | tuple[str, tuple[str, ...]]
            | tuple[str, tuple[str, ...], tuple[tuple[str, Any], ...]]
        )
        value: dict[
            str,
            Settings.CallbackOnly
            | Settings.PathCallbackOnly
            | Settings.SpinboxAndCallback
            | Settings.ComboboxAndCallback
            | Settings.EditableComboboxAndCallback,
        ]
        for key, value in settings.dialog.items():
            if not isinstance(value, dict):
                PreferencesBody.logger.error(f"Invalid value of {key!r}: {value!r}")
                continue
            if not value:
                continue
            new_item: QListWidgetItem
            if isinstance(key, str):
                new_item = QListWidgetItem(key)
            elif isinstance(key, tuple):
                if len(key) == 1:
                    new_item = QListWidgetItem(key[0])
                elif len(key) == 2:
                    new_item = QListWidgetItem(icon(*key[1]), key[0])
                    new_item.setData(Qt.ItemDataRole.UserRole, (key[1], ()))
                elif len(key) == 3:
                    new_item = QListWidgetItem(icon(*key[1], **dict(key[2])), key[0])
                    new_item.setData(Qt.ItemDataRole.UserRole, (key[1], key[2]))
                else:
                    PreferencesBody.logger.error(f"Invalid key: {key!r}")
                    continue
            else:
                PreferencesBody.logger.error(f"Invalid key type: {key!r}")
                continue
            content.addItem(new_item)
            box: PreferencePage = PreferencePage(
                **value, settings=settings, parent=self._stack
            )
            self._stack.addWidget(box)
        content.setMinimumWidth(content.sizeHintForColumn(0) + 2 * content.frameWidth())
        self.addWidget(content)
        self.addWidget(self._stack)

        if content.count() > 0:
            content.setCurrentRow(0)  # select the first page

        content.currentRowChanged.connect(self._stack.setCurrentIndex)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.PaletteChange:
            from qtawesome import reset_cache

            reset_cache()
            for row in range(self._content.count()):
                with the(self._content.item(row)) as item:
                    if (data := item.data(Qt.ItemDataRole.UserRole)) is not None:
                        args, kwargs = data
                        item.setIcon(icon(*args, **dict(kwargs)))
        return super().event(event)

    @property
    def changed_settings(self) -> dict[str, Any]:
        changed_settings: dict[str, Any] = {}
        for index in range(self._stack.count()):
            changed_settings.update(
                cast(PreferencePage, self._stack.widget(index)).changed_settings
            )
        return changed_settings


class Preferences(QDialog):
    """GUI preferences dialog."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesDialog")

        self._settings: Settings = settings
        self.setModal(True)
        self.setWindowTitle(self.tr("Preferences"))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QVBoxLayout = QVBoxLayout(self)
        self._preferences_body: PreferencesBody = PreferencesBody(
            settings=settings, parent=parent
        )
        layout.addWidget(self._preferences_body)
        buttons: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        self.adjustSize()
        self.resize(self.width() + 4, self.height())

        self._settings.restore(self)
        self._settings.restore(self._preferences_body)

    def reject(self) -> None:
        self._settings.save(self)
        self._settings.save(self._preferences_body)
        return super().reject()

    def accept(self) -> None:
        self._settings.save(self)
        self._settings.save(self._preferences_body)

        for key, value in self._preferences_body.changed_settings.items():
            setattr(self._settings, key, value)
        return super().accept()

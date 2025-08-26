from functools import partial
from logging import Logger, getLogger
from pathlib import Path
from typing import Any, cast

import pyqtgraph as pg  # type: ignore
from qtawesome import icon
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .colorselector import ColorSelector
from .open_file_path_entry import OpenFilePathEntry
from .settings import Settings

__all__ = ["Preferences"]


class BaseLogger:
    from typing import ClassVar

    logger: ClassVar[Logger]

    try:
        from typing import ParamSpec
    except ImportError:
        # noinspection PyUnusedLocal
        class ParamSpec:
            def __init__(
                self,
                name: str,
                *,
                bound: object | None = None,
                contravariant: bool = False,
                covariant: bool = False,
                infer_variance: bool = False,
                default: object = ...,
            ) -> None: ...

    _P = ParamSpec("_P")

    def __new__(cls, *args: _P.args, **kwargs: _P.kwargs) -> "BaseLogger":
        cls.logger = getLogger(cls.__name__)
        return super().__new__(cls)


class PreferencePage(BaseLogger, QScrollArea):
    """A page of the Preferences dialog."""

    def __init__(
        self,
        value: dict[
            str,
            Settings.CallbackOnly
            | Settings.PathCallbackOnly
            | Settings.SpinboxAndCallback
            | Settings.ComboboxAndCallback
            | Settings.EditableComboboxAndCallback,
        ],
        settings: Settings,
        parent: QWidget | None = None,
    ) -> None:
        QScrollArea.__init__(self, parent)

        widget: QWidget = QWidget(self)
        self.setWidget(widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameStyle(0)

        self._changed_settings: dict[str, Any] = {}

        # https://forum.qt.io/post/671245
        def _on_event(x: bool | int | float | str, *, callback: str) -> None:
            self._changed_settings[callback] = x

        def _on_combo_box_current_index_changed(
            _: int, *, sender: QComboBox, callback: str
        ) -> None:
            self._changed_settings[callback] = sender.currentData()

        if not (isinstance(value, dict) and value):
            raise TypeError(f"Invalid type: {type(value)}")
        layout: QFormLayout = QFormLayout(self)
        key2: str
        value2: (
            Settings.CallbackOnly
            | Settings.PathCallbackOnly
            | Settings.SpinboxAndCallback
            | Settings.ComboboxAndCallback
            | Settings.EditableComboboxAndCallback
        )

        check_box: QCheckBox
        path_entry: OpenFilePathEntry
        spin_box: pg.SpinBox
        combo_box: QComboBox
        color_selector: ColorSelector

        for key2, value2 in value.items():
            current_value: Any = getattr(settings, value2.callback)
            if isinstance(value2, Settings.CallbackOnly):
                if isinstance(current_value, bool):
                    check_box = QCheckBox(key2, self)
                    check_box.setChecked(current_value)
                    check_box.toggled.connect(
                        partial(_on_event, callback=value2.callback)
                    )
                    layout.addWidget(check_box)
                elif isinstance(current_value, Path):
                    path_entry = OpenFilePathEntry(current_value, widget)
                    path_entry.changed.connect(
                        partial(_on_event, callback=value2.callback)
                    )
                    layout.addRow(key2, path_entry)
                elif isinstance(current_value, QColor):
                    color_selector = ColorSelector(
                        self, getattr(settings, value2.callback)
                    )
                    color_selector.colorSelected.connect(
                        partial(_on_event, callback=value2.callback)
                    )
                    layout.addRow(key2, color_selector)
                else:
                    PreferencePage.logger.error(
                        f"The type of {value2.callback!r} is not supported"
                    )
            elif isinstance(value2, Settings.PathCallbackOnly):
                if isinstance(current_value, (Path, type(None))):
                    path_entry = OpenFilePathEntry(current_value, widget)
                    path_entry.changed.connect(
                        partial(_on_event, callback=value2.callback)
                    )
                    layout.addRow(key2, path_entry)
                else:
                    PreferencePage.logger.error(
                        f"The type of {value2.callback!r} is not supported"
                    )
            elif isinstance(value2, Settings.SpinboxAndCallback):
                spin_box = pg.SpinBox(self, getattr(settings, value2.callback))
                spin_box.setOpts(**value2.spinbox_opts)
                spin_box.valueChanged.connect(
                    partial(_on_event, callback=value2.callback)
                )
                layout.addRow(key2, spin_box)
            elif isinstance(value2, Settings.ComboboxAndCallback):
                combo_box = QComboBox(self)
                for data, item in value2.combobox_data.items():
                    combo_box.addItem(item, data)
                combo_box.setCurrentText(
                    value2.combobox_data[getattr(settings, value2.callback)]
                )
                combo_box.currentIndexChanged.connect(
                    partial(
                        _on_combo_box_current_index_changed,
                        sender=combo_box,
                        callback=value2.callback,
                    )
                )
                layout.addRow(key2, combo_box)
            elif isinstance(value2, Settings.EditableComboboxAndCallback):
                if isinstance(current_value, str):
                    current_text: str = current_value
                else:
                    PreferencePage.logger.error(
                        f"The type of {value2.callback!r} is not supported"
                    )
                    continue
                combo_box = QComboBox(widget)
                combo_box.addItems(value2.combobox_items)
                if current_text in value2.combobox_items:
                    combo_box.setCurrentIndex(value2.combobox_items.index(current_text))
                else:
                    combo_box.insertItem(0, current_text)
                    combo_box.setCurrentIndex(0)
                combo_box.setEditable(True)
                combo_box.currentTextChanged.connect(
                    partial(_on_event, callback=value2.callback)
                )
                layout.addRow(key2, combo_box)
            else:
                PreferencePage.logger.error(f"{value2!r} is not supported")

    @property
    def changed_settings(self) -> dict[str, Any]:
        return self._changed_settings.copy()


class PreferencesBody(BaseLogger, QSplitter):
    """The main area of the GUI preferences dialog."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        QSplitter.__init__(self, parent)
        self.setObjectName("preferencesBody")

        self.setOrientation(Qt.Orientation.Horizontal)
        self.setChildrenCollapsible(False)
        content: QListWidget = QListWidget(self)
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
                elif len(key) == 3:
                    new_item = QListWidgetItem(icon(*key[1], **dict(key[2])), key[0])
                else:
                    PreferencesBody.logger.error(f"Invalid key: {key!r}")
                    continue
            else:
                PreferencesBody.logger.error(f"Invalid key type: {key!r}")
                continue
            content.addItem(new_item)
            box: PreferencePage = PreferencePage(value, settings, self._stack)
            self._stack.addWidget(box)
        content.setMinimumWidth(content.sizeHintForColumn(0) + 2 * content.frameWidth())
        self.addWidget(content)
        self.addWidget(self._stack)

        if content.count() > 0:
            content.setCurrentRow(0)  # select the first page

        content.currentRowChanged.connect(self._stack.setCurrentIndex)

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

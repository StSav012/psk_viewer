# coding: utf-8
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QToolButton, QWidget

__all__ = ["OpenFilePathEntry"]


class OpenFilePathEntry(QWidget):
    changed: ClassVar[Signal] = Signal(Path, name="changed")

    def __init__(
        self,
        initial_file_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._path: Path | None = None

        layout: QHBoxLayout = QHBoxLayout(self)

        self._label: QLineEdit = QLineEdit(self)
        self.path = initial_file_path
        self._label.setReadOnly(True)
        self._label.setMinimumWidth(self._label.height() * 4)
        layout.addWidget(self._label)

        browse_button: QToolButton = QToolButton(self)
        browse_button.setText(self.tr("&Browse…"))
        browse_button.clicked.connect(self._on_browse_button_clicked)
        layout.addWidget(browse_button)

        self._dialog: QFileDialog = QFileDialog(self)
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        _space_before_extensions: str = " " * (not self._dialog.testOption(QFileDialog.Option.HideNameFilterDetails))
        self._dialog.setNameFilter("".join((self.tr("Translations"), _space_before_extensions, "(*.qm)")))
        self._dialog.setDefaultSuffix(".qm")
        if self._path is not None:
            self._dialog.selectFile(str(self._path))

    @property
    def path(self) -> Path | None:
        return self._path

    @path.setter
    def path(self, path: Path | None) -> None:
        if path is None or not path.is_file():
            self._path = None
            self._label.clear()
            self._label.setToolTip("")
        else:
            self._path = path
            self._label.setText(str(path))
            self._label.setToolTip(str(self._path))

    @Slot()
    def _on_browse_button_clicked(self) -> None:
        if self._dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files: list[str] = self._dialog.selectedFiles()
            if selected_files:
                if Path(selected_files[0]) != self._path:
                    self.path = Path(selected_files[0])
                    self.changed.emit(self._path)

from collections.abc import Collection, Iterable
from pathlib import Path
from typing import ClassVar, NamedTuple

from qtpy.QtCore import QCoreApplication, Signal, Slot
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QToolButton,
    QWidget,
)

__all__ = ["OpenFilePathEntry", "OpenFilePathsEntry"]

_translate = QCoreApplication.translate


class OpenFilePathEntry(QWidget):
    changed: ClassVar[Signal] = Signal(Path, name="changed")

    class NameFilter(NamedTuple):
        name: str
        suffixes: Collection[str] = [""]

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
        if self._path is not None:
            self._dialog.selectFile(str(self._path))
        if self._dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files: list[str] = self._dialog.selectedFiles()
            if selected_files and Path(selected_files[0]) != self._path:
                self.path = Path(selected_files[0])
                self.changed.emit(self._path)

    def set_name_filters(self, name_filters: Collection[NameFilter]) -> None:
        def_suffix: str = ""
        nfs: list[str] = []
        all_suffixes: list[str] = []
        space_before_extensions: str = " " * (
            not self._dialog.testOption(QFileDialog.Option.HideNameFilterDetails)
        )
        for nf in name_filters:
            nfs.append(
                space_before_extensions.join(
                    (
                        nf.name,
                        "".join(
                            (
                                "(",
                                " ".join(
                                    (s if s.startswith("*") else "*" + s)
                                    for s in nf.suffixes
                                ),
                                ")",
                            )
                        ),
                    )
                )
            )
            all_suffixes.extend(
                starred_suffix
                for s in nf.suffixes
                if (starred_suffix := (s if s.startswith("*") else "*" + s))
                not in all_suffixes
            )
            if not def_suffix:
                def_suffix = next(
                    (
                        bare_suffix
                        for s in nf.suffixes
                        if (bare_suffix := s.lstrip("*")) and "*" not in bare_suffix
                    ),
                    "",
                )
        if all_suffixes:
            nfs.insert(
                0,
                space_before_extensions.join(
                    (
                        _translate("file type", "All supported"),
                        "".join(("(", " ".join(all_suffixes), ")")),
                    )
                ),
            )
        self._dialog.setNameFilters(nfs)
        self._dialog.setDefaultSuffix(def_suffix)


class OpenFilePathsEntry(QWidget):
    changed: ClassVar[Signal] = Signal(list, name="changed")

    class NameFilter(NamedTuple):
        name: str
        suffixes: Collection[str] = [""]

    def __init__(
        self,
        initial_file_paths: Collection[Path] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._paths: list[Path] = []

        layout: QHBoxLayout = QHBoxLayout(self)

        self._label: QTextEdit = QTextEdit(self)
        self.paths = initial_file_paths
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

    @property
    def paths(self) -> Collection[Path]:
        return self._paths

    @paths.setter
    def paths(self, paths: Iterable[Path]) -> None:
        self._paths = list(paths)
        self._label.setPlainText("\n".join(map(str, self._paths)))

    @Slot()
    def _on_browse_button_clicked(self) -> None:
        if self._paths:
            self._dialog.selectFile(str(self._paths[0]))
        if self._dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files: list[Path] = list(map(Path, self._dialog.selectedFiles()))
            if frozenset(selected_files) != frozenset(self._paths):
                self.paths = selected_files
                self.changed.emit(self._paths)

    def set_name_filters(self, name_filters: Collection[NameFilter]) -> None:
        def_suffix: str = ""
        nfs: list[str] = []
        all_suffixes: list[str] = []
        space_before_extensions: str = " " * (
            not self._dialog.testOption(QFileDialog.Option.HideNameFilterDetails)
        )
        for nf in name_filters:
            nfs.append(
                space_before_extensions.join(
                    (
                        nf.name,
                        "".join(
                            (
                                "(",
                                " ".join(
                                    (s if s.startswith("*") else "*" + s)
                                    for s in nf.suffixes
                                ),
                                ")",
                            )
                        ),
                    )
                )
            )
            all_suffixes.extend(
                starred_suffix
                for s in nf.suffixes
                if (starred_suffix := (s if s.startswith("*") else "*" + s))
                not in all_suffixes
            )
            if not def_suffix:
                def_suffix = next(
                    (
                        bare_suffix
                        for s in nf.suffixes
                        if (bare_suffix := s.lstrip("*")) and "*" not in bare_suffix
                    ),
                    "",
                )
        if all_suffixes:
            nfs.insert(
                0,
                space_before_extensions.join(
                    (
                        _translate("file type", "All supported"),
                        "".join(("(", " ".join(all_suffixes), ")")),
                    )
                ),
            )
        self._dialog.setNameFilters(nfs)
        self._dialog.setDefaultSuffix(def_suffix)

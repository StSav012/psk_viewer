from collections.abc import Collection, Iterable
from pathlib import Path
from typing import ClassVar, NamedTuple

from qtpy.QtCore import (
    QCoreApplication,
    QUrl,
    Qt,
    Signal,
    Slot,
)
from qtpy.QtGui import QContextMenuEvent, QDesktopServices, QKeyEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QWidget,
)

from ..utils import load_icon, the

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


class OpenFilePathsEntry(QTableWidget):
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

        self._dialog: QFileDialog = QFileDialog(self)
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        self.setAlternatingRowColors(True)
        self.setColumnCount(1)
        self.setCornerButtonEnabled(False)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        with the(self.horizontalHeader()) as header:
            header.setVisible(False)
            header.setHighlightSections(False)
            header.setStretchLastSection(True)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        with the(self.verticalHeader()) as header:
            header.setVisible(False)
            header.setHighlightSections(False)

        self.paths = initial_file_paths

        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        current_item: QTableWidgetItem | None = self.currentItem()
        if current_item is None:
            return super().contextMenuEvent(event)
        menu: QMenu = QMenu(self)
        menu.setDefaultAction(
            menu.addAction(
                load_icon(self, "open"),
                self.tr("&Browse…"),
                self._on_browse_button_clicked,
            ),
        )
        if current_item.data(Qt.ItemDataRole.UserRole) is not None:
            menu.addAction(
                load_icon(self, "delete"),
                self.tr("&Clear"),
                self._on_clear_button_clicked,
            )
            menu.addSeparator()
            menu.addAction(
                load_icon(self, "target"),
                self.tr("Open File &Location"),
                self._on_open_file_location_triggered,
            )
        menu.exec(event.globalPos())
        return super().contextMenuEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        current_item: QTableWidgetItem | None = self.currentItem()
        if current_item is not None:
            if event.key() == Qt.Key.Key_Delete:
                self._clear(current_item)
                event.accept()
            elif event.key() == Qt.Key.Key_Enter:
                self._browse(current_item)
                event.accept()
        return super().keyPressEvent(event)

    @staticmethod
    def _locate_file(item: QTableWidgetItem) -> bool:
        file_location: Path | None = item.data(Qt.ItemDataRole.UserRole)
        if file_location is None:
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_location.parent)))

    def _browse(self, item: QTableWidgetItem) -> None:
        initial_path: Path | None = item.data(Qt.ItemDataRole.UserRole)
        if initial_path is None:
            for row in range(item.row() - 1, -1, -1):
                if (item_above := self.item(row, item.column())) is not None and (
                    data := item_above.data(Qt.ItemDataRole.UserRole)
                ) is not None:
                    self._dialog.setDirectory(str(data.parent))
                    break
        else:
            self._dialog.selectFile(str(initial_path))
        old_paths: list[Path] = self.paths.copy()
        if self._dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
        selected_files: list[str] = self._dialog.selectedFiles()
        if not selected_files:
            return
        selected_path: Path = Path(selected_files[0]).resolve()
        if item.row() == self.rowCount() - 1:
            self.setRowCount(self.rowCount() + 1)
            self.setItem(item.row() + 1, 0, QTableWidgetItem())
        item.setText(str(selected_path))
        item.setToolTip(str(selected_path))
        item.setData(Qt.ItemDataRole.UserRole, selected_path)
        new_paths: list[Path] = self.paths
        if frozenset(old_paths) != frozenset(new_paths):
            self.changed.emit(new_paths)

    def _clear(self, item: QTableWidgetItem) -> None:
        selected_path: Path | None = item.data(Qt.ItemDataRole.UserRole)
        if selected_path is None:
            return
        old_paths: list[Path] = self.paths.copy()
        item.setText("")
        item.setToolTip("")
        item.setData(Qt.ItemDataRole.UserRole, None)
        if item.row() == self.rowCount() - 2:
            self.setRowCount(self.rowCount() - 1)
        new_paths: list[Path] = self.paths
        if frozenset(old_paths) != frozenset(new_paths):
            self.changed.emit(new_paths)

    @property
    def paths(self) -> list[Path]:
        paths: list[Path] = []
        item: QTableWidgetItem | None
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item is None:
                continue
            path: Path | None = item.data(Qt.ItemDataRole.UserRole)
            if path is not None:
                paths.append(path)
        return paths

    @paths.setter
    def paths(self, paths: Iterable[Path]) -> None:
        row: int
        item: QTableWidgetItem
        for row, path in enumerate(paths):
            self.setRowCount(row + 2)
            item = QTableWidgetItem(str(path))
            item.setToolTip(str(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.setItem(row, 0, item)
        self.setItem(self.rowCount() - 1, 0, QTableWidgetItem())

    @Slot(QTableWidgetItem)
    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        self._browse(item)

    @Slot()
    def _on_open_file_location_triggered(self) -> None:
        current_item: QTableWidgetItem | None = self.currentItem()
        if current_item is None:
            return
        self._locate_file(current_item)

    @Slot()
    def _on_browse_button_clicked(self) -> None:
        current_item: QTableWidgetItem | None = self.currentItem()
        if current_item is None:
            return
        self._browse(current_item)

    @Slot()
    def _on_clear_button_clicked(self) -> None:
        current_item: QTableWidgetItem | None = self.currentItem()
        if current_item is None:
            return
        self._clear(current_item)

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

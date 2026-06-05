from typing import cast

from qtpy.QtCore import QAbstractItemModel, QModelIndex, QPoint, Qt, Slot
from qtpy.QtGui import QKeyEvent, QKeySequence
from qtpy.QtWidgets import (
    QAction,
    QHeaderView,
    QMenu,
    QTableView,
    QWidget,
)

from ..settings import Settings
from ..utils import HeaderWithUnit, copy_to_clipboard, remove_html, the
from .found_lines_model import FoundLinesModel
from .rich_combo_box import RichComboBoxDelegate

__all__ = ["TableView"]


class TableView(QTableView):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings: Settings = settings

        def popup(pos: QPoint) -> None:
            menu: QMenu = QMenu()
            model: QAbstractItemModel = self.model()
            if not isinstance(model, FoundLinesModel):
                return
            # store the actions not to lose all of them but the last
            actions: list[QAction] = []
            index: int
            column: str | HeaderWithUnit
            for index, column in enumerate(model.header):
                action: QAction = QAction(str(column))
                action.setCheckable(True)
                action.setChecked(not self.isColumnHidden(index))
                menu.addAction(action)
                actions.append(action)
            # if only one action checked
            if sum(action.isChecked() for action in actions) == 1:
                for action in actions:
                    if action.isChecked():
                        action.setDisabled(
                            True
                        )  # don't allow hiding the last visible column
            chosen_action: QAction | None = menu.exec_(self.mapToGlobal(pos))
            if chosen_action is not None and chosen_action in actions:
                self.setColumnHidden(
                    actions.index(chosen_action), not chosen_action.isChecked()
                )

        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.setDropIndicatorShown(False)
        self.setDragDropOverwriteMode(False)
        self.setCornerButtonEnabled(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.setAlternatingRowColors(True)
        with the(self.horizontalHeader()) as header:
            header.setDefaultSectionSize(90)
            header.setHighlightSections(False)
            header.setStretchLastSection(True)
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            header.customContextMenuRequested.connect(popup)
            header.sectionCountChanged.connect(self.on_column_count_changed)
        with the(self.verticalHeader()) as header:
            header.setVisible(False)
            header.setHighlightSections(False)
        if self.model() is not None:
            self.setItemDelegateForColumn(
                self.model().columnCount() - 1,
                RichComboBoxDelegate(self),
            )

    @Slot(int, int)
    def on_column_count_changed(self, old: int, new: int) -> None:
        if old == new:
            return
        # hide columns according to the settings
        with self.settings.section("marksTable"), self.settings.read_array("columns"):
            column: int
            for column in range(old, new):
                self.settings.setArrayIndex(column)
                hidden: bool = not cast(
                    bool,
                    self.settings.value(
                        "visible", not self.isColumnHidden(column), bool
                    ),
                )
                if hidden != self.isColumnHidden(column):
                    super().setColumnHidden(column, hidden)
                    if not hidden:
                        self.resizeColumnToContents(column)

    def setColumnHidden(self, column: int, hidden: bool) -> None:
        super().setColumnHidden(column, hidden)
        with self.settings.section("marksTable"):
            header: QHeaderView = self.horizontalHeader()
            with self.settings.write_array("columns", header.count()):
                self.settings.setArrayIndex(column)
                self.settings.setValue("visible", not hidden)

    def setModel(self, model: QAbstractItemModel | None) -> None:
        super().setModel(model)
        if model is None:
            return
        for column in range(model.columnCount() - 1):
            self.setItemDelegateForColumn(column, None)
        self.setItemDelegateForColumn(
            model.columnCount() - 1,
            RichComboBoxDelegate(self),
        )
        model.modelReset.connect(self.resizeColumnsToContents)

    def stringify_table_plain_text(self, whole_table: bool = True) -> str:
        """Convert selected cells to string for copying as plain text.

        :return: the plain text representation of the selected table lines
        """
        model: QAbstractItemModel = self.model()
        if not isinstance(model, FoundLinesModel):
            return ""

        text_matrix: list[list[str]]
        if whole_table:
            text_matrix = [
                [
                    remove_html(model.formatted_item(row, column, force_plain=True))
                    for column in range(model.columnCount())
                    if not self.isColumnHidden(column)
                ]
                for row in range(model.rowCount(available_count=True))
            ]
        else:
            si: QModelIndex
            rows: list[int] = sorted(set(si.row() for si in self.selectedIndexes()))
            cols: list[int] = sorted(set(si.column() for si in self.selectedIndexes()))
            text_matrix = [["" for _ in range(len(cols))] for _ in range(len(rows))]
            for si in self.selectedIndexes():
                text_matrix[rows.index(si.row())][cols.index(si.column())] = (
                    remove_html(
                        model.formatted_item(si.row(), si.column(), force_plain=True)
                    )
                )
        text: list[str] = [
            self.settings.csv_separator.join(row_texts) for row_texts in text_matrix
        ]
        return self.settings.line_end.join(text)

    def stringify_table_html(self, whole_table: bool = True) -> str:
        """Convert selected cells to string for copying as rich text.

        :return: the rich text representation of the selected table lines
        """
        model: QAbstractItemModel = self.model()
        if not isinstance(model, FoundLinesModel):
            return ""

        text_matrix: list[list[str]]
        if whole_table:
            text_matrix = [
                [
                    (
                        "<td>"
                        + model.index(row, column).data(Qt.ItemDataRole.DisplayRole)
                        + "</td>"
                    )
                    for column in range(model.columnCount())
                    if not self.isColumnHidden(column)
                ]
                for row in range(model.rowCount(available_count=True))
            ]
        else:
            si: QModelIndex
            rows: list[int] = sorted(set(si.row() for si in self.selectedIndexes()))
            cols: list[int] = sorted(set(si.column() for si in self.selectedIndexes()))
            text_matrix = [["" for _ in range(len(cols))] for _ in range(len(rows))]
            for si in self.selectedIndexes():
                text_matrix[rows.index(si.row())][cols.index(si.column())] = (
                    "<td>" + si.data(Qt.ItemDataRole.DisplayRole) + "</td>"
                )
        text: list[str] = [
            ("<tr>" + self.settings.csv_separator.join(row_texts) + "</tr>")
            for row_texts in text_matrix
        ]
        text.insert(0, "<table>")
        text.append("</table>")
        return self.settings.line_end.join(text)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.matches(QKeySequence.StandardKey.Copy):
            copy_to_clipboard(
                self.stringify_table_plain_text(False),
                self.stringify_table_html(False),
                Qt.TextFormat.RichText,
            )
            e.accept()
        elif e.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
            e.accept()
        else:
            super().keyPressEvent(e)

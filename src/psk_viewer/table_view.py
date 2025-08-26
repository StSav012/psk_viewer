from typing import cast

from qtpy.QtCore import QAbstractItemModel, QModelIndex, QPoint, Qt
from qtpy.QtGui import QKeyEvent, QKeySequence
from qtpy.QtWidgets import QAction, QHeaderView, QMenu, QTableView, QWidget

from .found_lines_model import FoundLinesModel
from .settings import Settings
from .utils import HeaderWithUnit, copy_to_clipboard

__all__ = ["TableView"]


class TableView(QTableView):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings: Settings = settings

        def popup(pos: QPoint) -> None:
            menu: QMenu = QMenu()
            model: FoundLinesModel = cast(FoundLinesModel, self.model())
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
            if chosen_action in actions:
                self.setColumnHidden(
                    actions.index(chosen_action), not chosen_action.isChecked()
                )

        header: QHeaderView = self.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(popup)
        header.sectionCountChanged.connect(self.on_column_count_changed)

    def on_column_count_changed(self, old: int, new: int) -> None:
        if old == new:
            return
        # hide columns according to the settings
        self.settings.beginGroup("marksTable")
        self.settings.beginReadArray("columns")
        column: int
        for column in range(old, new):
            self.settings.setArrayIndex(column)
            hidden: bool = not cast(
                bool,
                self.settings.value("visible", not self.isColumnHidden(column), bool),
            )
            if hidden != self.isColumnHidden(column):
                super().setColumnHidden(column, hidden)
                if not hidden:
                    self.resizeColumnToContents(column)
        self.settings.endArray()
        self.settings.endGroup()

    def setColumnHidden(self, column: int, hidden: bool) -> None:
        super().setColumnHidden(column, hidden)
        self.settings.beginGroup("marksTable")
        header: QHeaderView = self.horizontalHeader()
        self.settings.beginWriteArray("columns", header.count())
        self.settings.setArrayIndex(column)
        self.settings.setValue("visible", not hidden)
        self.settings.endArray()
        self.settings.endGroup()

    def setModel(self, model: QAbstractItemModel | None) -> None:
        super().setModel(model)
        if model is None:
            return
        model.modelReset.connect(self.adjust_columns_widths)

    def adjust_columns_widths(self) -> None:
        self.resizeColumnsToContents()

    def stringify_table_plain_text(self, whole_table: bool = True) -> str:
        """Convert selected cells to string for copying as plain text.

        :return: the plain text representation of the selected table lines
        """
        model: FoundLinesModel = cast(FoundLinesModel, self.model())
        text_matrix: list[list[str]]
        if whole_table:
            text_matrix = [
                [
                    model.formatted_item(row, column)
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
                    model.formatted_item(si.row(), si.column())
                )
        text: list[str] = [
            self.settings.csv_separator.join(row_texts) for row_texts in text_matrix
        ]
        return self.settings.line_end.join(text)

    def stringify_table_html(self, whole_table: bool = True) -> str:
        """Convert selected cells to string for copying as rich text.

        :return: the rich text representation of the selected table lines
        """
        model: FoundLinesModel = cast(FoundLinesModel, self.model())
        text_matrix: list[list[str]]
        if whole_table:
            text_matrix = [
                [
                    ("<td>" + model.formatted_item(row, column) + "</td>")
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
                    "<td>" + model.formatted_item(si.row(), si.column()) + "</td>"
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

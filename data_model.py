# -*- coding: utf-8 -*-

from typing import Final, Iterable, List, Optional, Tuple, Union

import numpy as np
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt


class DataModel(QAbstractTableModel):
    ROW_BATCH_COUNT: Final[int] = 96

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: np.ndarray = np.empty((0, 0))
        self._rows_loaded: int = self.ROW_BATCH_COUNT

        self._header: List[str] = []
        self._format: List[Tuple[int, float]] = []
        self._sort_column: int = 0
        self._sort_order: Qt.SortOrder = Qt.DescendingOrder

    @property
    def header(self) -> List[str]:
        return self._header

    @header.setter
    def header(self, new_header: Iterable[str]):
        self._header = list(map(str, new_header))

    @property
    def all_data(self) -> np.ndarray:
        return self._data

    @property
    def is_empty(self) -> bool:
        return self._data.size == 0

    def rowCount(self, parent=None, *, available_count: bool = False) -> int:
        if available_count:
            return self._data.shape[0]
        return min(self._data.shape[0], self._rows_loaded)

    def columnCount(self, parent=None) -> int:
        return self._data.shape[1]

    def formatted_item(self, row: int, column: int, replace_hyphen: bool = False) -> str:
        value: float = self.item(row, column)
        if np.isnan(value):
            return ''
        if column >= len(self._format):
            if replace_hyphen:
                return str(value).replace('-', '−')
            return str(value)
        precision: int
        scale: float
        precision, scale = self._format[column]
        if replace_hyphen:
            return f'{value * scale:.{precision}f}'.replace('-', '−')
        return f'{value * scale:.{precision}f}'

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Optional[str]:
        if index.isValid() and role == Qt.DisplayRole:
            return self.formatted_item(index.row(), index.column(), replace_hyphen=True)
        return None

    def item(self, row_index: int, column_index: int) -> float:
        if 0 <= row_index < self._data.shape[0] and 0 <= column_index < self._data.shape[1]:
            return self._data[row_index, column_index]
        else:
            return np.nan

    def headerData(self, col, orientation, role: int = Qt.DisplayRole) -> Optional[str]:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and 0 <= col < len(self._header):
            return self._header[col]
        return None

    def setHeaderData(self, section: int, orientation: Qt.Orientation, value: str, role: int = Qt.DisplayRole) -> bool:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and 0 <= section < len(self._header):
            self._header[section] = value
            return True
        return False

    def set_format(self, new_format: List[Tuple[int, float]]):
        self.beginResetModel()
        self._format = [(int(p), float(s) if not np.isnan(float(s)) else 1.0)
                        for p, s in new_format]
        self.endResetModel()

    def set_data(self, new_data: Union[List[List[float]], np.ndarray]):
        self.beginResetModel()
        self._data = np.array(new_data)
        self._rows_loaded = self.ROW_BATCH_COUNT
        if self._sort_column < self._data.shape[1]:
            sort_indices: np.ndarray = np.argsort(self._data[:, self._sort_column], kind='heapsort')
            if self._sort_order == Qt.DescendingOrder:
                sort_indices = sort_indices[::-1]
            self._data = self._data[sort_indices]
        self.endResetModel()

    def append_data(self, new_data_line: Union[List[float], np.ndarray]):
        self.beginResetModel()
        if self._data.shape[1] == len(new_data_line):
            self._data = np.row_stack((self._data, new_data_line))
            if self._sort_column < self._data.shape[1]:
                sort_indices: np.ndarray = np.argsort(self._data[:, self._sort_column], kind='heapsort')
                if self._sort_order == Qt.DescendingOrder:
                    sort_indices = sort_indices[::-1]
                self._data = self._data[sort_indices]
        else:
            self._data = np.array([new_data_line])
        self.endResetModel()

    def extend_data(self, new_data_lines: Union[List[List[float]], np.ndarray]):
        self.beginResetModel()
        for new_data_line in new_data_lines:
            if self._data.shape[1] == len(new_data_line):
                self._data = np.row_stack((self._data, new_data_line))
        if self._sort_column < self._data.shape[1]:
            sort_indices: np.ndarray = np.argsort(self._data[:, self._sort_column], kind='heapsort')
            if self._sort_order == Qt.DescendingOrder:
                sort_indices = sort_indices[::-1]
            self._data = self._data[sort_indices]
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._data: np.ndarray = np.empty((0, 0))
        self._rows_loaded: int = self.ROW_BATCH_COUNT
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        if column >= self._data.shape[1]:
            return
        sort_indices: np.ndarray = np.argsort(self._data[:, column], kind='heapsort')
        if order == Qt.DescendingOrder:
            sort_indices = sort_indices[::-1]
        self._sort_column = column
        self._sort_order = order
        self.beginResetModel()
        self._data = self._data[sort_indices]
        self.endResetModel()

    def canFetchMore(self, index: QModelIndex = QModelIndex()) -> bool:
        return self._data.shape[1] > self._rows_loaded

    def fetchMore(self, index: QModelIndex = QModelIndex()):
        # FIXME: if the 0th column is hidden, no data gets fetched despite it is available according to `canFetchMore`
        #  For now, the only solution is to load more than one screen can display. If the table is scrolled, data loads.
        # https://sateeshkumarb.wordpress.com/2012/04/01/paginated-display-of-table-data-in-pyqt/
        reminder: int = self._data.shape[1] - self._rows_loaded
        items_to_fetch: int = min(reminder, self.ROW_BATCH_COUNT)
        self.beginInsertRows(QModelIndex(), self._rows_loaded, self._rows_loaded + items_to_fetch - 1)
        self._rows_loaded += items_to_fetch
        self.endInsertRows()

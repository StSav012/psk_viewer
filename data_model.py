# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Final, Iterable, NamedTuple, cast

import numpy as np
from numpy.typing import NDArray
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt

from utils import superscript_tag

__all__ = ('DataModel',)


class DataModel(QAbstractTableModel):
    ROW_BATCH_COUNT: Final[int] = 5

    class Format(NamedTuple):
        precision: int
        scale: float
        fancy: bool

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data: NDArray[np.float64] = np.empty((0, 0))
        self._rows_loaded: int = self.ROW_BATCH_COUNT

        self._header: list[str] = []
        self._format: list[DataModel.Format] = []
        self._sort_column: int = 0
        self._sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder

    @property
    def header(self) -> list[str]:
        return self._header

    @header.setter
    def header(self, new_header: Iterable[str]) -> None:
        self._header = list(map(str, new_header))

    @property
    def all_data(self) -> NDArray[np.float64]:
        return self._data

    @property
    def is_empty(self) -> bool:
        return bool(self._data.size == 0)

    def rowCount(self, parent: QModelIndex | None = None, *, available_count: bool = False) -> int:
        if available_count:
            return cast(int, self._data.shape[0])
        return min(cast(int, self._data.shape[0]), self._rows_loaded)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return cast(int, self._data.shape[1])

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
        fancy: bool
        precision, scale, fancy = self._format[column]
        if np.isnan(scale):
            if fancy:
                s: str = f'{value:.{precision}e}'
                while 'e+0' in s:
                    s = s.replace('e+0', 'e+')
                while 'e-0' in s:
                    s = s.replace('e-0', 'e-')
                if s.endswith('e+') or s.endswith('e-'):
                    s = s[:-2]
                s = s.replace('e+', 'e', 1)
                if replace_hyphen:
                    s = s.replace('-', '−')
                s = s.replace('e', '×10<sup>', 1) + '</sup>'
                return superscript_tag(s)
            else:
                if replace_hyphen:
                    return f'{value:.{precision}e}'.replace('-', '−')
                return f'{value:.{precision}e}'
        if replace_hyphen:
            return f'{value * scale:.{precision}f}'.replace('-', '−')
        return f'{value * scale:.{precision}f}'

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            return self.formatted_item(index.row(), index.column(), replace_hyphen=True)
        return None

    def item(self, row_index: int, column_index: int) -> float:
        if 0 <= row_index < self._data.shape[0] and 0 <= column_index < self._data.shape[1]:
            return cast(float, self._data[row_index, column_index])
        else:
            return cast(float, np.nan)

    def headerData(self, col: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if (orientation == Qt.Orientation.Horizontal
                and role == Qt.ItemDataRole.DisplayRole and 0 <= col < len(self._header)):
            return self._header[col]
        return None

    def setHeaderData(self, section: int, orientation: Qt.Orientation, value: str,
                      role: int = Qt.ItemDataRole.DisplayRole) -> bool:
        if (orientation == Qt.Orientation.Horizontal
                and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(self._header)):
            self._header[section] = value
            return True
        return False

    def set_format(self, new_format: list[tuple[int, float, bool] | tuple[int, float]]) -> None:
        self.beginResetModel()
        f: tuple[int, float, bool] | tuple[int, float]
        self._format = [DataModel.Format(precision=int(round(f[0])), scale=float(f[1]),
                                         fancy=bool(f[2]) if len(f) > 2 else False)
                        for f in new_format]
        self.endResetModel()

    def set_data(self, new_data: list[list[float]] | NDArray[np.float64]) -> None:
        self.beginResetModel()
        self._data = np.array(new_data)
        self._rows_loaded = self.ROW_BATCH_COUNT
        if self._sort_column < self._data.shape[1]:
            sort_indices: NDArray[np.float64] = np.argsort(self._data[:, self._sort_column], kind='heapsort')
            if self._sort_order == Qt.SortOrder.DescendingOrder:
                sort_indices = sort_indices[::-1]
            self._data = self._data[sort_indices]
        self.endResetModel()

    def append_data(self, new_data_line: list[float] | NDArray[np.float64]) -> None:
        self.beginResetModel()
        if self._data.shape[1] == len(new_data_line):
            self._data = np.row_stack((self._data, new_data_line))
            if self._sort_column < self._data.shape[1]:
                sort_indices: NDArray[np.float64] = np.argsort(self._data[:, self._sort_column], kind='heapsort')
                if self._sort_order == Qt.SortOrder.DescendingOrder:
                    sort_indices = sort_indices[::-1]
                self._data = self._data[sort_indices]
        else:
            self._data = np.array([new_data_line])
        self.endResetModel()

    def extend_data(self, new_data_lines: list[list[float]] | NDArray[np.float64]) -> None:
        self.beginResetModel()
        for new_data_line in new_data_lines:
            if self._data.shape[1] == len(new_data_line):
                self._data = np.row_stack((self._data, new_data_line))
        if self._sort_column < self._data.shape[1]:
            sort_indices: NDArray[np.float64] = np.argsort(self._data[:, self._sort_column], kind='heapsort')
            if self._sort_order == Qt.SortOrder.DescendingOrder:
                sort_indices = sort_indices[::-1]
            self._data = self._data[sort_indices]
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._data = np.empty((0, 0))
        self._rows_loaded = self.ROW_BATCH_COUNT
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if column >= self._data.shape[1]:
            return
        sort_indices: NDArray[np.float64] = np.argsort(self._data[:, column], kind='heapsort')
        if order == Qt.SortOrder.DescendingOrder:
            sort_indices = sort_indices[::-1]
        self._sort_column = column
        self._sort_order = order
        self.beginResetModel()
        self._data = self._data[sort_indices]
        self.endResetModel()

    def canFetchMore(self, index: QModelIndex = QModelIndex()) -> bool:
        return cast(bool, self._data.shape[0] > self._rows_loaded)

    def fetchMore(self, index: QModelIndex = QModelIndex()) -> None:
        # https://sateeshkumarb.wordpress.com/2012/04/01/paginated-display-of-table-data-in-pyqt/
        reminder: int = self._data.shape[0] - self._rows_loaded
        items_to_fetch: int = min(reminder, self.ROW_BATCH_COUNT)
        self.beginInsertRows(QModelIndex(), self._rows_loaded, self._rows_loaded + items_to_fetch - 1)
        self._rows_loaded += items_to_fetch
        self.endInsertRows()

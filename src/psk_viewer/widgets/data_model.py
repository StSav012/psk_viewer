from collections.abc import Iterable
from contextlib import suppress
from typing import Final, NamedTuple, cast

import numpy as np
from numpy.typing import NDArray
from qtpy.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)

from ..utils import HeaderWithUnit, superscript_tag

__all__ = ("DataModel",)


class DataModel(QAbstractTableModel):
    ROW_BATCH_COUNT: Final[int] = 5

    class Format(NamedTuple):
        precision: int
        scale: float
        fancy: bool = False
        log10: bool = False

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._data: dict[tuple[int, int], dict[Qt.ItemDataRole | int, object]] = {}
        self._numeric_data: NDArray[np.double] = np.empty((0, 0))
        self._rows_loaded: int = DataModel.ROW_BATCH_COUNT

        self._header: list[str | HeaderWithUnit] = []
        self._format: list[DataModel.Format] = []

    @property
    def header(self) -> list[str | HeaderWithUnit]:
        return self._header[: self.columnCount()]

    @header.setter
    def header(self, new_header: Iterable[str | HeaderWithUnit]) -> None:
        self._header = list(new_header)
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, len(self._header) - 1)

    def all_data(self, column: int | None = None) -> NDArray[np.double]:
        if column is None:
            return self._numeric_data
        return self._numeric_data[:, column]

    @property
    def data_column_count(self) -> int:
        return self._numeric_data.shape[1]

    @property
    def is_empty(self) -> bool:
        return bool(self._numeric_data.size == 0)

    def rowCount(
        self,
        parent: QModelIndex | QPersistentModelIndex | None = None,
        *,
        available_count: bool = False,
    ) -> int:
        if available_count:
            return cast(int, self._numeric_data.shape[0])
        return min(cast(int, self._numeric_data.shape[0]), self._rows_loaded)

    def columnCount(
        self,
        parent: QModelIndex | QPersistentModelIndex | None = None,
    ) -> int:
        return len(self._header)

    def formatted_item(
        self,
        row: int,
        column: int,
        replace_hyphen: bool = False,
        force_plain: bool = False,
    ) -> str:
        def fancy_format(v: float) -> str:
            s: str = f"{v:.{precision}e}"
            while "e+0" in s:
                s = s.replace("e+0", "e+")
            while "e-0" in s:
                s = s.replace("e-0", "e-")
            if s.endswith("e+") or s.endswith("e-"):
                s = s[:-2]
            if "e" in s:
                s = s.replace("e+", "e")
                s = s.replace("e", "×10<sup>") + "</sup>"
            if replace_hyphen:
                s = s.replace("-", "−")
            return superscript_tag(s)

        value: object | None = self.item(row, column)
        if value is None:
            return "???"
        if isinstance(value, str):
            return value
        if np.isnan(value):
            return ""
        if isinstance(value, complex) and value.imag == 0.0:
            value = value.real
        if not isinstance(value, (float, complex)) or column >= len(self._format):
            return str(value).replace("-", "−", -int(replace_hyphen))
        precision: int
        scale: float
        fancy: bool
        log10: bool
        precision, scale, fancy, log10 = self._format[column]
        if log10 and isinstance(value, float):
            value = np.log10(np.complex128(value)).item()
            if isinstance(value, complex) and value.imag == 0.0:
                value = value.real
        if np.isnan(scale):
            if fancy and not force_plain:
                if isinstance(value, float):
                    return fancy_format(value)
                if isinstance(value, complex):
                    re_s: str = fancy_format(value.real)
                    im_s: str = fancy_format(value.imag)
                    if value.imag < 0:
                        return re_s + im_s + "j"
                    return re_s + "+" + im_s + "j"
            if isinstance(value, float):
                if log10:
                    return f"{value:.{precision}f}".replace(
                        "-", "−", -int(replace_hyphen)
                    )
                return f"{value:.{precision}e}".replace("-", "−", -int(replace_hyphen))
        if isinstance(value, float):
            return f"{value * scale:.{precision}f}".replace(
                "-", "−", -int(replace_hyphen)
            )
        return repr(value)

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if 0 <= index.column() < self.data_column_count:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: Qt.ItemDataRole | int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        row_index: int = index.row()
        column_index: int = index.column()
        if (
            0 <= row_index < self.rowCount(available_count=True)
            and 0 <= column_index < self.columnCount()
        ):
            key: tuple[int, int] = row_index, column_index
            with suppress(LookupError):
                return self._data[key][role]
            if 0 <= column_index < self.data_column_count:
                if role == Qt.ItemDataRole.DisplayRole:
                    data = self.formatted_item(
                        row_index,
                        column_index,
                        replace_hyphen=True,
                    )
                elif role == Qt.ItemDataRole.UserRole:
                    data = self.formatted_item(
                        row_index,
                        column_index,
                        replace_hyphen=False,
                        force_plain=True,
                    )
                else:
                    data = None
            else:
                data = self.substitution_for_cell(
                    index,
                    tuple(self._numeric_data[row_index]),
                    role,
                )
            if key not in self._data:
                self._data[key] = {}
            self._data[key][role] = data
            return data
        return None

    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: object,
        role: Qt.ItemDataRole | int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        key: tuple[int, int] = index.row(), index.column()
        if key not in self._data:
            self._data[key] = {}
        self._data[key][role] = value
        self.dataChanged.emit(index, index, [role])
        return True

    def setItemData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        roles: dict[Qt.ItemDataRole | int, object],
    ) -> bool:
        if not index.isValid():
            return False
        key: tuple[int, int] = index.row(), index.column()
        if key not in self._data:
            self._data[key] = {}
        for role, value in roles.items():
            self._data[key][role] = value
        self.dataChanged.emit(index, index, list(roles))
        return True

    def substitution_for_cell(
        self,
        index: QModelIndex | QPersistentModelIndex,
        content: tuple[object],
        role: Qt.ItemDataRole | int,
    ) -> object:
        return None

    def item(self, row: int, column: int) -> object:
        if not (0 <= row < self._numeric_data.shape[0]):
            return np.nan
        if 0 <= column < self.data_column_count:
            if self._numeric_data[row, column].imag == 0.0:
                return self._numeric_data[row, column].real.item()
            return self._numeric_data[row, column].item()
        with suppress(LookupError):
            return self._data[row, column][Qt.ItemDataRole.DisplayRole]
        if self.data_column_count <= column < self.columnCount():
            text: object | None = self.substitution_for_cell(
                self.index(row, column),
                tuple(self._numeric_data[row]),
                Qt.ItemDataRole.DisplayRole,
            )
            if isinstance(text, (str, float, complex)):
                return text
        return np.nan

    def headerData(
        self,
        col: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= col < len(self._header)
        ):
            return str(self._header[col])
        return None

    def setHeaderData(
        self,
        section: int,
        orientation: Qt.Orientation,
        value: str,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> bool:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(self._header)
        ):
            self._header[section] = value
            return True
        return False

    def set_format(self, new_format: list[Format]) -> None:
        self.beginResetModel()
        self._format = [
            DataModel.Format(
                precision=int(round(f.precision)),
                scale=float(f.scale),
                fancy=bool(f.fancy),
                log10=bool(f.log10),
            )
            for f in new_format
        ]
        self.endResetModel()

    def set_data(
        self,
        new_data: list[list[float]] | NDArray[np.double],
    ) -> None:
        self.beginResetModel()
        self._data.clear()
        self._numeric_data = np.asarray(new_data)
        self._rows_loaded = DataModel.ROW_BATCH_COUNT
        self.endResetModel()

    def extend_data(
        self,
        new_data_lines: list[list[float]] | NDArray[np.double],
    ) -> None:
        data_column_count: int = self.data_column_count
        new_data_lines = np.asarray(
            [
                (
                    list(new_data_line[:data_column_count])
                    + [np.nan] * max(0, data_column_count - len(new_data_line))
                )
                if 0 < data_column_count != len(new_data_line)
                else new_data_line
                for new_data_line in new_data_lines
            ]
        )
        self.beginInsertRows(
            QModelIndex(),
            self.rowCount(),
            self.rowCount() + new_data_lines.shape[0] - 1,
        )
        if self._numeric_data.size != 0:
            self._numeric_data = np.vstack((self._numeric_data, new_data_lines))
        else:
            self._numeric_data = new_data_lines
        self.endInsertRows()

    def remove_row(self, row: int) -> bool:
        if not (0 <= row < self._numeric_data.shape[0]):
            return False

        self.beginRemoveRows(
            QModelIndex(),
            row,
            row,
        )
        mask: NDArray[np.bool_] = np.full(self._numeric_data.shape[0], True)
        mask[row] = False
        self._numeric_data = self._numeric_data[mask]
        for r, c in list(self._data.keys()):
            if r > row:
                self._data[r - 1, c] = self._data[r, c]
                del self._data[r, c]
        self.endRemoveRows()
        return True

    def clear(self) -> None:
        self.beginResetModel()
        self._numeric_data = np.empty((0, 0))
        self._data.clear()
        self._rows_loaded = DataModel.ROW_BATCH_COUNT
        self.endResetModel()

    def canFetchMore(self, index: QModelIndex | QPersistentModelIndex) -> bool:
        return self._numeric_data.shape[0] > self._rows_loaded

    def fetchMore(self, index: QModelIndex | QPersistentModelIndex) -> None:
        # https://sateeshkumarb.wordpress.com/2012/04/01/paginated-display-of-table-data-in-pyqt/
        remainder: int = self._numeric_data.shape[0] - self._rows_loaded
        items_to_fetch: int = min(remainder, DataModel.ROW_BATCH_COUNT)
        self.beginInsertRows(
            index,
            self._rows_loaded,
            self._rows_loaded + items_to_fetch - 1,
        )
        self._rows_loaded += items_to_fetch
        self.endInsertRows()

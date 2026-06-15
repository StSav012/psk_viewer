from collections.abc import Iterable, Sequence
from contextlib import suppress
from math import inf
from pathlib import Path

# noinspection PyPackageRequirements
import numpy as np

# noinspection PyPackageRequirements
from numpy.typing import NDArray
from qtpy.QtCore import (
    QCoreApplication,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    Signal,
    Slot,
)

from ..plot_data_item import PlotDataItem
from ..utils import HeaderWithUnit, best_name
from .data_model import DataModel

__all__ = ["FoundLinesModel"]

_translate = QCoreApplication.translate


class FoundLinesModel(DataModel):
    frequencies_removed: Signal = Signal(frozenset, name="frequencies_removed")

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._catalog: object = None
        self._df: float = 0.6e6
        self._frequencies: NDArray[np.float64] = np.empty(0)
        self._log10_gamma: bool = False
        self._fancy_table_numbers: bool = False

        self._header = [""] * 4

        self.set_format(
            [
                DataModel.Format(precision=3, scale=1e-6),
                DataModel.Format(precision=4, scale=1e3),
                DataModel.Format(
                    precision=4,
                    scale=np.nan,
                    fancy=self._fancy_table_numbers,
                    log10=self._log10_gamma,
                ),
            ]
        )

        @Slot(QModelIndex, int, int)
        def on_model_rows_removed(_parent: QModelIndex, start: int, end: int) -> None:
            frequencies: set[float] = set()
            for row in range(start, end + 1):
                frequencies.add(self._numeric_data[row, 0])
            self.frequencies_removed.emit(frozenset(frequencies))

        self.rowsAboutToBeRemoved.connect(on_model_rows_removed)

    @property
    def log10_gamma(self) -> bool:
        return self._log10_gamma

    @log10_gamma.setter
    def log10_gamma(self, new_value: bool) -> None:
        if bool(new_value) == self._log10_gamma:
            return
        self._log10_gamma = bool(new_value)
        if len(self._header) >= 3:
            self._header[2] = HeaderWithUnit(
                name=_translate("plot axes labels", "Absorption"),
                unit=(
                    _translate("unit", "cm⁻¹")
                    if not self._log10_gamma
                    else _translate("unit", "log₁₀(cm⁻¹)")
                ),
            )
        self.set_format(
            [
                DataModel.Format(precision=3, scale=1e-6),
                DataModel.Format(precision=4, scale=1e3),
                DataModel.Format(
                    precision=4,
                    scale=np.nan,
                    fancy=self._fancy_table_numbers,
                    log10=self._log10_gamma,
                ),
            ]
        )
        if self.columnCount() >= 3:
            for row, column in self._data:
                if column == 2:
                    del self._data[row, column][Qt.ItemDataRole.DisplayRole]
            self.dataChanged.emit(
                self.createIndex(0, 2),
                self.createIndex(self.rowCount() - 1, 2),
            )

    @property
    def fancy_table_numbers(self) -> bool:
        return self._fancy_table_numbers

    @fancy_table_numbers.setter
    def fancy_table_numbers(self, new_value: bool) -> None:
        if bool(new_value) == self._fancy_table_numbers:
            return
        self._fancy_table_numbers = bool(new_value)
        self.set_format(
            [
                DataModel.Format(precision=3, scale=1e-6),
                DataModel.Format(precision=4, scale=1e3),
                DataModel.Format(
                    precision=4,
                    scale=np.nan,
                    fancy=self._fancy_table_numbers,
                    log10=self._log10_gamma,
                ),
            ]
        )
        if self.columnCount() >= 3:
            for row, column in self._data:
                if column == 2:
                    del self._data[row, column][Qt.ItemDataRole.DisplayRole]
            self.dataChanged.emit(
                self.createIndex(0, 2),
                self.createIndex(self.rowCount() - 1, 2),
            )

    @property
    def df(self) -> float:
        return self._df

    @df.setter
    def df(self, df: float) -> None:
        if df == self._df:
            return
        df = abs(df)
        self._df = df
        for roles in self._data.values():
            if Qt.ItemDataRole.BackgroundRole in roles:
                del roles[Qt.ItemDataRole.BackgroundRole]
        self.dataChanged.emit(
            self.createIndex(0, 0),
            self.createIndex(self.rowCount() - 1, self.columnCount() - 1),
        )

    def substitution_for_cell(
        self,
        index: QModelIndex | QPersistentModelIndex,
        content: tuple[object],
        role: Qt.ItemDataRole | int,
    ) -> object:
        _key: tuple[int, int] = index.row(), index.column()
        with suppress(LookupError):
            return self._data[_key][role]

        if not self.catalog_file_names:
            return None
        try:
            # noinspection PyPackageRequirements
            from pycatsearch.catalog import Catalog

            # noinspection PyPackageRequirements
            from pycatsearch.utils import LINES, CatalogEntryType, CatalogType
        except ImportError:
            return None

        catalog: object = self._catalog
        if not isinstance(catalog, Catalog):
            return None

        frequency, *_ = content
        frequency *= 1e-6
        entries: CatalogType = catalog.filter(
            min_frequency=frequency - self._df * 1e-6,
            max_frequency=frequency + self._df * 1e-6,
        )
        substances: list[tuple[float, CatalogEntryType]] = []
        for entry in entries.values():
            key = CatalogEntryType()
            for slot in entry.__slots__:
                if slot != LINES:
                    setattr(key, slot, getattr(entry, slot))
            weight: float = sum(
                (
                    (10.0**line.intensity / (line.frequency - frequency) ** 2)
                    if line.frequency != frequency
                    else inf
                )
                for line in entry.lines
            )
            substances.append((weight, key))
        if not substances:
            return None
        substances.sort(reverse=True, key=lambda s: s[0])
        best_line_entry: CatalogEntryType = substances[0][1]
        label: str = best_name(best_line_entry)
        data: dict[Qt.ItemDataRole | int, object] = {
            Qt.ItemDataRole.DisplayRole: label,
            Qt.ItemDataRole.UserRole: label,
            Qt.ItemDataRole.ForegroundRole: (label, best_line_entry),
            Qt.ItemDataRole.BackgroundRole: [
                (best_name(substance[1]), substance[1]) for substance in substances
            ],
        }
        if _key not in self._data:
            self._data[_key] = {}
        for _role, value in data.items():
            # preserve previously set values
            if _role not in self._data[_key]:
                self._data[_key][_role] = value
        return data.get(role)

    def add_line(self, plot_data: PlotDataItem, frequency: float) -> None:
        self.add_lines(plot_data, [frequency])

    def add_lines(
        self,
        plot_data: PlotDataItem,
        frequency_values: Iterable[float],
    ) -> None:
        frequency_values = [
            frequency
            for frequency in frequency_values
            if frequency not in self._frequencies
        ]
        if not frequency_values:
            return
        frequency_indices: NDArray[np.long] = self.frequency_indices(
            plot_data, frequency_values
        )
        if not frequency_indices.size:
            return
        new_data: NDArray[np.double]
        if plot_data.voltage_data.size == plot_data.gamma_data.size:
            new_data = np.column_stack(
                (
                    plot_data.frequency_data[frequency_indices],
                    plot_data.voltage_data[frequency_indices],
                    plot_data.gamma_data[frequency_indices],
                )
            )
        else:
            new_data = np.column_stack(
                (
                    plot_data.frequency_data[frequency_indices],
                    plot_data.voltage_data[frequency_indices],
                    np.ones_like(frequency_indices) * np.nan,
                )
            )
        self._frequencies = np.concatenate((self._frequencies, frequency_values))
        self._rows_loaded += frequency_indices.size
        self.extend_data(new_data)

    def remove_line(self, frequency: float) -> None:
        for row in np.argwhere(self._numeric_data[:, 0] == frequency).ravel():
            self.remove_row(row.item())
        self._frequencies = self._frequencies[self._frequencies != frequency]

    def set_lines(
        self,
        plot_data: PlotDataItem,
        *frequencies: NDArray[np.double],
    ) -> None:
        self._frequencies = np.concatenate(frequencies)
        # avoid duplicates
        self._frequencies = self._frequencies[
            np.unique(self._frequencies, return_index=True)[1]
        ]
        self.refresh(plot_data)

    def frequency_indices(
        self,
        plot_data: PlotDataItem,
        frequencies: Sequence[float] | NDArray[np.double] | None = None,
    ) -> NDArray[np.long]:
        if frequencies is None:
            frequencies = self._frequencies
        return np.searchsorted(plot_data.x_data, frequencies)

    def refresh(self, plot_data: PlotDataItem) -> None:
        frequency_indices: NDArray[np.int64] = self.frequency_indices(plot_data)
        if not frequency_indices.size:
            self.clear()
            return

        if plot_data.voltage_data.size == plot_data.gamma_data.size:
            self.set_data(
                np.column_stack(
                    (
                        plot_data.frequency_data[frequency_indices],
                        plot_data.voltage_data[frequency_indices],
                        plot_data.gamma_data[frequency_indices],
                    )
                )
            )
        else:
            self.set_data(
                np.column_stack(
                    (
                        plot_data.frequency_data[frequency_indices],
                        plot_data.voltage_data[frequency_indices],
                        np.ones_like(frequency_indices) * np.nan,
                    )
                )
            )

    @property
    def catalog_file_names(self) -> list[Path]:
        try:
            # noinspection PyPackageRequirements
            from pycatsearch.catalog import Catalog
        except ImportError:
            return []
        else:
            if isinstance(self._catalog, Catalog):
                return self._catalog.sources
        return []

    try:
        # noinspection PyPackageRequirements,PyUnusedImports
        from pycatsearch.catalog import Catalog
    except ImportError:

        @property
        def catalog(_self) -> None:
            return None
    else:

        @property
        def catalog(self) -> Catalog | None:
            if isinstance(self._catalog, FoundLinesModel.Catalog):
                return self._catalog
            return None

    @catalog.setter
    def catalog(self, catalog: object) -> None:
        try:
            # noinspection PyPackageRequirements
            from pycatsearch.catalog import Catalog
        except ImportError:
            return
        if isinstance(catalog, Catalog):
            self._catalog = catalog

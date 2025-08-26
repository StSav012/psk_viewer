from collections.abc import Iterable

import numpy as np
from numpy.typing import NDArray
from qtpy.QtCore import QCoreApplication, QObject

from .data_model import DataModel
from .plot_data_item import PlotDataItem
from .utils import HeaderWithUnit

__all__ = ["FoundLinesModel"]

_translate = QCoreApplication.translate


class FoundLinesModel(DataModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._frequencies: NDArray[np.float64] = np.empty(0)
        self._last_plot_data: PlotDataItem | None = None
        self._log10_gamma: bool = False
        self._fancy_table_numbers: bool = False

        self._header = [
            HeaderWithUnit(
                name=_translate("plot axes labels", "Frequency"),
                unit=_translate("unit", "MHz"),
            ),
            HeaderWithUnit(
                name=_translate("plot axes labels", "Voltage"),
                unit=_translate("unit", "mV"),
            ),
            HeaderWithUnit(
                name=_translate("plot axes labels", "Absorption"),
                unit=(
                    _translate("unit", "cm⁻¹")
                    if not self._log10_gamma
                    else _translate("unit", "log₁₀(cm⁻¹)")
                ),
            ),
        ]
        self.set_format(
            [
                DataModel.Format(precision=3, scale=1e-6),
                DataModel.Format(precision=4, scale=1e3),
                DataModel.Format(
                    precision=4, scale=np.nan, fancy=self._fancy_table_numbers
                ),
            ]
        )

    @property
    def log10_gamma(self) -> bool:
        return self._log10_gamma

    @log10_gamma.setter
    def log10_gamma(self, new_value: bool) -> None:
        if bool(new_value) == self._log10_gamma:
            return
        self._log10_gamma = bool(new_value)
        if len(self._header) == 3:
            self._header[2] = HeaderWithUnit(
                name=_translate("plot axes labels", "Absorption"),
                unit=(
                    _translate("unit", "cm⁻¹")
                    if not self._log10_gamma
                    else _translate("unit", "log₁₀(cm⁻¹)")
                ),
            )
        self.refresh()

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
                    precision=4, scale=np.nan, fancy=self._fancy_table_numbers
                ),
            ]
        )
        self.refresh()

    def add_line(self, plot_data: PlotDataItem, frequency: float) -> None:
        if frequency in self._frequencies:
            return
        self._frequencies = np.append(self._frequencies, frequency)
        self.refresh(plot_data)

    def add_lines(
        self, plot_data: PlotDataItem, frequency_values: Iterable[float]
    ) -> None:
        self._frequencies = np.concatenate((self._frequencies, frequency_values))
        # avoid duplicates
        self._frequencies = self._frequencies[
            np.unique(self._frequencies, return_index=True)[1]
        ]
        self.refresh(plot_data)

    def set_lines(
        self,
        plot_data: PlotDataItem,
        frequencies: NDArray[np.float64] | Iterable[NDArray[np.float64]],
    ) -> None:
        if isinstance(frequencies, np.ndarray):
            self._frequencies = frequencies.ravel()
        else:
            self._frequencies = np.concatenate(frequencies)
        # avoid duplicates
        self._frequencies = self._frequencies[
            np.unique(self._frequencies, return_index=True)[1]
        ]
        self.refresh(plot_data)

    def frequency_indices(
        self, plot_data: PlotDataItem, frequencies: NDArray[np.float64] | None = None
    ) -> np.int64 | NDArray[np.int64]:
        if frequencies is None:
            frequencies = self._frequencies
        return np.searchsorted(plot_data.x_data, frequencies)

    def refresh(self, plot_data: PlotDataItem | None = None) -> None:
        if plot_data is None:
            plot_data = self._last_plot_data
            if plot_data is None:  # still
                return
        else:
            self._last_plot_data = plot_data

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
                        (
                            np.log10(
                                plot_data.gamma_data[frequency_indices].astype(
                                    np.complex128
                                )
                            )
                            if self._log10_gamma
                            else plot_data.gamma_data[frequency_indices]
                        ),
                    )
                )
            )
        else:
            self.set_data(
                np.column_stack(
                    (
                        plot_data.frequency_data[frequency_indices],
                        plot_data.voltage_data[frequency_indices],
                    )
                )
            )

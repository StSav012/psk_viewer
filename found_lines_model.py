# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable

import numpy as np
from numpy.typing import NDArray
from qtpy.QtCore import QObject

from data_model import DataModel
from plot_data_item import PlotDataItem

__all__ = ('FoundLinesModel',)


class FoundLinesModel(DataModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._frequencies: NDArray[np.float64] = np.empty(0)

    def add_line(self, plot_data: PlotDataItem, frequency: float) -> None:
        if frequency in self._frequencies:
            return
        self._frequencies = np.append(self._frequencies, frequency)
        self.refresh(plot_data)

    def set_lines(self, plot_data: PlotDataItem,
                  frequencies: NDArray[np.float64] | Iterable[NDArray[np.float64]]) -> None:
        if isinstance(frequencies, np.ndarray):
            self._frequencies = frequencies.ravel()
        else:
            self._frequencies = np.concatenate(frequencies)
        self.refresh(plot_data)

    def frequency_indices(self, plot_data: PlotDataItem,
                          frequencies: NDArray[np.float64] | None = None) -> NDArray[np.float64]:
        if frequencies is None:
            frequencies = self._frequencies
        return np.searchsorted(plot_data.x_data, frequencies)

    def refresh(self, plot_data: PlotDataItem) -> None:
        frequency_indices: NDArray[np.float64] = self.frequency_indices(plot_data)
        if not frequency_indices.size:
            self.clear()
            return

        if plot_data.voltage_data.size == plot_data.gamma_data.size:
            self.set_data(np.column_stack((
                plot_data.frequency_data[frequency_indices],
                plot_data.voltage_data[frequency_indices],
                plot_data.gamma_data[frequency_indices],
            )))
        else:
            self.set_data(np.column_stack((
                plot_data.frequency_data[frequency_indices],
                plot_data.voltage_data[frequency_indices],
            )))

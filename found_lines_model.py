# -*- coding: utf-8 -*-
from typing import Optional, Union, Iterable

import numpy as np
from PySide6.QtCore import QObject

from data_model import DataModel
from plot_data_item import PlotDataItem

__all__ = ('FoundLinesModel',)


class FoundLinesModel(DataModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._frequencies: np.ndarray = np.empty(0)

    def add_line(self, plot_data: PlotDataItem, frequency: float) -> None:
        if frequency in self._frequencies:
            return
        self._frequencies = np.append(self._frequencies, frequency)
        self.refresh(plot_data)

    def set_lines(self, plot_data: PlotDataItem, frequencies: Union[np.ndarray, Iterable[np.ndarray]]) -> None:
        self._frequencies = frequencies.ravel() if isinstance(frequencies, np.ndarray) else np.concatenate(frequencies)
        self.refresh(plot_data)

    def frequency_indices(self, plot_data: PlotDataItem, frequencies: Optional[np.ndarray] = None) -> np.ndarray:
        if frequencies is None:
            frequencies = self._frequencies
        return np.searchsorted(plot_data.x_data, frequencies)

    def refresh(self, plot_data: PlotDataItem) -> None:
        frequency_indices: np.ndarray = self.frequency_indices(plot_data)
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

from typing import Final

import numpy as np
from numpy.typing import NDArray

__all__ = ["PlotDataItem"]


class PlotDataItem:
    GAMMA_DATA: Final[str] = "gamma_data"
    VOLTAGE_DATA: Final[str] = "voltage_data"

    _jump: float = np.nan
    _data_type: str = VOLTAGE_DATA

    def __init__(self) -> None:
        self._frequency_data: NDArray[np.float64] = np.empty(0)
        self._voltage_data: NDArray[np.float64] = np.empty(0)
        self._gamma_data: NDArray[np.float64] = np.empty(0)

    def __bool__(self) -> bool:
        return bool(
            self._frequency_data.size
            and (self._voltage_data.size or self._gamma_data.size)
        )

    def set_data(
        self,
        frequency_data: NDArray[np.float64],
        voltage_data: NDArray[np.float64],
        gamma_data: NDArray[np.float64] | None = None,
    ) -> None:
        if gamma_data is None:
            gamma_data = np.empty(0, dtype=np.float64)
        if frequency_data.size != voltage_data.size:
            raise ValueError(
                "Frequency and voltage data must be of the same size, but the sizes are "
                f"{frequency_data.size} and {voltage_data.size}"
            )
        if gamma_data.size != 0 and gamma_data.size != frequency_data.size:
            raise ValueError(
                "Frequency and absorption data must be of the same size, but the sizes are "
                f"{frequency_data.size} and {gamma_data.size}"
            )
        if frequency_data.ndim != 1:
            raise ValueError(
                f"Frequency data must be a 1D array, but it is {frequency_data.ndim}D"
            )
        if voltage_data.ndim != 1:
            raise ValueError(
                f"Voltage data must be a 1D array, but it is {voltage_data.ndim}D"
            )
        if gamma_data.size != 0 and gamma_data.ndim != 1:
            raise ValueError(
                f"Absorption data must be a 1D array, but it is {gamma_data.ndim}D"
            )
        sorting_indices: NDArray[np.float64] = np.argsort(frequency_data)
        self._frequency_data = frequency_data[sorting_indices]
        self._voltage_data = voltage_data[sorting_indices]
        if gamma_data.size:
            self._gamma_data = gamma_data[sorting_indices]

    def clear(self) -> None:
        self._frequency_data = np.empty(0)
        self._voltage_data = np.empty(0)
        self._gamma_data = np.empty(0)
        self.jump = np.nan

    @property
    def min_frequency(self) -> float | np.float64:
        if np.isnan(self._jump):
            return self._frequency_data[0]
        step: int = int(round(self._jump / self.frequency_step))
        if 2 * step >= self._frequency_data.size:
            return np.nan
        return self._frequency_data[step]

    @property
    def max_frequency(self) -> float | np.float64:
        if np.isnan(self._jump):
            return self._frequency_data[-1]
        step: int = int(round(self._jump / self.frequency_step))
        if 2 * step >= self._frequency_data.size:
            return np.nan
        return self._frequency_data[-step]

    @property
    def frequency_data(self) -> NDArray[np.float64]:
        if np.isnan(self._jump):
            return self._frequency_data
        step: int = int(round(self._jump / self.frequency_step))
        if step == 0:
            return self._frequency_data
        if 2 * step >= self._frequency_data.size:
            return np.empty(0)
        return self._frequency_data[step:-step]

    @property
    def voltage_data(self) -> NDArray[np.float64]:
        if np.isnan(self._jump):
            return self._voltage_data
        step: int = int(round(self._jump / self.frequency_step))
        if 2 * step >= self._voltage_data.size:
            return np.empty(0)
        if step == 0:
            return self._voltage_data
        return (
            self._voltage_data[step:-step]
            - (self._voltage_data[2 * step :] + self._voltage_data[: -2 * step]) / 2.0
        )

    @property
    def gamma_data(self) -> NDArray[np.float64]:
        if np.isnan(self._jump):
            return self._gamma_data
        step: int = int(round(self._jump / self.frequency_step))
        if 2 * step >= self._gamma_data.size:
            return np.empty(0)
        if step == 0:
            return self._gamma_data
        return (
            self._gamma_data[step:-step]
            - (self._gamma_data[2 * step :] + self._gamma_data[: -2 * step]) / 2.0
        )

    @property
    def frequency_span(self) -> float | np.float64:
        if not self._frequency_data.size:
            return 0.0
        if np.isnan(self._jump):
            return self._frequency_data[-1] - self._frequency_data[0]
        step: int = int(
            round(
                self._jump
                / (
                    (self._frequency_data[-1] - self._frequency_data[0])
                    / (self._frequency_data.size - 1)
                )
            )
        )
        if 2 * step >= self._frequency_data.size:
            return 0.0
        return self._frequency_data[-step - 1] - self._frequency_data[step]

    @property
    def frequency_step(self) -> float | np.float64:
        if not self._frequency_data.size:
            return np.nan
        return (self._frequency_data[-1] - self._frequency_data[0]) / (
            self._frequency_data.size - 1
        )

    @property
    def jump(self) -> float:
        return PlotDataItem._jump

    @jump.setter
    def jump(self, new_value: float) -> None:
        if new_value < 0.0:
            raise ValueError("Negative jump values are not allowed")
        PlotDataItem._jump = new_value

    @property
    def data_type(self) -> str:
        return PlotDataItem._data_type

    @data_type.setter
    def data_type(self, new_value: str) -> None:
        if new_value not in (PlotDataItem.VOLTAGE_DATA, PlotDataItem.GAMMA_DATA):
            raise ValueError(f"Unknown data type: {new_value}")
        PlotDataItem._data_type = new_value

    @property
    def x_data(self) -> NDArray[np.float64]:
        return self.frequency_data

    @property
    def y_data(self) -> NDArray[np.float64]:
        if self.data_type == PlotDataItem.VOLTAGE_DATA:
            return self.voltage_data
        if self.data_type == PlotDataItem.GAMMA_DATA:
            return self.gamma_data
        raise ValueError(f"Unknown data type: {self.data_type}")

from typing import Final

import numpy as np
from numpy.typing import NDArray

__all__ = ["PlotDataItem"]


class PlotDataItem:
    TIME_DATA: Final[str] = "time_data"
    FREQUENCY_DATA: Final[str] = "frequency_data"
    GAMMA_DATA: Final[str] = "gamma_data"
    VOLTAGE_DATA: Final[str] = "voltage_data"

    _jump: float = np.nan
    _x_data_type: str = FREQUENCY_DATA
    _y_data_type: str = VOLTAGE_DATA

    def __init__(self) -> None:
        self._time_data: NDArray[np.float64] = np.empty(0)
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
        time_data: NDArray[np.float64] | None = None,
    ) -> None:
        if gamma_data is None:
            gamma_data = np.empty(0, dtype=np.float64)
        if time_data is None:
            time_data = np.empty(0, dtype=np.float64)
        if (
            time_data.size != voltage_data.size
            and frequency_data.size != voltage_data.size
        ):
            raise ValueError(
                "Voltage data must be of the same size as time or frequency, but the sizes are "
                f"{time_data.size}, {frequency_data.size}, and {voltage_data.size}"
            )
        if (
            gamma_data.size != 0
            and gamma_data.size != time_data.size
            and gamma_data.size != frequency_data.size
        ):
            raise ValueError(
                "Absorption data must be of the same size as time or frequency, but the sizes are "
                f"{time_data.size}, {frequency_data.size}, and {gamma_data.size}"
            )
        if time_data.ndim != 1:
            raise ValueError(
                f"Time data must be a 1D array, but it is {time_data.ndim}D"
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
        self._frequency_data = frequency_data
        self._voltage_data = voltage_data
        self._gamma_data = gamma_data
        self._time_data = time_data

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
    def time_data(self) -> NDArray[np.float64]:
        return self._time_data

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
    def x_data_type(self) -> str:
        return PlotDataItem._x_data_type

    @x_data_type.setter
    def x_data_type(self, new_value: str) -> None:
        if new_value not in (PlotDataItem.TIME_DATA, PlotDataItem.FREQUENCY_DATA):
            raise ValueError(f"Unknown data type: {new_value}")
        PlotDataItem._x_data_type = new_value

    @property
    def y_data_type(self) -> str:
        return PlotDataItem._y_data_type

    @y_data_type.setter
    def y_data_type(self, new_value: str) -> None:
        if new_value not in (PlotDataItem.VOLTAGE_DATA, PlotDataItem.GAMMA_DATA):
            raise ValueError(f"Unknown data type: {new_value}")
        PlotDataItem._y_data_type = new_value

    @property
    def x_data(self) -> NDArray[np.float64]:
        if self.x_data_type == PlotDataItem.TIME_DATA:
            return self.time_data
        if self.x_data_type == PlotDataItem.FREQUENCY_DATA:
            return self.frequency_data
        raise ValueError(f"Unknown data type: {self.x_data_type}")

    @property
    def y_data(self) -> NDArray[np.float64]:
        if self.y_data_type == PlotDataItem.VOLTAGE_DATA:
            return self.voltage_data
        if self.y_data_type == PlotDataItem.GAMMA_DATA:
            return self.gamma_data
        raise ValueError(f"Unknown data type: {self.y_data_type}")

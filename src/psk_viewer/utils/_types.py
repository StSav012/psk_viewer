import enum
from contextlib import suppress
from pathlib import Path
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray
from qtpy.QtCore import QCoreApplication

_translate = QCoreApplication.translate

__all__ = [
    "DataMode",
    "FSData",
    "HeaderWithUnit",
    "PSKData",
    "SpectrometerData",
    "XValues",
]


class DataMode(enum.Enum):
    unknown = enum.auto()
    FS = enum.auto()
    PSK = enum.auto()
    PSK_WITH_JUMP = enum.auto()
    TIME_DOMAIN = enum.auto()


class FSData(NamedTuple):
    frequency: NDArray[np.double] = np.empty(0, dtype=np.double)
    voltage: NDArray[np.double] = np.empty(0, dtype=np.double)


class XValues(enum.Enum):
    unknown = enum.auto()
    time = enum.auto()
    frequency = enum.auto()


class PSKData(NamedTuple):
    frequency: NDArray[np.double] = np.empty(0, dtype=np.double)
    voltage: NDArray[np.double] = np.empty(0, dtype=np.double)
    absorption: NDArray[np.double] = np.empty(0, dtype=np.double)
    time: NDArray[np.double] = np.empty(0, dtype=np.double)
    jump: float = np.nan
    mode: XValues = XValues.unknown


class SpectrometerData(NamedTuple):
    filename: Path
    frequency: NDArray[np.double] = np.empty(0, dtype=np.double)
    voltage: NDArray[np.double] = np.empty(0, dtype=np.double)
    absorption: NDArray[np.double] = np.empty(0, dtype=np.double)
    time: NDArray[np.double] = np.empty(0, dtype=np.double)
    mode: DataMode = DataMode.unknown


class HeaderWithUnit:
    __slots__ = ("_fmt", "_name", "_str", "_unit")

    def __init__(self, name: str, unit: str, fmt: str = "") -> None:
        self._name: str = name
        self._unit: str = unit
        self._fmt: str = fmt or _translate("header with unit", "{name} ({unit})")
        self._str: str = self._fmt.format(name=self._name, unit=self._unit)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_value: str) -> None:
        with suppress(Exception):
            self._str = self._fmt.format(name=new_value, unit=self._unit)
            self._name = new_value

    @property
    def unit(self) -> str:
        return self._unit

    @unit.setter
    def unit(self, new_value: str) -> None:
        with suppress(Exception):
            self._str = self._fmt.format(name=self._name, unit=new_value)
            self._unit = new_value

    @property
    def format(self) -> str:
        return self._fmt

    @format.setter
    def format(self, new_value: str) -> None:
        with suppress(Exception):
            self._str = new_value.format(name=self._name, unit=self._unit)
            self._fmt = new_value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._str!r})"

    def __str__(self) -> str:
        return self._str

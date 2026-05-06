from pathlib import Path
from typing import cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

from ..utils import DataMode, SpectrometerData, load_data, superscript_number
from .frequency_domain_window import FrequencyDomainWindow
from .time_domain_window import TimeDomainWindow

__all__ = ["tick_strings", "TimeDomainWindow", "FrequencyDomainWindow", "Window"]

pg.ViewBox.suggestPadding = lambda *_: 0.0


def tick_strings(
    self: pg.AxisItem, values: list[float], scale: float, spacing: float
) -> list[str]:
    """Improve formatting of `AxisItem.tickStrings`."""
    if self.logMode:
        return cast(list[str], self.logTickStrings(values, scale, spacing))

    places: int = max(0, int(np.ceil(-np.log10(spacing * scale))))
    strings: list[str] = []
    v: float
    for v in values:
        vs: float = v * scale
        v_str: str
        if abs(vs) < 0.001 or abs(vs) >= 10000:
            v_str = f"{vs:g}".casefold()
            while "e-0" in v_str:
                v_str = v_str.replace("e-0", "e-")
            v_str = v_str.replace("+", "")
            if "e" in v_str:
                e_pos: int = v_str.find("e")
                man: str = v_str[:e_pos]
                exp: str = superscript_number(v_str[e_pos + 1 :])
                v_str = man + "×10" + exp
            v_str = v_str.replace("-", "−")
        else:
            v_str = f"{vs:0.{places}f}"
        strings.append(v_str)
    return strings


pg.AxisItem.tickStrings = tick_strings


class Window:
    def __new__(
        cls,
        file_path: Path | None = None,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> TimeDomainWindow | FrequencyDomainWindow | None:
        if file_path is None:
            return FrequencyDomainWindow(parent=parent, flags=flags)
        data: SpectrometerData | None = load_data(parent, file_path)
        if data is None:
            return None
        if data.mode == DataMode.TIME_DOMAIN:
            w = TimeDomainWindow(parent=parent, flags=flags)
            w.set_data(data)
            return w
        if data.mode in (DataMode.FS, DataMode.PSK, DataMode.PSK_WITH_JUMP):
            w = FrequencyDomainWindow(parent=parent, flags=flags)
            w.set_data(data)
            return w
        return None

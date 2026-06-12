from typing import cast

# noinspection PyPackageRequirements
import numpy as np
import pyqtgraph as pg  # type: ignore

# noinspection PyPackageRequirements
from numpy.typing import NDArray
from qtpy.QtCore import QCoreApplication, Qt, Signal, Slot
from qtpy.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...plot_data_item import PlotDataItem
from ...settings import Settings
from ...utils import DataMode, resource_path, the

__all__ = ["FindLinesBox"]

_translate = QCoreApplication.translate


class FindLinesBox(QDockWidget):
    lines_found: Signal = Signal(int, name="lines_found")
    line_removed: Signal = Signal(float, name="line_removed")
    found_lines_changed: Signal = Signal(np.ndarray, name="found_lines_changed")
    show_frequency_requested: Signal = Signal(float, name="show_frequency_requested")

    def __init__(
        self,
        settings: Settings,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)
        self.setObjectName("box_find_lines")

        self.settings: Settings = settings

        self.group_find_lines: QWidget = QWidget(self)
        self.v_layout_find_lines: QVBoxLayout = QVBoxLayout(self.group_find_lines)
        self.form_layout_find_lines: QFormLayout = QFormLayout()
        self.grid_layout_find_lines: QGridLayout = QGridLayout()
        self.spin_threshold: pg.SpinBox = pg.SpinBox(self.group_find_lines)
        self.button_find_lines: QPushButton = QPushButton(self.group_find_lines)
        self.button_clear_found_lines: QPushButton = QPushButton(self.group_find_lines)
        self.button_prev_found_line: QPushButton = QPushButton(self.group_find_lines)
        self.button_next_found_line: QPushButton = QPushButton(self.group_find_lines)

        self.f: NDArray[np.double] = np.empty(0)
        self.v: NDArray[np.double] = np.empty(0)
        self.g: NDArray[np.double] | None = None
        self.data_mode: DataMode = DataMode.unknown
        self.data_type: str = ""
        self.current_freq: float = np.nan
        self.found_lines_freq: NDArray[np.double] = np.empty(0)

        self.model_signal: NDArray[np.double]
        try:
            self.model_signal = np.fromiter(
                map(
                    float,
                    resource_path("averaged fs signal filtered.csv")
                    .read_text()
                    .split(),
                ),
                dtype=np.double,
            )
        except (OSError, BlockingIOError):
            self.model_signal = np.empty(0)
            self.hide()
            self.toggleViewAction().setDisabled(True)

    def setup_appearance(self) -> None:
        self.setWidget(self.group_find_lines)

        self.form_layout_find_lines.addRow(
            self.tr("Search threshold:"), self.spin_threshold
        )

        with the(self.grid_layout_find_lines) as layout:
            layout.addWidget(self.button_find_lines, 0, 0, 1, 2)
            layout.addWidget(self.button_clear_found_lines, 1, 0, 1, 2)
            layout.addWidget(self.button_prev_found_line, 2, 0)
            layout.addWidget(self.button_next_found_line, 2, 1)

        with the(self.v_layout_find_lines) as layout:
            layout.addLayout(self.form_layout_find_lines)
            layout.addLayout(self.grid_layout_find_lines)

        self.button_find_lines.setEnabled(False)
        self.button_clear_found_lines.setEnabled(False)
        self.button_next_found_line.setEnabled(False)
        self.button_prev_found_line.setEnabled(False)

        self.spin_threshold.setOpts(compactHeight=False)
        self.spin_threshold.setMinimum(1.0)
        self.spin_threshold.setMaximum(10000.0)

        self.adjustSize()

    def setup_translation(self) -> None:
        self.setWindowTitle(self.tr("Find Lines Automatically"))

        with the(self.form_layout_find_lines.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_threshold)).setText(
                self.tr("Search threshold:")
            )

        self.group_find_lines.setToolTip(self.tr("Try to detect lines automatically"))
        self.button_find_lines.setText(self.tr("Find Lines Automatically"))
        self.button_clear_found_lines.setText(
            self.tr("Clear Automatically Found Lines")
        )
        self.button_prev_found_line.setText(self.tr("Previous Line"))
        self.button_next_found_line.setText(self.tr("Next Line"))

    def setup_ui_actions(self) -> None:
        self.spin_threshold.valueChanged.connect(self.on_spin_threshold_changed)
        self.button_clear_found_lines.clicked.connect(self.on_clear_found_lines_clicked)
        self.button_find_lines.clicked.connect(self.on_button_find_lines_clicked)
        self.button_prev_found_line.clicked.connect(self.on_prev_found_line_clicked)
        self.button_next_found_line.clicked.connect(self.on_next_found_line_clicked)

    def load_config(self) -> None:
        with self.settings.section("lineSearch"):
            self.spin_threshold.setValue(self.settings.value("threshold", 12.0, float))

    @Slot(float)
    def on_spin_threshold_changed(self, threshold: float) -> None:
        with self.settings.section("lineSearch"):
            self.settings.setValue("threshold", threshold)

    @Slot()
    def on_button_find_lines_clicked(self) -> None:
        self.find_lines()
        self.found_lines_changed.emit(self.found_lines_freq)

    @Slot()
    def on_clear_found_lines_clicked(self) -> None:
        self.clear_found_lines()

    def set_spectrum(
        self,
        f: NDArray[np.double],
        v: NDArray[np.double],
        g: NDArray[np.double] | None,
        data_mode: DataMode,
    ) -> None:
        self.f = f
        self.v = v
        self.g = g
        self.data_mode = data_mode
        self.button_find_lines.setEnabled(
            bool(self.data_type) and data_mode != DataMode.unknown
        )

    def set_data_type(self, data_type: str) -> None:
        self.data_type = data_type
        self.button_find_lines.setEnabled(
            bool(data_type) and self.data_mode != DataMode.unknown
        )

    def set_found_lines(self, frequencies: NDArray[np.double]) -> None:
        if self.found_lines_freq.shape != frequencies.shape or not np.all(
            self.found_lines_freq == frequencies
        ):
            self.found_lines_freq = frequencies
            self.found_lines_changed.emit(self.found_lines_freq)

    def clear_found_lines(self) -> None:
        self.found_lines_freq = np.empty(0)
        self.button_clear_found_lines.setEnabled(False)
        self.button_next_found_line.setEnabled(False)
        self.button_prev_found_line.setEnabled(False)
        self.found_lines_changed.emit(self.found_lines_freq)

    def remove_found_line(self, f: float) -> None:
        remaining_frequencies: NDArray[np.double] = self.found_lines_freq[
            self.found_lines_freq != f
        ]
        if self.found_lines_freq.shape != remaining_frequencies.shape or not np.all(
            self.found_lines_freq == remaining_frequencies
        ):
            self.found_lines_freq = remaining_frequencies
            self.line_removed.emit(f)

    def find_lines(self) -> NDArray[np.long]:
        from ...detection import correlation, peaks_positions

        found_lines_pos: NDArray[np.long] = np.empty(0, dtype=np.long).astype(np.long)

        if self.data_mode == DataMode.unknown or self.model_signal.size < 2:
            return found_lines_pos

        if self.data_type == PlotDataItem.VOLTAGE_DATA:
            y = self.v
        elif self.data_type == PlotDataItem.GAMMA_DATA and (_y := self.g) is not None:
            y = _y
        else:
            return found_lines_pos
        x = self.f

        if x.size < 2 or y.size < 2:
            return found_lines_pos

        threshold: float = self.spin_threshold.value()

        if self.data_mode == DataMode.FS:
            # re-scale the signal to the actual frequency mesh
            # noinspection PyTypeChecker
            x_model: NDArray[np.float64] = (
                np.arange(self.model_signal.size, dtype=np.double) * 0.1
            )
            # noinspection PyTypeChecker
            x_model_new: NDArray[np.float64] = np.arange(
                x_model[0], x_model[-1], x[1] - x[0]
            )
            y_model_new: NDArray[np.float64] = np.interp(
                x_model_new, x_model, self.model_signal
            )
            found_lines_pos = peaks_positions(
                x, correlation(y_model_new, x, y), threshold=1.0 / threshold
            )
        elif self.data_mode in (DataMode.PSK, DataMode.PSK_WITH_JUMP):
            found_lines_pos = peaks_positions(x, y, threshold=1.0 / threshold)

        with the(bool(found_lines_pos.size)) as anything:
            self.button_clear_found_lines.setEnabled(anything)
            self.button_next_found_line.setEnabled(anything)
            self.button_prev_found_line.setEnabled(anything)

        self.found_lines_freq = x[found_lines_pos]

        self.lines_found.emit(found_lines_pos.size)

        return found_lines_pos

    @Slot()
    def on_prev_found_line_clicked(self) -> None:
        with the(self.found_lines_freq) as line_data:
            if not line_data.size:
                return
            i: int = (
                np.searchsorted(line_data, self.current_freq, side="right").item() - 2
            )
            if 0 <= i < line_data.size and line_data[i] != self.current_freq:
                f = line_data[i]
                self.show_frequency_requested.emit(f)

    @Slot()
    def on_next_found_line_clicked(self) -> None:
        with the(self.found_lines_freq) as line_data:
            if not line_data.size:
                return
            i: int = (
                np.searchsorted(line_data, self.current_freq, side="left").item() + 1
            )
            if 0 <= i < line_data.size and line_data[i] != self.current_freq:
                f = line_data[i]
                self.show_frequency_requested.emit(f)

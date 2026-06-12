from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast

import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QCoreApplication, QObject, Qt, Signal, Slot
from qtpy.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...plot_data_item import PlotDataItem
from ...settings import Settings
from ...utils import the

__all__ = ["VoltageBox"]

_translate = QCoreApplication.translate


class VoltageBox(QDockWidget):
    changed: Signal = Signal(float, float, name="changed")
    dataModeChanged: Signal = Signal(str, name="dataModeChanged")

    def __init__(
        self,
        settings: Settings,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)
        self.setObjectName("box_voltage")

        self.settings: Settings = settings

        self.group_voltage: QWidget = QWidget(self)
        self.v_layout_voltage: QVBoxLayout = QVBoxLayout(self.group_voltage)
        self.form_layout_voltage: QFormLayout = QFormLayout()
        self.h_layout_voltage: QHBoxLayout = QHBoxLayout()

        self.spin_min: pg.SpinBox = pg.SpinBox(self.group_voltage)
        self.spin_max: pg.SpinBox = pg.SpinBox(self.group_voltage)

        self.switch_data_action: QPushButton = QPushButton(self.group_voltage)

        # Zoom Y
        self.button_zoom_y_out_coarse: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_out_fine: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_in_fine: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_in_coarse: QPushButton = QPushButton(self.group_voltage)

    def setup_appearance(self) -> None:
        self.setWidget(self.group_voltage)

        with the(self.form_layout_voltage) as layout:
            layout.addRow(self.tr("Minimum:"), self.spin_min)
            layout.addRow(self.tr("Maximum:"), self.spin_max)

        with the(self.h_layout_voltage) as layout:
            layout.addWidget(self.button_zoom_y_out_coarse)
            layout.addWidget(self.button_zoom_y_out_fine)
            layout.addWidget(self.button_zoom_y_in_fine)
            layout.addWidget(self.button_zoom_y_in_coarse)

        with the(self.switch_data_action) as button:
            button.setEnabled(False)
            button.setCheckable(True)
            button.setShortcut("Ctrl+`")

        with the(self.v_layout_voltage) as layout:
            layout.addWidget(self.switch_data_action)
            layout.addLayout(self.form_layout_voltage)
            layout.addLayout(self.h_layout_voltage)

        with the(
            dict(
                siPrefix=True,
                decimals=3,
                dec=True,
                compactHeight=False,
                format="{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
            )
        ) as opts:
            self.spin_min.setOpts(**opts)
            self.spin_max.setOpts(**opts)

        self.adjustSize()

    def setup_translation(self) -> None:
        self.setWindowTitle(self.tr("Vertical Axis"))

        with the(self.form_layout_voltage.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_min)).setText(self.tr("Minimum:"))
            cast(QLabel, labelForField(self.spin_max)).setText(self.tr("Maximum:"))

        with the(self.switch_data_action) as button:
            button.setText(self.tr("Show Absorption"))
            button.setToolTip(self.tr("Switch Y data between absorption and voltage"))

        self.button_zoom_y_out_coarse.setText(self.tr("−50%"))
        self.button_zoom_y_out_fine.setText(self.tr("−10%"))
        self.button_zoom_y_in_fine.setText(self.tr("+10%"))
        self.button_zoom_y_in_coarse.setText(self.tr("+50%"))

        with the(_translate("unit", "V")) as unit_y:
            self.spin_min.setSuffix(unit_y)
            self.spin_max.setSuffix(unit_y)

    def setup_ui_actions(self) -> None:
        self.spin_min.valueChanged.connect(self.on_spin_min_changed)
        self.spin_max.valueChanged.connect(self.on_spin_max_changed)
        self.button_zoom_y_out_coarse.clicked.connect(
            self.on_button_zoom_out_coarse_clicked
        )
        self.button_zoom_y_out_fine.clicked.connect(
            self.on_button_zoom_out_fine_clicked
        )
        self.button_zoom_y_in_fine.clicked.connect(self.on_button_zoom_in_fine_clicked)
        self.button_zoom_y_in_coarse.clicked.connect(
            self.on_button_zoom_in_coarse_clicked
        )

        self.switch_data_action.toggled.connect(self.on_switch_data_action_toggled)

    def load_config(self) -> None:
        with self.settings.section("display"):
            self.switch_data_action.setChecked(
                self.settings.value("unit", PlotDataItem.VOLTAGE_DATA, str)
                == PlotDataItem.GAMMA_DATA
            )

    @contextmanager
    def block_children(self) -> Iterator[None]:
        def _block(parent: QObject, block: bool) -> None:
            for child in parent.children():
                child.blockSignals(block)
                _block(child, block)

        try:
            _block(self, True)
            yield None
        finally:
            _block(self, False)

    @property
    def range(self) -> tuple[float, float]:
        return self.spin_min.value(), self.spin_max.value()

    @range.setter
    def range(self, r: tuple[float, float]) -> None:
        self.set_range(*r)

    def set_range(self, min_y: float, max_y: float) -> None:
        with self.block_children():
            self.spin_min.setValue(min_y)
            self.spin_max.setValue(max_y)
            self.spin_min.setMaximum(max_y)
            self.spin_max.setMinimum(min_y)

    def switch_range(self, min_y: float, max_y: float) -> None:
        """Extend the range if needed."""
        with self.block_children():
            self.spin_min.setMaximum(max(max_y, self.spin_min.value()))
            self.spin_max.setMinimum(min(min_y, self.spin_max.value()))
            self.spin_min.setValue(min_y)
            self.spin_max.setValue(max_y)
        self.changed.emit(min_y, max_y)

    @Slot(float)
    def on_spin_min_changed(self, min_y: float) -> None:
        max_y = self.spin_max.value()
        with self.block_children():
            self.spin_min.setValue(min_y)
            self.spin_max.setMinimum(min_y)
        self.changed.emit(min_y, max_y)

    @Slot(float)
    def on_spin_max_changed(self, max_y: float) -> None:
        min_y = self.spin_min.value()
        with self.block_children():
            self.spin_max.setValue(max_y)
            self.spin_min.setMaximum(max_y)
        self.changed.emit(min_y, max_y)

    @Slot()
    def on_button_zoom_out_coarse_clicked(self) -> None:
        self.zoom(1.0 / 0.5)

    @Slot()
    def on_button_zoom_out_fine_clicked(self) -> None:
        self.zoom(1.0 / 0.9)

    @Slot()
    def on_button_zoom_in_fine_clicked(self) -> None:
        self.zoom(0.9)

    @Slot()
    def on_button_zoom_in_coarse_clicked(self) -> None:
        self.zoom(0.5)

    def zoom(self, factor: float) -> None:
        y_span: float = (self.spin_min.value() - self.spin_max.value()) * factor
        y_center: float = (self.spin_min.value() + self.spin_max.value()) / 2.0
        min_y: float = y_center - 0.5 * y_span
        max_y: float = y_center + 0.5 * y_span
        self.set_range(min_y, max_y)
        self.changed.emit(min_y, max_y)

    @Slot(bool)
    def on_switch_data_action_toggled(self, display_gamma: bool) -> None:
        mode: str = (
            PlotDataItem.GAMMA_DATA if display_gamma else PlotDataItem.VOLTAGE_DATA
        )
        with self.settings.section("display"):
            self.settings.setValue("unit", mode)
        if display_gamma:
            self.setWindowTitle(self.tr("Absorption"))
            opts = dict(
                suffix=_translate("unit", "cm⁻¹"),
                siPrefix=False,
                format="{value:.{decimals}e}{suffixGap}{suffix}",
            )
        else:
            self.setWindowTitle(self.tr("Voltage"))
            opts = dict(
                suffix=_translate("unit", "V"),
                siPrefix=True,
                format="{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
            )
        self.spin_min.setOpts(**opts)
        self.spin_max.setOpts(**opts)
        self.dataModeChanged.emit(mode)

    @property
    def show_gamma(self) -> bool:
        return self.switch_data_action.isChecked()

    @show_gamma.setter
    def show_gamma(self, show: bool) -> None:
        self.switch_data_action.setChecked(show)

    @property
    def can_show_gamma(self) -> bool:
        return self.switch_data_action.isEnabled()

    @can_show_gamma.setter
    def can_show_gamma(self, can: bool) -> None:
        self.switch_data_action.setEnabled(can)
        if not can and self.show_gamma:
            self.show_gamma = False

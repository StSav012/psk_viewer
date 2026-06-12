from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast

import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QCoreApplication, QObject, Qt, Signal, Slot
from qtpy.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...settings import Settings
from ...utils import the

__all__ = ["TimeBox"]

_translate = QCoreApplication.translate


class TimeBox(QDockWidget):
    changed: Signal = Signal(float, float, name="changed")

    def __init__(
        self,
        settings: Settings,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)
        self.setObjectName("box_time")

        self.settings: Settings = settings

        self.widget: QWidget = QWidget(self)
        self.v_layout: QVBoxLayout = QVBoxLayout(self.widget)
        self.form_layout: QFormLayout = QFormLayout()
        self.grid_layout: QGridLayout = QGridLayout()

        self.spin_min: pg.SpinBox = pg.SpinBox(self.widget)
        self.spin_max: pg.SpinBox = pg.SpinBox(self.widget)
        self.spin_center: pg.SpinBox = pg.SpinBox(self.widget)
        self.spin_span: pg.SpinBox = pg.SpinBox(self.widget)

        # Zoom X
        self.button_zoom_out_coarse: QPushButton = QPushButton(self.widget)
        self.button_zoom_out_fine: QPushButton = QPushButton(self.widget)
        self.button_zoom_in_fine: QPushButton = QPushButton(self.widget)
        self.button_zoom_in_coarse: QPushButton = QPushButton(self.widget)

    def setup_appearance(self) -> None:
        self.setWidget(self.widget)

        with the(self.form_layout) as layout:
            layout.addRow(self.tr("Minimum:"), self.spin_min)
            layout.addRow(self.tr("Maximum:"), self.spin_max)
            layout.addRow(self.tr("Center:"), self.spin_center)
            layout.addRow(self.tr("Span:"), self.spin_span)

        with the(self.grid_layout) as layout:
            layout.addWidget(self.button_zoom_out_coarse, 0, 0)
            layout.addWidget(self.button_zoom_out_fine, 0, 1)
            layout.addWidget(self.button_zoom_in_fine, 0, 2)
            layout.addWidget(self.button_zoom_in_coarse, 0, 3)

        with the(self.v_layout) as layout:
            layout.addLayout(self.form_layout)
            layout.addLayout(self.grid_layout)

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
            self.spin_center.setOpts(**opts)
            self.spin_span.setOpts(**opts)
        self.spin_span.setMinimum(1e-8)

        self.adjustSize()

    def setup_translation(self) -> None:
        self.setWindowTitle(self.tr("Time"))

        with the(self.form_layout.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_min)).setText(self.tr("Minimum:"))
            cast(QLabel, labelForField(self.spin_max)).setText(self.tr("Maximum:"))
            cast(QLabel, labelForField(self.spin_center)).setText(self.tr("Center:"))
            cast(QLabel, labelForField(self.spin_span)).setText(self.tr("Span:"))

        self.button_zoom_out_coarse.setText(self.tr("−50%"))
        self.button_zoom_out_fine.setText(self.tr("−10%"))
        self.button_zoom_in_fine.setText(self.tr("+10%"))
        self.button_zoom_in_coarse.setText(self.tr("+50%"))

        with the(_translate("unit", "s")) as unit_x:
            self.spin_min.setSuffix(unit_x)
            self.spin_max.setSuffix(unit_x)
            self.spin_center.setSuffix(unit_x)
            self.spin_span.setSuffix(unit_x)

    def setup_ui_actions(self) -> None:
        self.spin_min.valueChanged.connect(self.on_spin_min_changed)
        self.spin_max.valueChanged.connect(self.on_spin_max_changed)
        self.spin_center.valueChanged.connect(self.on_spin_center_changed)
        self.spin_span.valueChanged.connect(self.on_spin_span_changed)
        self.button_zoom_out_coarse.clicked.connect(
            self.on_button_zoom_out_coarse_clicked
        )
        self.button_zoom_out_fine.clicked.connect(self.on_button_zoom_out_fine_clicked)
        self.button_zoom_in_fine.clicked.connect(self.on_button_zoom_in_fine_clicked)
        self.button_zoom_in_coarse.clicked.connect(
            self.on_button_zoom_in_coarse_clicked
        )

    def load_config(self) -> None:
        pass

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

    @property
    def center(self) -> float:
        return self.spin_center.value()

    @center.setter
    def center(self, center: float) -> None:
        self.spin_center.setValue(center)

    def set_range(self, min_time: float, max_time: float) -> None:
        with self.block_children():
            self.spin_min.setValue(min_time)
            self.spin_max.setValue(max_time)
            self.spin_span.setValue(max_time - min_time)
            self.spin_center.setValue(0.5 * (max_time + min_time))
            self.spin_min.setMaximum(max_time)
            self.spin_max.setMinimum(min_time)

    def switch_range(self, min_time: float, max_time: float) -> None:
        """Extend the range if needed."""
        with self.block_children():
            self.spin_min.setMaximum(max(max_time, self.spin_min.value()))
            self.spin_max.setMinimum(min(min_time, self.spin_max.value()))
            self.spin_min.setValue(min_time)
            self.spin_max.setValue(max_time)
            self.spin_span.setValue(max_time - min_time)
            self.spin_center.setValue(0.5 * (max_time + min_time))
        self.changed.emit(min_time, max_time)

    @Slot(float)
    def on_spin_min_changed(self, min_time: float) -> None:
        max_time: float = self.spin_max.value()
        with self.block_children():
            self.spin_min.setValue(min_time)
            self.spin_span.setValue(max_time - min_time)
            self.spin_center.setValue(0.5 * (max_time + min_time))
            self.spin_max.setMinimum(min_time)
        self.changed.emit(min_time, max_time)

    @Slot(float)
    def on_spin_max_changed(self, max_time: float) -> None:
        min_time: float = self.spin_min.value()
        with self.block_children():
            self.spin_max.setValue(max_time)
            self.spin_span.setValue(max_time - min_time)
            self.spin_center.setValue(0.5 * (max_time + min_time))
            self.spin_min.setMaximum(max_time)
        self.changed.emit(min_time, max_time)

    @Slot(float)
    def on_spin_center_changed(self, center: float) -> None:
        span: float = self.spin_span.value()
        min_time: float = center - span / 2.0
        max_time: float = center + span / 2.0
        self.set_range(min_time, max_time)
        self.changed.emit(min_time, max_time)

    @Slot(float)
    def on_spin_span_changed(self, span: float) -> None:
        center: float = self.spin_center.value()
        min_time: float = center - span / 2.0
        max_time: float = center + span / 2.0
        self.set_range(min_time, max_time)
        self.changed.emit(min_time, max_time)

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
        time_span: float = self.spin_span.value() * factor
        time_center: float = self.spin_center.value()
        min_time: float = time_center - 0.5 * time_span
        max_time: float = time_center + 0.5 * time_span
        self.set_range(min_time, max_time)
        self.changed.emit(min_time, max_time)

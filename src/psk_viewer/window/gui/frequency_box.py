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

__all__ = ["FrequencyBox"]

_translate = QCoreApplication.translate


class FrequencyBox(QDockWidget):
    changed: Signal = Signal(float, float, name="changed")

    def __init__(
        self,
        settings: Settings,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)
        self.setObjectName("box_frequency")

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

        # Move X
        self.button_move_left_coarse: QPushButton = QPushButton(self.widget)
        self.button_move_left_fine: QPushButton = QPushButton(self.widget)
        self.button_move_right_fine: QPushButton = QPushButton(self.widget)
        self.button_move_right_coarse: QPushButton = QPushButton(self.widget)

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

            layout.addWidget(self.button_move_left_coarse, 1, 0)
            layout.addWidget(self.button_move_left_fine, 1, 1)
            layout.addWidget(self.button_move_right_fine, 1, 2)
            layout.addWidget(self.button_move_right_coarse, 1, 3)

        with the(self.v_layout) as layout:
            layout.addLayout(self.form_layout)
            layout.addLayout(self.grid_layout)

        with the(
            dict(
                siPrefix=True,
                decimals=6,
                dec=True,
                compactHeight=False,
                format="{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
                scaleAtZero=1e6,
            )
        ) as opts:
            self.spin_min.setOpts(**opts)
            self.spin_max.setOpts(**opts)
            self.spin_center.setOpts(**opts)
            self.spin_span.setOpts(**opts)
        self.spin_span.setMinimum(0.01)

        self.adjustSize()

    def setup_translation(self) -> None:
        self.setWindowTitle(self.tr("Frequency"))

        with the(self.form_layout.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_min)).setText(self.tr("Minimum:"))
            cast(QLabel, labelForField(self.spin_max)).setText(self.tr("Maximum:"))
            cast(QLabel, labelForField(self.spin_center)).setText(self.tr("Center:"))
            cast(QLabel, labelForField(self.spin_span)).setText(self.tr("Span:"))

        self.button_zoom_out_coarse.setText(self.tr("−50%"))
        self.button_zoom_out_fine.setText(self.tr("−10%"))
        self.button_zoom_in_fine.setText(self.tr("+10%"))
        self.button_zoom_in_coarse.setText(self.tr("+50%"))

        with the(_translate("unit", "Hz")) as unit_x:
            self.button_move_left_coarse.setText("−" + pg.siFormat(5e8, suffix=unit_x))
            self.button_move_left_fine.setText("−" + pg.siFormat(5e7, suffix=unit_x))
            self.button_move_right_fine.setText("+" + pg.siFormat(5e7, suffix=unit_x))
            self.button_move_right_coarse.setText("+" + pg.siFormat(5e8, suffix=unit_x))

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
        self.button_move_left_coarse.clicked.connect(
            self.on_button_move_left_coarse_clicked
        )
        self.button_move_left_fine.clicked.connect(
            self.on_button_move_left_fine_clicked
        )
        self.button_move_right_fine.clicked.connect(
            self.on_button_move_right_fine_clicked
        )
        self.button_move_right_coarse.clicked.connect(
            self.on_button_move_right_coarse_clicked
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

    def set_range(self, min_freq: float, max_freq: float) -> None:
        with self.block_children():
            self.spin_min.setValue(min_freq)
            self.spin_max.setValue(max_freq)
            self.spin_span.setValue(max_freq - min_freq)
            self.spin_center.setValue(0.5 * (max_freq + min_freq))
            self.spin_min.setMaximum(max_freq)
            self.spin_max.setMinimum(min_freq)

    def switch_range(self, min_freq: float, max_freq: float) -> None:
        """Extend the range if needed."""
        with self.block_children():
            self.spin_min.setMaximum(max(max_freq, self.spin_min.value()))
            self.spin_max.setMinimum(min(min_freq, self.spin_max.value()))
            self.spin_min.setValue(min_freq)
            self.spin_max.setValue(max_freq)
            self.spin_span.setValue(max_freq - min_freq)
            self.spin_center.setValue(0.5 * (max_freq + min_freq))
        self.changed.emit(min_freq, max_freq)

    @Slot(float)
    def on_spin_min_changed(self, min_freq: float) -> None:
        max_freq: float = self.spin_max.value()
        with self.block_children():
            self.spin_min.setValue(min_freq)
            self.spin_span.setValue(max_freq - min_freq)
            self.spin_center.setValue(0.5 * (max_freq + min_freq))
            self.spin_max.setMinimum(min_freq)
        self.changed.emit(min_freq, max_freq)

    @Slot(float)
    def on_spin_max_changed(self, max_freq: float) -> None:
        min_freq: float = self.spin_min.value()
        with self.block_children():
            self.spin_max.setValue(max_freq)
            self.spin_span.setValue(max_freq - min_freq)
            self.spin_center.setValue(0.5 * (max_freq + min_freq))
            self.spin_min.setMaximum(max_freq)
        self.changed.emit(min_freq, max_freq)

    @Slot(float)
    def on_spin_center_changed(self, center: float) -> None:
        span: float = self.spin_span.value()
        min_freq: float = center - span / 2.0
        max_freq: float = center + span / 2.0
        self.set_range(min_freq, max_freq)
        self.changed.emit(min_freq, max_freq)

    @Slot(float)
    def on_spin_span_changed(self, span: float) -> None:
        center: float = self.spin_center.value()
        min_freq: float = center - span / 2.0
        max_freq: float = center + span / 2.0
        self.set_range(min_freq, max_freq)
        self.changed.emit(min_freq, max_freq)

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
        freq_span: float = self.spin_span.value() * factor
        freq_center: float = self.spin_center.value()
        min_freq: float = freq_center - 0.5 * freq_span
        max_freq: float = freq_center + 0.5 * freq_span
        self.set_range(min_freq, max_freq)
        self.changed.emit(min_freq, max_freq)

    @Slot()
    def on_button_move_left_coarse_clicked(self) -> None:
        self.shift(-500.0e6)

    @Slot()
    def on_button_move_left_fine_clicked(self) -> None:
        self.shift(-50.0e6)

    @Slot()
    def on_button_move_right_fine_clicked(self) -> None:
        self.shift(50.0e6)

    @Slot()
    def on_button_move_right_coarse_clicked(self) -> None:
        self.shift(500.0e6)

    def shift(self, shift: float) -> None:
        freq_span: float = self.spin_span.value()
        freq_center: float = self.spin_center.value() + shift
        min_freq: float = freq_center - 0.5 * freq_span
        max_freq: float = freq_center + 0.5 * freq_span
        self.set_range(min_freq, max_freq)
        self.changed.emit(min_freq, max_freq)

from typing import cast

import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QFormLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...widgets.toolbar import TimeDomainToolbar
from . import GUI

__all__ = ["TimeDomainGUI"]

_translate = QCoreApplication.translate


class TimeDomainGUI(GUI):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        # Frequency box
        self.box_time: QDockWidget = QDockWidget(self.central_widget)
        self.box_time.setObjectName("box_time")
        self.group_time: QWidget = QWidget(self.box_time)
        self.v_layout_frequency: QVBoxLayout = QVBoxLayout(self.group_time)
        self.form_layout_frequency: QFormLayout = QFormLayout()
        self.grid_layout_frequency: QGridLayout = QGridLayout()

        self.spin_x_min: pg.SpinBox = pg.SpinBox(self.group_time)
        self.spin_x_max: pg.SpinBox = pg.SpinBox(self.group_time)
        self.spin_x_center: pg.SpinBox = pg.SpinBox(self.group_time)
        self.spin_x_span: pg.SpinBox = pg.SpinBox(self.group_time)
        self.spin_x_span.setMinimum(1e-8)

        self.check_x_range_persists: QCheckBox = QCheckBox(self.group_time)

        # Zoom X
        self.button_zoom_x_out_coarse: QPushButton = QPushButton(self.group_time)
        self.button_zoom_x_out_fine: QPushButton = QPushButton(self.group_time)
        self.button_zoom_x_in_fine: QPushButton = QPushButton(self.group_time)
        self.button_zoom_x_in_coarse: QPushButton = QPushButton(self.group_time)

        # Voltage box
        self.box_voltage: QDockWidget = QDockWidget(self.central_widget)
        self.box_voltage.setObjectName("box_voltage")
        self.group_voltage: QWidget = QWidget(self.box_voltage)
        self.v_layout_voltage: QVBoxLayout = QVBoxLayout(self.group_voltage)
        self.form_layout_voltage: QFormLayout = QFormLayout()
        self.grid_layout_voltage: QGridLayout = QGridLayout()

        self.spin_y_min: pg.SpinBox = pg.SpinBox(self.group_voltage)
        self.spin_y_max: pg.SpinBox = pg.SpinBox(self.group_voltage)

        self.check_y_range_persists: QCheckBox = QCheckBox(self.group_voltage)

        self.switch_data_action: QPushButton = QPushButton(self.group_voltage)

        # Zoom Y
        self.button_zoom_y_out_coarse: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_out_fine: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_in_fine: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_in_coarse: QPushButton = QPushButton(self.group_voltage)

        self.toolbar: TimeDomainToolbar = TimeDomainToolbar(self)

        self._setup_appearance()

    def _setup_appearance(self) -> None:
        super()._setup_appearance()

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.form_layout_frequency.addRow(self.tr("Minimum:"), self.spin_x_min)
        self.form_layout_frequency.addRow(self.tr("Maximum:"), self.spin_x_max)
        self.form_layout_frequency.addRow(self.tr("Center:"), self.spin_x_center)
        self.form_layout_frequency.addRow(self.tr("Span:"), self.spin_x_span)

        self.grid_layout_frequency.addWidget(self.check_x_range_persists, 0, 0, 1, 4)
        self.grid_layout_frequency.addWidget(self.button_zoom_x_out_coarse, 1, 0)
        self.grid_layout_frequency.addWidget(self.button_zoom_x_out_fine, 1, 1)
        self.grid_layout_frequency.addWidget(self.button_zoom_x_in_fine, 1, 2)
        self.grid_layout_frequency.addWidget(self.button_zoom_x_in_coarse, 1, 3)

        self.v_layout_frequency.addLayout(self.form_layout_frequency)
        self.v_layout_frequency.addLayout(self.grid_layout_frequency)

        self.form_layout_voltage.addRow(self.tr("Minimum:"), self.spin_y_min)
        self.form_layout_voltage.addRow(self.tr("Maximum:"), self.spin_y_max)

        self.grid_layout_voltage.addWidget(self.check_y_range_persists, 0, 0, 1, 4)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_coarse, 1, 0)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_fine, 1, 1)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_fine, 1, 2)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_coarse, 1, 3)

        self.v_layout_voltage.addWidget(self.switch_data_action)
        self.switch_data_action.setEnabled(False)
        self.switch_data_action.setCheckable(True)
        self.switch_data_action.setShortcut("Ctrl+`")

        self.v_layout_voltage.addLayout(self.form_layout_voltage)
        self.v_layout_voltage.addLayout(self.grid_layout_voltage)

        # TODO: adjust size when undocked
        self.box_time.setWidget(self.group_time)
        self.box_time.setFeatures(
            self.box_time.features() & ~QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_time)

        self.box_voltage.setWidget(self.group_voltage)
        self.box_voltage.setFeatures(
            self.box_voltage.features()
            & ~QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_voltage)

        opts = {
            "siPrefix": True,
            "decimals": 3,
            "dec": True,
            "compactHeight": False,
            "format": "{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
        }
        self.spin_x_min.setOpts(**opts)
        self.spin_x_max.setOpts(**opts)
        self.spin_x_center.setOpts(**opts)
        self.spin_x_span.setOpts(**opts)
        opts = {
            "siPrefix": True,
            "decimals": 3,
            "dec": True,
            "compactHeight": False,
            "format": "{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
        }
        self.spin_y_min.setOpts(**opts)
        self.spin_y_max.setOpts(**opts)

        self.figure.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._install_translation()

        self.adjustSize()

    def _setup_translation(self) -> None:
        super()._setup_translation()

        cast(QLabel, self.form_layout_frequency.labelForField(self.spin_x_min)).setText(
            self.tr("Minimum:")
        )
        cast(QLabel, self.form_layout_frequency.labelForField(self.spin_x_max)).setText(
            self.tr("Maximum:")
        )
        cast(
            QLabel, self.form_layout_frequency.labelForField(self.spin_x_center)
        ).setText(self.tr("Center:"))
        cast(
            QLabel, self.form_layout_frequency.labelForField(self.spin_x_span)
        ).setText(self.tr("Span:"))

        cast(QLabel, self.form_layout_voltage.labelForField(self.spin_y_min)).setText(
            self.tr("Minimum:")
        )
        cast(QLabel, self.form_layout_voltage.labelForField(self.spin_y_max)).setText(
            self.tr("Maximum:")
        )

        self.switch_data_action.setText(self.tr("Show Absorption"))
        self.switch_data_action.setToolTip(
            self.tr("Switch Y data between absorption and voltage")
        )

        self._cursor_x.suffix = _translate("unit", "s")
        self._cursor_y.suffix = _translate("unit", "V")

        self.box_time.setWindowTitle(self.tr("Time"))
        self.check_x_range_persists.setText(self.tr("Keep time range"))

        self.button_zoom_x_out_coarse.setText(self.tr("−50%"))
        self.button_zoom_x_out_fine.setText(self.tr("−10%"))
        self.button_zoom_x_in_fine.setText(self.tr("+10%"))
        self.button_zoom_x_in_coarse.setText(self.tr("+50%"))

        self.box_voltage.setWindowTitle(self.tr("Vertical Axis"))
        self.check_y_range_persists.setText(self.tr("Keep voltage range"))

        self.button_zoom_y_out_coarse.setText(self.tr("−50%"))
        self.button_zoom_y_out_fine.setText(self.tr("−10%"))
        self.button_zoom_y_in_fine.setText(self.tr("+10%"))
        self.button_zoom_y_in_coarse.setText(self.tr("+50%"))

        self.spin_x_min.setSuffix(_translate("unit", "s"))
        self.spin_x_max.setSuffix(_translate("unit", "s"))
        self.spin_x_center.setSuffix(_translate("unit", "s"))
        self.spin_x_span.setSuffix(_translate("unit", "s"))

        self.spin_y_min.setSuffix(_translate("unit", "V"))
        self.spin_y_max.setSuffix(_translate("unit", "V"))

        self.figure.setLabel(
            "bottom",
            text=_translate("plot axes labels", "Time"),
            units=_translate("unit", "s"),
        )
        self.figure.setLabel(
            "left",
            text=_translate("plot axes labels", "Voltage"),
            units=_translate("unit", "V"),
        )

        self._view_all_action.setText(
            _translate("plot context menu action", "View All")
        )
        self._canvas.ctrl.alphaGroup.parent().setTitle(
            _translate("plot context menu action", "Alpha")
        )
        self._canvas.ctrl.gridGroup.parent().setTitle(
            _translate("plot context menu action", "Grid")
        )
        self._canvas.ctrl.xGridCheck.setText(
            _translate("plot context menu action", "Show X Grid")
        )
        self._canvas.ctrl.yGridCheck.setText(
            _translate("plot context menu action", "Show Y Grid")
        )
        self._canvas.ctrl.label.setText(
            _translate("plot context menu action", "Opacity")
        )
        self._canvas.ctrl.alphaGroup.setTitle(
            _translate("plot context menu action", "Alpha")
        )
        self._canvas.ctrl.autoAlphaCheck.setText(
            _translate("plot context menu action", "Auto")
        )

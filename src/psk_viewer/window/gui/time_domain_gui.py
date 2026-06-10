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

from ...utils import the
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
        self.box_time: QDockWidget = QDockWidget(self)
        self.box_time.setObjectName("box_time")
        self.group_time: QWidget = QWidget(self.box_time)
        self.v_layout_time: QVBoxLayout = QVBoxLayout(self.group_time)
        self.form_layout_time: QFormLayout = QFormLayout()
        self.grid_layout_time: QGridLayout = QGridLayout()

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
        self.box_voltage: QDockWidget = QDockWidget(self)
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

        with the(self.form_layout_time) as layout:
            layout.addRow(self.tr("Minimum:"), self.spin_x_min)
            layout.addRow(self.tr("Maximum:"), self.spin_x_max)
            layout.addRow(self.tr("Center:"), self.spin_x_center)
            layout.addRow(self.tr("Span:"), self.spin_x_span)

        with the(self.grid_layout_time) as layout:
            layout.addWidget(self.check_x_range_persists, 0, 0, 1, 4)
            layout.addWidget(self.button_zoom_x_out_coarse, 1, 0)
            layout.addWidget(self.button_zoom_x_out_fine, 1, 1)
            layout.addWidget(self.button_zoom_x_in_fine, 1, 2)
            layout.addWidget(self.button_zoom_x_in_coarse, 1, 3)

        with the(self.v_layout_time) as layout:
            layout.addLayout(self.form_layout_time)
            layout.addLayout(self.grid_layout_time)

        with the(self.form_layout_voltage) as layout:
            layout.addRow(self.tr("Minimum:"), self.spin_y_min)
            layout.addRow(self.tr("Maximum:"), self.spin_y_max)

        with the(self.grid_layout_voltage) as layout:
            layout.addWidget(self.check_y_range_persists, 0, 0, 1, 4)
            layout.addWidget(self.button_zoom_y_out_coarse, 1, 0)
            layout.addWidget(self.button_zoom_y_out_fine, 1, 1)
            layout.addWidget(self.button_zoom_y_in_fine, 1, 2)
            layout.addWidget(self.button_zoom_y_in_coarse, 1, 3)

        with the(self.switch_data_action) as button:
            button.setEnabled(False)
            button.setCheckable(True)
            button.setShortcut("Ctrl+`")

        with the(self.v_layout_voltage) as layout:
            layout.addWidget(self.switch_data_action)
            layout.addLayout(self.form_layout_voltage)
            layout.addLayout(self.grid_layout_voltage)

        # TODO: adjust size when undocked
        self.box_time.setWidget(self.group_time)
        self.toolbar.toolboxes_menu.addAction(self.box_time.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_time)

        self.box_voltage.setWidget(self.group_voltage)
        self.toolbar.toolboxes_menu.addAction(self.box_voltage.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_voltage)

        with the(
            dict(
                siPrefix=True,
                decimals=3,
                dec=True,
                compactHeight=False,
                format="{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
            )
        ) as opts:
            self.spin_x_min.setOpts(**opts)
            self.spin_x_max.setOpts(**opts)
            self.spin_x_center.setOpts(**opts)
            self.spin_x_span.setOpts(**opts)
        with the(
            dict(
                siPrefix=True,
                decimals=3,
                dec=True,
                compactHeight=False,
                format="{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
            )
        ) as opts:
            self.spin_y_min.setOpts(**opts)
            self.spin_y_max.setOpts(**opts)

        self.figure.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._install_translation()

        self.adjustSize()

    def _setup_translation(self) -> None:
        super()._setup_translation()

        with the(self.form_layout_time.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_x_min)).setText(self.tr("Minimum:"))
            cast(QLabel, labelForField(self.spin_x_max)).setText(self.tr("Maximum:"))
            cast(QLabel, labelForField(self.spin_x_center)).setText(self.tr("Center:"))
            cast(QLabel, labelForField(self.spin_x_span)).setText(self.tr("Span:"))

        with the(self.form_layout_voltage.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_y_min)).setText(self.tr("Minimum:"))
            cast(QLabel, labelForField(self.spin_y_max)).setText(self.tr("Maximum:"))

        with the(self.switch_data_action) as button:
            button.setText(self.tr("Show Absorption"))
            button.setToolTip(self.tr("Switch Y data between absorption and voltage"))

        with (
            the(_translate("unit", "s")) as unit_x,
            the(_translate("unit", "V")) as unit_y,
        ):
            self._cursor_x.suffix = unit_x
            self._cursor_y.suffix = unit_y

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

            self.spin_x_min.setSuffix(unit_x)
            self.spin_x_max.setSuffix(unit_x)
            self.spin_x_center.setSuffix(unit_x)
            self.spin_x_span.setSuffix(unit_x)

            self.spin_y_min.setSuffix(unit_y)
            self.spin_y_max.setSuffix(unit_y)

            self.figure.setLabel(
                "bottom",
                text=_translate("plot axes labels", "Time"),
                units=unit_x,
            )
            self.figure.setLabel(
                "left",
                text=_translate("plot axes labels", "Voltage"),
                units=unit_y,
            )

        self._view_all_action.setText(
            _translate("plot context menu action", "View All")
        )
        with the(self._canvas.ctrl) as c:
            c.alphaGroup.parent().setTitle(
                _translate("plot context menu action", "Alpha")
            )
            c.gridGroup.parent().setTitle(
                _translate("plot context menu action", "Grid")
            )
            c.xGridCheck.setText(_translate("plot context menu action", "Show X Grid"))
            c.yGridCheck.setText(_translate("plot context menu action", "Show Y Grid"))
            c.label.setText(_translate("plot context menu action", "Opacity"))
            c.alphaGroup.setTitle(_translate("plot context menu action", "Alpha"))
            c.autoAlphaCheck.setText(_translate("plot context menu action", "Auto"))

from typing import cast

import numpy as np
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
from ...widgets.found_lines_model import FoundLinesModel
from ...widgets.table_view import TableView
from ...widgets.toolbar import FrequencyDomainToolbar
from . import GUI

__all__ = ["FrequencyDomainGUI"]

_translate = QCoreApplication.translate


class FrequencyDomainGUI(GUI):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        # Frequency box
        self.box_frequency: QDockWidget = QDockWidget(self.central_widget)
        self.box_frequency.setObjectName("box_frequency")
        self.group_frequency: QWidget = QWidget(self.box_frequency)
        self.v_layout_frequency: QVBoxLayout = QVBoxLayout(self.group_frequency)
        self.form_layout_frequency: QFormLayout = QFormLayout()
        self.grid_layout_frequency: QGridLayout = QGridLayout()

        self.spin_x_min: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_x_max: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_x_center: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_x_span: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_x_span.setMinimum(0.01)

        self.check_x_range_persists: QCheckBox = QCheckBox(self.group_frequency)

        # Zoom X
        self.button_zoom_x_out_coarse: QPushButton = QPushButton(self.group_frequency)
        self.button_zoom_x_out_fine: QPushButton = QPushButton(self.group_frequency)
        self.button_zoom_x_in_fine: QPushButton = QPushButton(self.group_frequency)
        self.button_zoom_x_in_coarse: QPushButton = QPushButton(self.group_frequency)

        # Move X
        self.button_move_x_left_coarse: QPushButton = QPushButton(self.group_frequency)
        self.button_move_x_left_fine: QPushButton = QPushButton(self.group_frequency)
        self.button_move_x_right_fine: QPushButton = QPushButton(self.group_frequency)
        self.button_move_x_right_coarse: QPushButton = QPushButton(self.group_frequency)

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

        # Find Lines box
        self.box_find_lines: QDockWidget = QDockWidget(self.central_widget)
        self.box_find_lines.setObjectName("box_find_lines")
        self.group_find_lines: QWidget = QWidget(self.box_find_lines)
        self.v_layout_find_lines: QVBoxLayout = QVBoxLayout(self.group_find_lines)
        self.form_layout_find_lines: QFormLayout = QFormLayout()
        self.grid_layout_find_lines: QGridLayout = QGridLayout()
        self.spin_threshold: pg.SpinBox = pg.SpinBox(self.group_find_lines)
        self.spin_threshold.setMinimum(1.0)
        self.spin_threshold.setMaximum(10000.0)
        self.button_find_lines: QPushButton = QPushButton(self.group_find_lines)
        self.button_clear_automatically_found_lines: QPushButton = QPushButton(
            self.group_find_lines
        )
        self.button_prev_found_line: QPushButton = QPushButton(self.group_find_lines)
        self.button_next_found_line: QPushButton = QPushButton(self.group_find_lines)

        # Found Lines table
        self.box_found_lines: QDockWidget = QDockWidget(self.central_widget)
        self.box_found_lines.setObjectName("box_found_lines")
        self.group_found_lines: QWidget = QWidget(self.box_found_lines)
        self.v_layout_found_lines: QVBoxLayout = QVBoxLayout(self.group_found_lines)
        self.form_layout_found_lines: QFormLayout = QFormLayout()
        self.spin_df: pg.SpinBox = pg.SpinBox(self.group_found_lines)
        self.spin_df.setMinimum(0.01e6)
        self.spin_df.setMaximum(10.0e6)
        self.spin_df.setOpts(scaleAtZero=1e6)
        self.table_found_lines: TableView = TableView(
            self.settings, self.group_found_lines
        )
        self.model_found_lines: FoundLinesModel = FoundLinesModel(self)

        self.toolbar: FrequencyDomainToolbar = FrequencyDomainToolbar(self)

        self._setup_appearance()

    def _setup_appearance(self) -> None:
        super()._setup_appearance()

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        with the(self.form_layout_frequency) as layout:
            layout.addRow(self.tr("Minimum:"), self.spin_x_min)
            layout.addRow(self.tr("Maximum:"), self.spin_x_max)
            layout.addRow(self.tr("Center:"), self.spin_x_center)
            layout.addRow(self.tr("Span:"), self.spin_x_span)

        with the(self.grid_layout_frequency) as layout:
            layout.addWidget(self.check_x_range_persists, 0, 0, 1, 4)
            layout.addWidget(self.button_zoom_x_out_coarse, 1, 0)
            layout.addWidget(self.button_zoom_x_out_fine, 1, 1)
            layout.addWidget(self.button_zoom_x_in_fine, 1, 2)
            layout.addWidget(self.button_zoom_x_in_coarse, 1, 3)

            layout.addWidget(self.button_move_x_left_coarse, 2, 0)
            layout.addWidget(self.button_move_x_left_fine, 2, 1)
            layout.addWidget(self.button_move_x_right_fine, 2, 2)
            layout.addWidget(self.button_move_x_right_coarse, 2, 3)

        with the(self.v_layout_frequency) as layout:
            layout.addLayout(self.form_layout_frequency)
            layout.addLayout(self.grid_layout_frequency)

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

        self.form_layout_find_lines.addRow(
            self.tr("Search threshold:"), self.spin_threshold
        )

        with the(self.grid_layout_find_lines) as layout:
            layout.addWidget(self.button_find_lines, 0, 0, 1, 2)
            layout.addWidget(self.button_clear_automatically_found_lines, 1, 0, 1, 2)
            layout.addWidget(self.button_prev_found_line, 2, 0)
            layout.addWidget(self.button_next_found_line, 2, 1)

        with the(self.v_layout_find_lines) as layout:
            layout.addLayout(self.form_layout_find_lines)
            layout.addLayout(self.grid_layout_find_lines)

        self.form_layout_found_lines.addRow(
            self.tr("Frequency uncertainty:"), self.spin_df
        )

        with the(self.v_layout_found_lines) as layout:
            layout.addWidget(self.table_found_lines, 1)
            layout.addLayout(self.form_layout_found_lines)

        # TODO: adjust size when undocked
        self.box_frequency.setWidget(self.group_frequency)
        self.toolbar.toolboxes_menu.addAction(self.box_frequency.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_frequency)

        self.box_voltage.setWidget(self.group_voltage)
        self.toolbar.toolboxes_menu.addAction(self.box_voltage.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_voltage)

        self.box_find_lines.setWidget(self.group_find_lines)
        self.toolbar.toolboxes_menu.addAction(self.box_find_lines.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_find_lines)

        self.box_found_lines.setWidget(self.group_found_lines)
        self.toolbar.toolboxes_menu.addAction(self.box_found_lines.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.box_found_lines)

        self.button_clear_automatically_found_lines.setEnabled(False)
        self.button_next_found_line.setEnabled(False)
        self.button_prev_found_line.setEnabled(False)

        self.model_found_lines.set_format(
            [
                FoundLinesModel.Format(3, 1e-6),
                FoundLinesModel.Format(4, 1e3),
                FoundLinesModel.Format(
                    precision=4,
                    scale=np.nan,
                    fancy=self.settings.fancy_table_numbers,
                    log10=self.settings.log10_gamma,
                ),
            ]
        )

        self.table_found_lines.setModel(self.model_found_lines)

        with the(
            dict(
                siPrefix=True,
                decimals=6,
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

        self.spin_threshold.setOpts(compactHeight=False)
        self.spin_df.setOpts(
            siPrefix=True,
            decimals=1,
            dec=True,
            compactHeight=False,
            format="{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
        )

        self.figure.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._install_translation()

        self.adjustSize()

    def _setup_translation(self) -> None:
        super()._setup_translation()

        with the(self.form_layout_frequency.labelForField) as labelForField:
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

        with the(self.form_layout_find_lines.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_threshold)).setText(
                self.tr("Search threshold:")
            )

        with the(self.form_layout_found_lines.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_df)).setText(
                self.tr("Frequency uncertainty:")
            )

        with (
            the(_translate("unit", "Hz")) as unit_x,
            the(_translate("unit", "V")) as unit_y,
        ):
            self._cursor_x.suffix = unit_x
            self._cursor_y.suffix = unit_y

            self.box_frequency.setWindowTitle(self.tr("Frequency"))
            self.check_x_range_persists.setText(self.tr("Keep frequency range"))

            self.button_zoom_x_out_coarse.setText(self.tr("−50%"))
            self.button_zoom_x_out_fine.setText(self.tr("−10%"))
            self.button_zoom_x_in_fine.setText(self.tr("+10%"))
            self.button_zoom_x_in_coarse.setText(self.tr("+50%"))

            self.button_move_x_left_coarse.setText(
                "−" + pg.siFormat(5e8, suffix=unit_x)
            )
            self.button_move_x_left_fine.setText("−" + pg.siFormat(5e7, suffix=unit_x))
            self.button_move_x_right_fine.setText("+" + pg.siFormat(5e7, suffix=unit_x))
            self.button_move_x_right_coarse.setText(
                "+" + pg.siFormat(5e8, suffix=unit_x)
            )

            self.box_voltage.setWindowTitle(self.tr("Vertical Axis"))
            self.check_y_range_persists.setText(self.tr("Keep voltage range"))

            self.button_zoom_y_out_coarse.setText(self.tr("−50%"))
            self.button_zoom_y_out_fine.setText(self.tr("−10%"))
            self.button_zoom_y_in_fine.setText(self.tr("+10%"))
            self.button_zoom_y_in_coarse.setText(self.tr("+50%"))

            self.box_find_lines.setWindowTitle(self.tr("Find Lines Automatically"))
            self.group_find_lines.setToolTip(
                self.tr("Try to detect lines automatically")
            )
            self.button_find_lines.setText(self.tr("Find Lines Automatically"))
            self.button_clear_automatically_found_lines.setText(
                self.tr("Clear Automatically Found Lines")
            )
            self.button_prev_found_line.setText(self.tr("Previous Line"))
            self.button_next_found_line.setText(self.tr("Next Line"))

            self.box_found_lines.setWindowTitle(self.tr("Found Lines"))

            self.spin_x_min.setSuffix(unit_x)
            self.spin_x_max.setSuffix(unit_x)
            self.spin_x_center.setSuffix(unit_x)
            self.spin_x_span.setSuffix(unit_x)
            self.spin_df.setSuffix(unit_x)

            self.spin_y_min.setSuffix(unit_y)
            self.spin_y_max.setSuffix(unit_y)

            self.figure.setLabel(
                "bottom",
                text=_translate("plot axes labels", "Frequency"),
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

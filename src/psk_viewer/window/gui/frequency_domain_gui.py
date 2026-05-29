from typing import cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDockWidget,
    QFormLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from psk_viewer.widgets.data_model import DataModel
from psk_viewer.widgets.found_lines_model import FoundLinesModel
from psk_viewer.widgets.table_view import TableView
from ...widgets.data_model import DataModel
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
        self.table_found_lines: TableView = TableView(
            self.settings, self.box_found_lines
        )
        self.model_found_lines: FoundLinesModel = FoundLinesModel(self)

        self.toolbar: FrequencyDomainToolbar = FrequencyDomainToolbar(self)

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

        self.grid_layout_frequency.addWidget(self.button_move_x_left_coarse, 2, 0)
        self.grid_layout_frequency.addWidget(self.button_move_x_left_fine, 2, 1)
        self.grid_layout_frequency.addWidget(self.button_move_x_right_fine, 2, 2)
        self.grid_layout_frequency.addWidget(self.button_move_x_right_coarse, 2, 3)

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

        self.form_layout_find_lines.addRow(
            self.tr("Search threshold:"), self.spin_threshold
        )
        self.grid_layout_find_lines.addWidget(self.button_find_lines, 0, 0, 1, 2)
        self.grid_layout_find_lines.addWidget(
            self.button_clear_automatically_found_lines, 1, 0, 1, 2
        )
        self.grid_layout_find_lines.addWidget(self.button_prev_found_line, 2, 0)
        self.grid_layout_find_lines.addWidget(self.button_next_found_line, 2, 1)

        self.v_layout_find_lines.addLayout(self.form_layout_find_lines)
        self.v_layout_find_lines.addLayout(self.grid_layout_find_lines)

        # TODO: adjust size when undocked
        self.box_frequency.setWidget(self.group_frequency)
        self.box_frequency.setFeatures(
            self.box_frequency.features()
            & ~QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_frequency)

        self.box_voltage.setWidget(self.group_voltage)
        self.box_voltage.setFeatures(
            self.box_voltage.features()
            & ~QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_voltage)

        self.box_find_lines.setWidget(self.group_find_lines)
        self.box_find_lines.setFeatures(
            self.box_find_lines.features()
            & ~QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_find_lines)

        self.box_found_lines.setWidget(self.table_found_lines)
        self.box_found_lines.setFeatures(
            self.box_found_lines.features()
            & ~QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.box_found_lines)

        self.button_clear_automatically_found_lines.setEnabled(False)
        self.button_next_found_line.setEnabled(False)
        self.button_prev_found_line.setEnabled(False)

        self.model_found_lines.set_format(
            [
                DataModel.Format(3, 1e-6),
                DataModel.Format(4, 1e3),
                DataModel.Format(4, np.nan, self.settings.fancy_table_numbers),
            ]
        )
        self.table_found_lines.setModel(self.model_found_lines)
        self.table_found_lines.setMouseTracking(True)
        self.table_found_lines.setContextMenuPolicy(
            Qt.ContextMenuPolicy.ActionsContextMenu
        )
        self.table_found_lines.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table_found_lines.setDropIndicatorShown(False)
        self.table_found_lines.setDragDropOverwriteMode(False)
        self.table_found_lines.setCornerButtonEnabled(False)
        self.table_found_lines.setSortingEnabled(True)
        self.table_found_lines.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.table_found_lines.setAlternatingRowColors(True)
        self.table_found_lines.horizontalHeader().setDefaultSectionSize(90)
        self.table_found_lines.horizontalHeader().setHighlightSections(False)
        self.table_found_lines.horizontalHeader().setStretchLastSection(True)
        self.table_found_lines.verticalHeader().setVisible(False)
        self.table_found_lines.verticalHeader().setHighlightSections(False)

        opts = {
            "siPrefix": True,
            "decimals": 6,
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

        self.spin_threshold.setOpts(compactHeight=False)

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

        cast(
            QLabel, self.form_layout_find_lines.labelForField(self.spin_threshold)
        ).setText(self.tr("Search threshold:"))

        self._cursor_x.suffix = _translate("unit", "Hz")
        self._cursor_y.suffix = _translate("unit", "V")

        self.box_frequency.setWindowTitle(self.tr("Frequency"))
        self.check_x_range_persists.setText(self.tr("Keep frequency range"))

        self.button_zoom_x_out_coarse.setText(self.tr("−50%"))
        self.button_zoom_x_out_fine.setText(self.tr("−10%"))
        self.button_zoom_x_in_fine.setText(self.tr("+10%"))
        self.button_zoom_x_in_coarse.setText(self.tr("+50%"))

        self.button_move_x_left_coarse.setText(
            "−" + pg.siFormat(5e8, suffix=_translate("unit", "Hz"))
        )
        self.button_move_x_left_fine.setText(
            "−" + pg.siFormat(5e7, suffix=_translate("unit", "Hz"))
        )
        self.button_move_x_right_fine.setText(
            "+" + pg.siFormat(5e7, suffix=_translate("unit", "Hz"))
        )
        self.button_move_x_right_coarse.setText(
            "+" + pg.siFormat(5e8, suffix=_translate("unit", "Hz"))
        )

        self.box_voltage.setWindowTitle(self.tr("Vertical Axis"))
        self.check_y_range_persists.setText(self.tr("Keep voltage range"))

        self.button_zoom_y_out_coarse.setText(self.tr("−50%"))
        self.button_zoom_y_out_fine.setText(self.tr("−10%"))
        self.button_zoom_y_in_fine.setText(self.tr("+10%"))
        self.button_zoom_y_in_coarse.setText(self.tr("+50%"))

        self.box_find_lines.setWindowTitle(self.tr("Find Lines Automatically"))
        self.group_find_lines.setToolTip(self.tr("Try to detect lines automatically"))
        self.button_find_lines.setText(self.tr("Find Lines Automatically"))
        self.button_clear_automatically_found_lines.setText(
            self.tr("Clear Automatically Found Lines")
        )
        self.button_prev_found_line.setText(self.tr("Previous Line"))
        self.button_next_found_line.setText(self.tr("Next Line"))

        self.box_found_lines.setWindowTitle(self.tr("Found Lines"))

        self.spin_x_min.setSuffix(_translate("unit", "Hz"))
        self.spin_x_max.setSuffix(_translate("unit", "Hz"))
        self.spin_x_center.setSuffix(_translate("unit", "Hz"))
        self.spin_x_span.setSuffix(_translate("unit", "Hz"))

        self.spin_y_min.setSuffix(_translate("unit", "V"))
        self.spin_y_max.setSuffix(_translate("unit", "V"))

        self.figure.setLabel(
            "bottom",
            text=_translate("plot axes labels", "Frequency"),
            units=_translate("unit", "Hz"),
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

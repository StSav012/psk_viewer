# -*- coding: utf-8 -*-

import os
from typing import Callable, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtCore import QCoreApplication, QPointF, Qt, QItemSelectionModel, QModelIndex
from PyQt5.QtGui import QBrush, QPalette, QColor
from PyQt5.QtWidgets import QAction, QHeaderView, QDesktopWidget
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

import detection
from gui import GUI
from utils import copy_to_clipboard, load_data_fs, load_data_scandat, load_data_csv, resource_path

try:
    from typing import Final
except ImportError:
    class _Final:
        def __getitem__(self, item):
            return item


    Final = _Final()

pg.ViewBox.suggestPadding = lambda *_: 0.0


class App(GUI):
    PSK_DATA_MODE: Final[int] = 1
    FS_DATA_MODE: Final[int] = -1

    def __init__(self, flags=Qt.WindowFlags()):
        super().__init__(flags=flags)

        self._data_mode: int = 0

        self._is_dark: bool = QPalette().color(QPalette.Window).lightness() < 128

        self.legend_item: Optional[pg.LegendItem] = None

        self._canvas: pg.PlotItem = self.figure.getPlotItem()
        self._view_all_action: QAction = QAction()

        self._plot_line: pg.PlotDataItem = self.figure.plot(np.empty(0), name='', pen=self.settings.line_color)
        self._plot_line.yData = np.empty(0)

        self._ignore_scale_change: bool = False

        try:
            self.model_signal: np.ndarray = np.loadtxt(resource_path('averaged fs signal filtered.csv'))
        except (OSError, BlockingIOError):
            self.model_signal: np.ndarray = np.empty(0)
        self.user_found_lines: pg.PlotDataItem = \
            self._canvas.scatterPlot(np.empty(0),
                                     pen=self.settings.line_color, brush=self.settings.line_color)
        self.automatically_found_lines: pg.PlotDataItem = \
            self._canvas.scatterPlot(np.empty(0),
                                     pen=self.settings.line_color, brush=self.settings.line_color)

        # cross hair
        self._crosshair_v_line = pg.InfiniteLine(angle=90, movable=False)
        self._crosshair_h_line = pg.InfiniteLine(angle=0, movable=False)

        self._mouse_moved_signal_proxy = pg.SignalProxy(self.figure.scene().sigMouseMoved,
                                                        rateLimit=10, slot=self.on_mouse_moved)
        self._axis_range_changed_signal_proxy = pg.SignalProxy(self.figure.sigRangeChanged,
                                                               rateLimit=20, slot=self.on_lim_changed)

        self.setup_ui()

        self.load_config()

        self.setup_ui_actions()

    def setup_ui(self):
        if self._is_dark:
            self.figure.setBackground(QBrush(pg.mkColor(0, 0, 0)))
            label: str
            for label, ax_d in self._canvas.axes.items():
                ax: pg.AxisItem = ax_d['item']
                ax.setPen('d')
                ax.setTextPen('d')
        else:
            self.figure.setBackground(QBrush(pg.mkColor(255, 255, 255)))
            label: str
            for label, ax_d in self._canvas.axes.items():
                ax: pg.AxisItem = ax_d['item']
                ax.setPen('k')
                ax.setTextPen('k')
        if self.legend is not None:
            self.legend_item = pg.LegendItem(offset=(0, 0))
            self.legend.setCentralItem(self.legend_item)
            if self._is_dark:
                self.legend.setBackground(QBrush(pg.mkColor(0, 0, 0, 0)))
                self.legend_item.setLabelTextColor(255, 255, 255, 255)
            else:
                self.legend.setBackground(QBrush(pg.mkColor(255, 255, 255, 0)))
                self.legend_item.setLabelTextColor(0, 0, 0, 255)
            # self._legend_box.sceneObj.sigMouseClicked.connect(self.on_legend_click)

        self.figure.plotItem.addItem(self._crosshair_v_line, ignoreBounds=True)
        self.figure.plotItem.addItem(self._crosshair_h_line, ignoreBounds=True)
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)

        # customize menu
        titles_to_leave: List[str] = [
            self._canvas.ctrl.alphaGroup.parent().title(),
            self._canvas.ctrl.gridGroup.parent().title(),
        ]
        for action in self._canvas.ctrlMenu.actions():
            if action.text() not in titles_to_leave:
                self._canvas.ctrlMenu.removeAction(action)
        self._canvas.vb.menu = self._canvas.ctrlMenu
        self._canvas.ctrlMenu = None
        self._canvas.vb.menu.addAction(self._view_all_action)
        self.figure.sceneObj.contextMenu = None

        self.translate_ui()

    def translate_ui(self):
        _translate: Callable[[str, str, Optional[str], int], str] = QCoreApplication.translate

        self.figure.setLabel('bottom',
                             text=_translate("plot axes labels", 'Frequency'),
                             units=_translate('unit', 'Hz'),
                             unitPrefix=_translate('unit prefix', 'M'))
        self.figure.setLabel('left',
                             text=_translate("plot axes labels", 'Voltage'),
                             units=_translate('unit', 'V'),
                             unitPrefix=_translate('unit prefix', 'm'))

        self.plot_toolbar.open_action.setIconText(_translate("plot toolbar action", "Open"))
        self.plot_toolbar.open_action.setToolTip(_translate("plot toolbar action", "Load spectrometer data"))
        self.plot_toolbar.clear_action.setIconText(_translate("plot toolbar action", "Clear"))
        self.plot_toolbar.clear_action.setToolTip(_translate("plot toolbar action", "Clear lines and markers"))
        self.plot_toolbar.differentiate_action.setIconText(_translate("plot toolbar action",
                                                                      "Calculate second derivative"))
        self.plot_toolbar.differentiate_action.setToolTip(_translate("plot toolbar action",
                                                                     "Calculate finite-step second derivative"))
        self.plot_toolbar.save_data_action.setIconText(_translate("plot toolbar action", "Save Data"))
        self.plot_toolbar.save_data_action.setToolTip(_translate("plot toolbar action", "Export the visible data"))
        self.plot_toolbar.copy_figure_action.setIconText(_translate("plot toolbar action", "Copy Figure"))
        self.plot_toolbar.copy_figure_action.setToolTip(_translate("plot toolbar action", "Copy the plot as an image"))
        self.plot_toolbar.save_figure_action.setIconText(_translate("plot toolbar action", "Save Figure"))
        self.plot_toolbar.save_figure_action.setToolTip(_translate("plot toolbar action",
                                                                   "Save the plot into clipboard"))
        self.plot_toolbar.trace_action.setIconText(_translate("plot toolbar action", "Mark"))
        self.plot_toolbar.trace_action.setToolTip(_translate("plot toolbar action", "Mark data points"))
        self.plot_toolbar.copy_trace_action.setIconText(_translate("plot toolbar action", "Copy Marked"))
        self.plot_toolbar.copy_trace_action.setToolTip(_translate("plot toolbar action",
                                                                  "Copy marked points values into clipboard"))
        self.plot_toolbar.save_trace_action.setIconText(_translate("plot toolbar action", "Save Marked"))
        self.plot_toolbar.save_trace_action.setToolTip(_translate("plot toolbar action", "Save marked points values"))
        self.plot_toolbar.clear_trace_action.setIconText(_translate("plot toolbar action", "Clear Marked"))
        self.plot_toolbar.clear_trace_action.setToolTip(_translate("plot toolbar action", "Clear marked points"))
        self.plot_toolbar.configure_action.setIconText(_translate("plot toolbar action", "Configure"))
        self.plot_toolbar.configure_action.setToolTip(_translate("plot toolbar action", "Edit parameters"))

        self.plot_toolbar.parameters_title = _translate('plot config window title', 'Figure options')

        self._view_all_action.setText(_translate("plot context menu action", "View All"))
        self._canvas.ctrl.alphaGroup.parent().setTitle(_translate("plot context menu action", "Alpha"))
        self._canvas.ctrl.gridGroup.parent().setTitle(_translate("plot context menu action", "Grid"))

        self._canvas.vb.menu.setTitle(_translate('menu', 'Plot Options'))

    def load_config(self):
        self._loading = True
        # common settings
        if self.settings.contains('windowGeometry'):
            self.restoreGeometry(self.settings.value('windowGeometry', ''))
        else:
            window_frame = self.frameGeometry()
            desktop_center = QDesktopWidget().availableGeometry().center()
            window_frame.moveCenter(desktop_center)
            self.move(window_frame.topLeft())
        _v = self.settings.value('windowState', '')
        if isinstance(_v, str):
            self.restoreState(_v.encode())
        else:
            self.restoreState(_v)

        min_freq = self.get_config_value('frequency', 'lower',
                                         0.0,
                                         float)
        max_freq = self.get_config_value('frequency', 'upper',
                                         1e12,
                                         float)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_span.setValue(max_freq - min_freq)
        self.spin_frequency_center.setValue(0.5 * (max_freq + min_freq))
        self.set_frequency_range(lower_value=min_freq, upper_value=max_freq)
        self.check_frequency_persists.setChecked(self.get_config_value('frequency', 'persists', False, bool))

        min_voltage: float = self.get_config_value('voltage', 'lower', pg.np.nan, float)
        max_voltage: float = self.get_config_value('voltage', 'upper', pg.np.nan, float)
        if not pg.np.isnan(min_voltage):
            self.spin_voltage_min.setValue(min_voltage)
            self.spin_voltage_max.setMinimum(min_voltage)
        if not pg.np.isnan(max_voltage):
            self.spin_voltage_max.setValue(max_voltage)
            self.spin_voltage_min.setMaximum(max_voltage)
        if not pg.np.isnan(min_voltage) and not pg.np.isnan(max_voltage):
            self.set_voltage_range(lower_value=min_voltage, upper_value=max_voltage)
        self.check_voltage_persists.setChecked(self.get_config_value('voltage', 'persists', False, bool))

        self.spin_threshold.setValue(self.get_config_value('lineSearch', 'threshold', 12.0, float))

        self._loading = False
        return

    def setup_ui_actions(self):
        self.plot_toolbar.open_action.triggered.connect(self.load_data)
        self.plot_toolbar.clear_action.triggered.connect(self.clear)
        self.plot_toolbar.differentiate_action.triggered.connect(self.calculate_second_derivative)
        self.plot_toolbar.save_data_action.triggered.connect(self.save_data)
        self.plot_toolbar.copy_figure_action.triggered.connect(self.copy_figure)
        self.plot_toolbar.save_figure_action.triggered.connect(self.save_figure)
        self.plot_toolbar.copy_trace_action.triggered.connect(self.copy_found_lines)
        self.plot_toolbar.save_trace_action.triggered.connect(self.save_found_lines)
        self.plot_toolbar.clear_trace_action.triggered.connect(self.clear_found_lines)
        self.plot_toolbar.configure_action.triggered.connect(self.plot_toolbar.edit_parameters)

        self.spin_frequency_min.valueChanged.connect(self.spin_frequency_min_changed)
        self.spin_frequency_max.valueChanged.connect(self.spin_frequency_max_changed)
        self.spin_frequency_center.valueChanged.connect(self.spin_frequency_center_changed)
        self.spin_frequency_span.valueChanged.connect(self.spin_frequency_span_changed)
        self.button_zoom_x_out_coarse.clicked.connect(lambda: self.button_zoom_x_clicked(1. / 0.5))
        self.button_zoom_x_out_fine.clicked.connect(lambda: self.button_zoom_x_clicked(1. / 0.9))
        self.button_zoom_x_in_fine.clicked.connect(lambda: self.button_zoom_x_clicked(0.9))
        self.button_zoom_x_in_coarse.clicked.connect(lambda: self.button_zoom_x_clicked(0.5))
        self.button_move_x_left_coarse.clicked.connect(lambda: self.button_move_x_clicked(-500.))
        self.button_move_x_left_fine.clicked.connect(lambda: self.button_move_x_clicked(-50.))
        self.button_move_x_right_fine.clicked.connect(lambda: self.button_move_x_clicked(50.))
        self.button_move_x_right_coarse.clicked.connect(lambda: self.button_move_x_clicked(500.))
        self.check_frequency_persists.toggled.connect(self.check_frequency_persists_toggled)

        self.spin_voltage_min.valueChanged.connect(self.spin_voltage_min_changed)
        self.spin_voltage_max.valueChanged.connect(self.spin_voltage_max_changed)
        self.button_zoom_y_out_coarse.clicked.connect(lambda: self.button_zoom_y_clicked(1. / 0.5))
        self.button_zoom_y_out_fine.clicked.connect(lambda: self.button_zoom_y_clicked(1. / 0.9))
        self.button_zoom_y_in_fine.clicked.connect(lambda: self.button_zoom_y_clicked(0.9))
        self.button_zoom_y_in_coarse.clicked.connect(lambda: self.button_zoom_y_clicked(0.5))
        self.check_voltage_persists.toggled.connect(self.on_check_voltage_persists_toggled)

        self.spin_threshold.valueChanged.connect(lambda new_value:
                                                 self.set_config_value('lineSearch', 'threshold', new_value))
        self.button_find_lines.clicked.connect(self.on_button_find_lines_clicked)
        self.button_clear_lines.clicked.connect(self.clear_found_lines)
        self.button_prev_line.clicked.connect(self.prev_found_line)
        self.button_next_line.clicked.connect(self.next_found_line)

        def adjust_columns():
            _translate = QCoreApplication.translate
            self.model_found_lines.set_header(
                [_translate('main window', 'Frequency [MHz]')] +
                [_translate('main window', 'Voltage [V]')] * (self.table_found_lines.horizontalHeader().count() - 1))
            for i in range(self.table_found_lines.horizontalHeader().count()):
                self.table_found_lines.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.model_found_lines.modelReset.connect(adjust_columns)

        line: pg.PlotDataItem
        for line in (self.automatically_found_lines, self.user_found_lines):
            line.sigPointsClicked.connect(self.on_points_clicked)

        self._view_all_action.triggered.connect(lambda: self._canvas.vb.autoRange(padding=0.0))

        self.figure.sceneObj.sigMouseClicked.connect(self.on_plot_clicked)

    def on_xlim_changed(self, xlim: List[float]):
        if not hasattr(self, 'plot'):
            return
        min_freq, max_freq = xlim
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self._loading = True
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_span.setValue(max_freq - min_freq)
        self.spin_frequency_center.setValue(0.5 * (max_freq + min_freq))
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self._loading = False
        self.set_frequency_range(lower_value=self.spin_frequency_min.value(),
                                 upper_value=self.spin_frequency_max.value())

    def on_ylim_changed(self, ylim: List[float]):
        if not hasattr(self, 'plot'):
            return
        min_voltage, max_voltage = ylim
        self.set_config_value('voltage', 'lower', min_voltage)
        self.set_config_value('voltage', 'upper', max_voltage)
        self._loading = True
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self._loading = False
        self.set_voltage_range(lower_value=self.spin_voltage_min.value(),
                               upper_value=self.spin_voltage_max.value())

    def on_points_clicked(self, item: pg.PlotDataItem, points: List[pg.SpotItem], ev: MouseClickEvent):
        if item.xData is None or item.yData is None:
            return
        if not self.trace_mode:
            return
        if ev.modifiers() == Qt.ShiftModifier:
            point: pg.SpotItem
            items: np.ndarray = item.scatter.data['item']
            index: np.ndarray = np.full(items.shape, True, np.bool_)
            for point in points:
                index &= (items != point)
            item.setData(item.xData[index], item.yData[index])

            # update the table
            if self.user_found_lines.xData is not None and self.user_found_lines.yData is not None:
                self.model_found_lines.set_data(np.column_stack((
                    np.concatenate((self.automatically_found_lines.xData, self.user_found_lines.xData)),
                    np.concatenate((self.automatically_found_lines.yData, self.user_found_lines.yData)),
                )))
            else:
                self.model_found_lines.set_data(np.column_stack((
                    self.automatically_found_lines.xData,
                    self.automatically_found_lines.yData,
                )))

            self.plot_toolbar.copy_trace_action.setEnabled(not self.model_found_lines.is_empty)
            self.plot_toolbar.save_trace_action.setEnabled(not self.model_found_lines.is_empty)
            self.plot_toolbar.clear_trace_action.setEnabled(not self.model_found_lines.is_empty)

        else:
            point: pg.SpotItem
            found_lines_frequencies: np.ndarray = self.model_found_lines.all_data[:, 0]
            selected_points: List[int] = [np.argmin(np.abs(point.pos().x() - found_lines_frequencies))
                                          for point in points]
            self.on_points_selected(selected_points)

    def on_button_find_lines_clicked(self):
        self.status_bar.showMessage(f'Found {self.find_lines(self.spin_threshold.value())} lines')

    def on_mouse_moved(self, event: Tuple[QPointF]):
        pos: QPointF = event[0]
        if self.figure.sceneBoundingRect().contains(pos):
            point: QPointF = self._canvas.vb.mapSceneToView(pos)
            self.status_bar.clearMessage()
            self._crosshair_v_line.setPos(point.x())
            self._crosshair_h_line.setPos(point.y())
            self._crosshair_h_line.setVisible(True)
            self._crosshair_v_line.setVisible(True)
            self._cursor_x.setVisible(True)
            self._cursor_y.setVisible(True)
            self._cursor_x.setValue(point.x())
            self._cursor_y.setValue(point.y())
        else:
            self._crosshair_h_line.setVisible(False)
            self._crosshair_v_line.setVisible(False)
            self._cursor_x.setVisible(False)
            self._cursor_y.setVisible(False)

    def on_plot_clicked(self, event: MouseClickEvent):
        pos: QPointF = event.scenePos()
        if self.trace_mode and event.modifiers() == Qt.NoModifier and self.figure.sceneBoundingRect().contains(pos):
            x_span: float = np.ptp(self._canvas.axes['bottom']['item'].range)
            y_span: float = np.ptp(self._canvas.axes['left']['item'].range)
            point: QPointF = self._canvas.vb.mapSceneToView(pos)
            if self._plot_line.xData is None or not self._plot_line.xData.size:
                return
            distance: np.ndarray = np.min(np.hypot((self._plot_line.xData - point.x()) / x_span,
                                                   (self._plot_line.yData - point.y()) / y_span))
            if distance < 0.01:
                closest_point_index: int = np.argmin(np.hypot((self._plot_line.xData - point.x()) / x_span,
                                                              (self._plot_line.yData - point.y()) / y_span))
                if self.user_found_lines.xData is None or self.user_found_lines.yData.size is None:
                    self.user_found_lines.setData(
                        [self._plot_line.xData[closest_point_index]], [self._plot_line.yData[closest_point_index]]
                    )
                else:
                    # avoid the same point to be marked several times
                    if np.any(
                            (self.user_found_lines.xData == self._plot_line.xData[closest_point_index])
                            &
                            (self.user_found_lines.yData == self._plot_line.yData[closest_point_index])
                    ):
                        return
                    if np.any(
                            (self.automatically_found_lines.xData == self._plot_line.xData[closest_point_index])
                            &
                            (self.automatically_found_lines.yData == self._plot_line.yData[closest_point_index])
                    ):
                        return
                    self.user_found_lines.setData(
                        np.append(self.user_found_lines.xData,
                                  self._plot_line.xData[closest_point_index]),
                        np.append(self.user_found_lines.yData,
                                  self._plot_line.yData[closest_point_index])
                    )
                self.model_found_lines.append_data([self._plot_line.xData[closest_point_index],
                                                    self._plot_line.yData[closest_point_index]])
                self.plot_toolbar.copy_trace_action.setEnabled(True)
                self.plot_toolbar.save_trace_action.setEnabled(True)
                self.plot_toolbar.clear_trace_action.setEnabled(True)

    def on_lim_changed(self, *args):
        rect: List[List[float]] = args[0][1]
        if self._ignore_scale_change:
            return
        xlim: List[float]
        ylim: List[float]
        xlim, ylim = rect
        self._ignore_scale_change = True
        self.on_xlim_changed(xlim)
        self.on_ylim_changed(ylim)
        self._ignore_scale_change = False

    def on_data_loaded(self, limits):
        if self._loading:
            return
        if limits is not None:
            min_freq, max_freq, min_voltage, max_voltage = limits
            self.set_config_value('frequency', 'lower', min_freq)
            self.set_config_value('frequency', 'upper', max_freq)
            self.set_config_value('voltage', 'lower', min_voltage)
            self.set_config_value('voltage', 'upper', max_voltage)
            self._loading = True
            if not self.check_frequency_persists.isChecked():
                self.spin_frequency_min.setMaximum(max_freq)
                self.spin_frequency_max.setMinimum(min_freq)
                self.spin_frequency_min.setValue(min_freq)
                self.spin_frequency_max.setValue(max_freq)
                self.spin_frequency_span.setValue(max_freq - min_freq)
                self.spin_frequency_center.setValue(0.5 * (max_freq + min_freq))
            else:
                self.spin_frequency_min.setMaximum(max(max_freq, self.spin_frequency_min.value()))
                self.spin_frequency_max.setMinimum(min(min_freq, self.spin_frequency_max.value()))
            if not self.check_voltage_persists.isChecked():
                self.spin_voltage_min.setMaximum(max_voltage)
                self.spin_voltage_max.setMinimum(min_voltage)
                self.spin_voltage_min.setValue(min_voltage)
                self.spin_voltage_max.setValue(max_voltage)
            else:
                self.spin_voltage_min.setMaximum(max(max_voltage, self.spin_voltage_min.value()))
                self.spin_voltage_max.setMinimum(min(min_voltage, self.spin_voltage_max.value()))
            self._loading = False
            self.set_frequency_range(lower_value=self.spin_frequency_min.value(),
                                     upper_value=self.spin_frequency_max.value())
            self.set_voltage_range(lower_value=self.spin_voltage_min.value(),
                                   upper_value=self.spin_voltage_max.value())

    def on_points_selected(self, rows: List[int]):
        self.table_found_lines.clearSelection()
        sm: QItemSelectionModel = self.table_found_lines.selectionModel()
        row: int
        for row in rows:
            index: QModelIndex = self.model_found_lines.index(row, 0)
            sm.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            self.table_found_lines.scrollTo(index)

    def spin_frequency_min_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('frequency', 'lower', new_value)
        self._loading = True
        self.spin_frequency_max.setMinimum(new_value)
        self.spin_frequency_center.setValue(0.5 * (new_value + self.spin_frequency_max.value()))
        self.spin_frequency_span.setValue(self.spin_frequency_max.value() - new_value)
        self.set_frequency_range(lower_value=new_value, upper_value=self.spin_frequency_max.value())
        self._loading = False

    def spin_frequency_max_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('frequency', 'upper', new_value)
        self._loading = True
        self.spin_frequency_min.setMaximum(new_value)
        self.spin_frequency_center.setValue(0.5 * (self.spin_frequency_min.value() + new_value))
        self.spin_frequency_span.setValue(new_value - self.spin_frequency_min.value())
        self.set_frequency_range(lower_value=self.spin_frequency_min.value(), upper_value=new_value)
        self._loading = False

    def spin_frequency_center_changed(self, new_value):
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value()
        min_freq = new_value - 0.5 * freq_span
        max_freq = new_value + 0.5 * freq_span
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def spin_frequency_span_changed(self, new_value):
        if self._loading:
            return
        freq_center = self.spin_frequency_center.value()
        min_freq = freq_center - 0.5 * new_value
        max_freq = freq_center + 0.5 * new_value
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def button_zoom_x_clicked(self, factor):
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value() * factor
        freq_center = self.spin_frequency_center.value()
        min_freq = freq_center - 0.5 * freq_span
        max_freq = freq_center + 0.5 * freq_span
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_span.setValue(freq_span)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def button_move_x_clicked(self, shift):
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value()
        freq_center = self.spin_frequency_center.value() + shift
        min_freq = freq_center - 0.5 * freq_span
        max_freq = freq_center + 0.5 * freq_span
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_center.setValue(freq_center)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def check_frequency_persists_toggled(self, new_value):
        if self._loading:
            return
        self.set_config_value('frequency', 'persists', new_value)

    def spin_voltage_min_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('voltage', 'lower', new_value)
        self._loading = True
        self.spin_voltage_max.setMinimum(new_value)
        self.set_voltage_range(lower_value=new_value, upper_value=self.spin_voltage_max.value())
        self._loading = False

    def spin_voltage_max_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('voltage', 'upper', new_value)
        self._loading = True
        self.spin_voltage_min.setMaximum(new_value)
        self.set_voltage_range(lower_value=self.spin_voltage_min.value(), upper_value=new_value)
        self._loading = False

    def button_zoom_y_clicked(self, factor):
        if self._loading:
            return
        min_voltage = self.spin_voltage_min.value()
        max_voltage = self.spin_voltage_max.value()
        voltage_span = abs(max_voltage - min_voltage) * factor
        voltage_center = (max_voltage + min_voltage) * 0.5
        min_voltage = voltage_center - 0.5 * voltage_span
        max_voltage = voltage_center + 0.5 * voltage_span
        self._loading = True
        self.set_config_value('voltage', 'lower', min_voltage)
        self.set_config_value('voltage', 'upper', max_voltage)
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.set_voltage_range(upper_value=max_voltage, lower_value=min_voltage)
        self._loading = False

    def on_check_voltage_persists_toggled(self, new_value):
        if self._loading:
            return
        self.set_config_value('voltage', 'persists', new_value)

    @property
    def line(self):
        return self._plot_line

    @property
    def label(self):
        return self._plot_line.name()

    def set_frequency_range(self, lower_value: float, upper_value: float):
        self.figure.plotItem.setXRange(lower_value, upper_value, padding=0.0)

    def set_voltage_range(self, lower_value: float, upper_value: float):
        self.figure.plotItem.setYRange(lower_value, upper_value, padding=0.0)

    def set_line_color(self, color: QColor):
        self._plot_line.setPen(color)
        self._plot_line.setBrush(color)
        self.automatically_found_lines.setSymbolPen(color)
        self.automatically_found_lines.setSymbolBrush(color)
        self.user_found_lines.setSymbolPen(color)
        self.user_found_lines.setSymbolBrush(color)
        self._canvas.replot()

    def find_lines(self, threshold: float) -> int:
        if self._data_mode == 0 or self.model_signal.size < 2:
            return 0

        from scipy import interpolate

        x: Final[np.ndarray] = self._plot_line.xData
        y: Final[np.ndarray] = self._plot_line.yData
        if x.size < 2 or y.size < 2:
            return 0

        found_lines: np.ndarray
        if self._data_mode == self.FS_DATA_MODE:
            # re-scale the signal to the actual frequency mesh
            x_model: np.ndarray = np.arange(self.model_signal.size, dtype=x.dtype) * 0.1
            f = interpolate.interp1d(x_model, self.model_signal, kind=2)
            x_model_new: np.ndarray = np.arange(x_model[0], x_model[-1],
                                                x[1] - x[0])
            y_model_new: np.ndarray = f(x_model_new)
            found_lines = detection.peaks_positions(x,
                                                    detection.correlation(y_model_new,
                                                                          x,
                                                                          y),
                                                    threshold=1.0 / threshold)
        elif self._data_mode == self.PSK_DATA_MODE:
            found_lines = detection.peaks_positions(x,
                                                    y,
                                                    threshold=1.0 / threshold)
        else:
            return 0

        self._ignore_scale_change = True
        if found_lines.size:
            self.automatically_found_lines.setData(x[found_lines],
                                                   y[found_lines])
        else:
            self.automatically_found_lines.setData(np.empty(0), np.empty(0))

        # update the table
        if self.user_found_lines.xData is not None and self.user_found_lines.yData is not None:
            self.model_found_lines.set_data(np.column_stack((
                np.concatenate((self.automatically_found_lines.xData, self.user_found_lines.xData)),
                np.concatenate((self.automatically_found_lines.yData, self.user_found_lines.yData)),
            )))
        else:
            self.model_found_lines.set_data(np.column_stack((
                self.automatically_found_lines.xData,
                self.automatically_found_lines.yData,
            )))

        self.plot_toolbar.copy_trace_action.setEnabled(not self.model_found_lines.is_empty)
        self.plot_toolbar.save_trace_action.setEnabled(not self.model_found_lines.is_empty)
        self.plot_toolbar.clear_trace_action.setEnabled(not self.model_found_lines.is_empty)

        self._ignore_scale_change = False

        return found_lines.size

    def prev_found_line(self, init_frequency: float):
        if self.model_signal.size < 2:
            return init_frequency

        prev_line_freq: np.ndarray = np.full(len(self.automatically_found_lines), np.nan)
        index: int
        line: pg.ScatterPlotItem
        for index, line in enumerate(self.automatically_found_lines):
            line_data: np.ndarray = line.getData()[0]
            if line_data is None or not line_data.size:
                continue
            i: int = np.searchsorted(line_data, init_frequency, side='right') - 2
            if 0 <= i < line_data.size and line_data[i] != init_frequency:
                prev_line_freq[index] = line_data[i]
            else:
                prev_line_freq[index] = np.nan
        prev_line_freq = prev_line_freq[~np.isnan(prev_line_freq)]
        if prev_line_freq.size:
            self.spin_frequency_center.setValue(prev_line_freq[np.argmin(init_frequency - prev_line_freq)])

    def next_found_line(self, init_frequency: float):
        if self.model_signal.size < 2:
            return init_frequency

        next_line_freq: np.ndarray = np.full(len(self.automatically_found_lines), np.nan)
        index: int
        line: pg.ScatterPlotItem
        for index, line in enumerate(self.automatically_found_lines):
            line_data: np.ndarray = line.getData()[0]
            if line_data is None or not line_data.size:
                continue
            i: int = np.searchsorted(line_data, init_frequency, side='left') + 1
            if i < line_data.size and line_data[i] != init_frequency:
                next_line_freq[index] = line_data[i]
            else:
                next_line_freq[index] = np.nan
        next_line_freq = next_line_freq[~np.isnan(next_line_freq)]
        if next_line_freq.size:
            self.spin_frequency_center.setValue(next_line_freq[np.argmin(next_line_freq - init_frequency)])

    def stringify_table_plain_text(self) -> str:
        """
        Convert table cells to string for copying as plain text
        :return: the plain text representation of the table
        """
        text_matrix: List[List[str]] = [[self.model_found_lines.formatted_item(row, column)
                                         for column in range(self.model_found_lines.columnCount())]
                                        for row in range(self.model_found_lines.rowCount(available_count=True))]
        row_texts: List[str]
        text: List[str] = [self.settings.csv_separator.join(row_texts) for row_texts in text_matrix]
        return self.settings.line_end.join(text)

    def stringify_table_html(self) -> str:
        """
        Convert table cells to string for copying as rich text
        :return: the rich text representation of the table
        """
        text_matrix: List[List[str]] = [[('<td>' + self.model_found_lines.formatted_item(row, column) + '</td>')
                                         for column in range(self.model_found_lines.columnCount())]
                                        for row in range(self.model_found_lines.rowCount(available_count=True))]
        row_texts: List[str]
        text: List[str] = [('<tr>' + self.settings.csv_separator.join(row_texts) + '</tr>')
                           for row_texts in text_matrix]
        text.insert(0, '<table>')
        text.append('</table>')
        return self.settings.line_end.join(text)

    def copy_found_lines(self):
        copy_to_clipboard(self.stringify_table_plain_text(), self.stringify_table_html(), Qt.RichText)

    def save_found_lines(self):
        filename, _filter = self.save_file_dialog(_filter='CSV (*.csv);;XLSX (*.xlsx)')
        if not filename:
            return
        filename_parts: Tuple[str, str] = os.path.splitext(filename)
        x: np.ndarray = self.model_found_lines.all_data[:, 0] * 1e-6
        y: np.ndarray = self.model_found_lines.all_data[:, 1]
        data: np.ndarray = np.vstack((x, y)).transpose()
        if 'CSV' in _filter:
            if filename_parts[1] != '.csv':
                filename += '.csv'
            sep: str = self.settings.csv_separator
            # noinspection PyTypeChecker
            np.savetxt(filename, data,
                       delimiter=sep,
                       header=sep.join(('frequency', 'voltage')) + '\n' + sep.join(('MHz', 'mV')),
                       fmt='%s')
        elif 'XLSX' in _filter:
            if filename_parts[1] != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                df: pd.DataFrame = pd.DataFrame(data)
                df.to_excel(writer, index=False, header=['Frequency [MHz]', 'Voltage [mV]'],
                            sheet_name=self._plot_line.name() or 'Sheet1')

    def clear_found_lines(self):
        self.automatically_found_lines.clear()
        self.user_found_lines.clear()
        self.model_found_lines.clear()
        self.plot_toolbar.copy_trace_action.setEnabled(False)
        self.plot_toolbar.save_trace_action.setEnabled(False)
        self.plot_toolbar.clear_trace_action.setEnabled(False)
        self._canvas.replot()

    def clear(self):
        self._plot_line.clear()
        self.clear_found_lines()
        if self.legend_item is not None:
            self.legend_item.clear()
            # self._legend.setVisible(False)
        self.plot_toolbar.trace_action.setChecked(False)
        self.plot_toolbar.clear_action.setEnabled(False)
        self.plot_toolbar.differentiate_action.setEnabled(False)
        self.plot_toolbar.save_data_action.setEnabled(False)
        self.plot_toolbar.copy_figure_action.setEnabled(False)
        self.plot_toolbar.save_figure_action.setEnabled(False)
        self.plot_toolbar.trace_action.setEnabled(False)
        self.plot_toolbar.copy_trace_action.setEnabled(False)
        self.plot_toolbar.save_trace_action.setEnabled(False)
        self.plot_toolbar.clear_trace_action.setEnabled(False)
        self.plot_toolbar.configure_action.setEnabled(False)
        self._canvas.replot()

    def update_legend(self):
        if self.legend_item is not None:
            self.legend_item.clear()
            if self._plot_line.name():
                self.legend_item.addItem(self._plot_line, self._plot_line.name())
            self.legend.setMinimumWidth(self.legend_item.boundingRect().width())

    def load_data(self):
        filename: str
        _filter: str
        _formats: List[str] = [
            'PSK Spectrometer (*.csv *.scandat)',
            'Fast Sweep Spectrometer (*.fmd)',
        ]
        filename, _filter = self.open_file_dialog(_filter=';;'.join(_formats))
        y: np.ndarray
        x: np.ndarray
        if filename.casefold().endswith('.scandat'):
            fn: str = os.path.splitext(filename)[0]
            x, y = load_data_scandat(filename)
            if x.size and y.size:
                self._data_mode = self.PSK_DATA_MODE
        elif filename.casefold().endswith(('.csv', '.conf')):
            fn: str = os.path.splitext(filename)[0]
            x, y = load_data_csv(filename)
            if x.size and y.size:
                self._data_mode = self.PSK_DATA_MODE
        elif filename.casefold().endswith(('.fmd', '.frd')):
            fn: str = os.path.splitext(filename)[0]
            x, y = load_data_fs(filename)
            if x.size and y.size:
                self._data_mode = self.FS_DATA_MODE
        else:
            return

        if x.size and y.size:
            new_label: str = os.path.split(fn)[-1]

            self._plot_line.setData(x, y, name=new_label)

            min_frequency: float = x[0]
            max_frequency: float = x[-1]
            min_voltage: float = np.min(y)
            max_voltage: float = np.max(y)

            self._ignore_scale_change = True
            self.figure.setXRange(min_frequency, max_frequency)
            self.figure.setYRange(min_voltage, max_voltage)
            self._ignore_scale_change = False

            self.update_legend()

            self.plot_toolbar.clear_action.setEnabled(True)
            self.plot_toolbar.differentiate_action.setEnabled(True)
            self.plot_toolbar.save_data_action.setEnabled(True)
            self.plot_toolbar.copy_figure_action.setEnabled(True)
            self.plot_toolbar.save_figure_action.setEnabled(True)
            self.plot_toolbar.trace_action.setEnabled(True)
            self.plot_toolbar.configure_action.setEnabled(True)

            self.on_data_loaded((min_frequency, max_frequency,
                                 min_voltage, max_voltage))

    @property
    def trace_mode(self):
        return self.plot_toolbar.trace_action.isChecked()

    def actions_off(self):
        self.plot_toolbar.trace_action.setChecked(False)

    def calculate_second_derivative(self):
        x: np.ndarray = self._plot_line.xData
        y: np.ndarray = self._plot_line.yData
        step: int = round(self.settings.jump / ((x[-1] - x[0]) / (x.size - 1)))
        y = y[step:-step] - (y[2 * step:] + y[:-2 * step]) / 2.
        x = x[step:-step]
        self._plot_line.setData(x, y)

    def save_data(self):
        if self._plot_line.yData is None:
            return
        filename, _filter = self.save_file_dialog(_filter='CSV (*.csv);;XLSX (*.xlsx)')
        if not filename:
            return
        filename_parts: Tuple[str, str] = os.path.splitext(filename)
        x: np.ndarray = self._plot_line.xData
        y: np.ndarray = self._plot_line.yData
        max_mark: float
        min_mark: float
        min_mark, max_mark = self._canvas.axes['bottom']['item'].range
        good: np.ndarray = (min_mark <= x & x <= max_mark)
        x = x[good]
        y = y[good]
        del good
        data: np.ndarray = np.vstack((x * 1e-6, y)).transpose()
        if 'CSV' in _filter:
            if filename_parts[1] != '.csv':
                filename += '.csv'
            sep: str = self.settings.csv_separator
            # noinspection PyTypeChecker
            np.savetxt(filename, data,
                       delimiter=sep,
                       header=sep.join(('frequency', 'voltage')) + '\n' + sep.join(('MHz', 'mV')),
                       fmt='%s')
        elif 'XLSX' in _filter:
            if filename_parts[1] != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                df: pd.DataFrame = pd.DataFrame(data)
                df.to_excel(writer, index=False, header=['Frequency [MHz]', 'Voltage [mV]'],
                            sheet_name=self._plot_line.name() or 'Sheet1')

    def copy_figure(self):
        # TODO: add legend to the figure to save
        import pyqtgraph.exporters
        exporter = pg.exporters.ImageExporter(self._canvas)
        self._crosshair_h_line.setPos(np.nan)
        self._crosshair_v_line.setPos(np.nan)
        exporter.export(copy=True)

    def save_figure(self):
        # TODO: add legend to the figure to save
        import pyqtgraph.exporters
        exporter = pg.exporters.ImageExporter(self._canvas)
        _filter: str = 'Image files (' + ' '.join(exporter.getSupportedImageFormats()) + ')'
        filename, _filter = self.save_file_dialog(_filter=_filter)
        if not filename:
            return
        self._crosshair_h_line.setPos(np.nan)
        self._crosshair_v_line.setPos(np.nan)
        exporter.export(filename)

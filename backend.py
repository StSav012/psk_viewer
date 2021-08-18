﻿# -*- coding: utf-8 -*-

import os
from typing import Final, Iterable, List, Optional, Tuple, cast

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import pyqtgraph as pg  # type: ignore
import pyqtgraph.exporters  # type: ignore
from PySide6.QtCore import QByteArray, QCoreApplication, QItemSelectionModel, QModelIndex, \
    QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QAction, QBrush, QPalette, QPen, QScreen
from PySide6.QtWidgets import QHeaderView, QMessageBox
from pyqtgraph import PlotWidget
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent  # type: ignore

import detection
from gui import GUI
from preferences import Preferences
from toolbar import NavigationToolbar
from utils import copy_to_clipboard, load_data_csv, load_data_fs, load_data_scandat, resource_path, \
    superscript_number

_translate = QCoreApplication.translate

pg.ViewBox.suggestPadding = lambda *_: 0.0


def tick_strings(self: pg.AxisItem, values: Iterable[float], scale: float, spacing: float) -> List[str]:
    """ improve formatting of `AxisItem.tickStrings` """

    if self.logMode:
        return cast(List[str], self.logTickStrings(values, scale, spacing))

    places: int = max(0, int(np.ceil(-np.log10(spacing * scale))))
    strings: List[str] = []
    v: float
    for v in values:
        vs: float = v * scale
        v_str: str
        if abs(vs) < .001 or abs(vs) >= 10000:
            v_str = f'{vs:g}'.casefold()
            while 'e-0' in v_str:
                v_str = v_str.replace('e-0', 'e-')
            v_str = v_str.replace('+', '')
            if 'e' in v_str:
                e_pos: int = v_str.find('e')
                man: str = v_str[:e_pos]
                exp: str = superscript_number(v_str[e_pos + 1:])
                v_str = man + '×10' + exp
            v_str = v_str.replace('-', '−')
        else:
            v_str = f'{vs:0.{places}f}'
        strings.append(v_str)
    return strings


pg.AxisItem.tickStrings = tick_strings


class PlotDataItem(pg.PlotDataItem):  # type: ignore
    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        super().__init__(*args, **kwargs)

        self.voltage_data: np.ndarray = np.empty(0)
        self.gamma_data: np.ndarray = np.empty(0)


class App(GUI):
    PSK_DATA_MODE: Final[int] = 1
    PSK_WITH_JUMP_DATA_MODE: Final[int] = 2
    FS_DATA_MODE: Final[int] = -1

    _GAMMA_DATA: Final[str] = 'gamma_data'  # should be the same as in class `PlotDataItem`
    _VOLTAGE_DATA: Final[str] = 'voltage_data'  # should be the same as in class `PlotDataItem`

    def __init__(self, filename: str = '', flags: Qt.WindowFlags = Qt.WindowFlags()) -> None:
        super().__init__(flags=flags)

        self._data_mode: int = 0

        self._is_dark: bool = self.palette().color(QPalette.Window).lightness() < 128

        self.legend_item: pg.LegendItem = pg.LegendItem(offset=(0, 0))
        self.toolbar: NavigationToolbar = NavigationToolbar(self, parameters_icon='configure')
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self._canvas: pg.PlotItem = self.figure.getPlotItem()
        self._view_all_action: QAction = QAction()

        self._plot_line: PlotDataItem = self.figure.plot(np.empty(0), name='')
        self._plot_line.voltage_data = np.empty(0)
        self._plot_line.gamma_data = np.empty(0)

        self._ignore_scale_change: bool = False

        self.model_signal: np.ndarray
        try:
            self.model_signal = pd.read_csv(resource_path('averaged fs signal filtered.csv')).values.ravel()
        except (OSError, BlockingIOError):
            self.model_signal = np.empty(0)
            self.box_find_lines.hide()
        self.box_find_lines.setDisabled(True)
        self.user_found_lines: PlotDataItem = self._canvas.scatterPlot(np.empty(0), symbol='o', pxMode=True)
        self.automatically_found_lines: PlotDataItem = self._canvas.scatterPlot(np.empty(0), symbol='o', pxMode=True)
        self.user_found_lines.voltage_data = np.empty(0)
        self.user_found_lines.gamma_data = np.empty(0)
        self.automatically_found_lines.voltage_data = np.empty(0)
        self.automatically_found_lines.gamma_data = np.empty(0)

        self._data_type: str = self._VOLTAGE_DATA

        # cross hair
        self._crosshair_v_line: pg.InfiniteLine = pg.InfiniteLine(angle=90, movable=False)
        self._crosshair_h_line: pg.InfiniteLine = pg.InfiniteLine(angle=0, movable=False)

        self._cursor_balloon: pg.TextItem = pg.TextItem(color='#ccc' if self._is_dark else '#333')
        self.figure.addItem(self._cursor_balloon)

        self._mouse_moved_signal_proxy: pg.SignalProxy = pg.SignalProxy(self.figure.scene().sigMouseMoved,
                                                                        rateLimit=10, slot=self.on_mouse_moved)
        self._axis_range_changed_signal_proxy: pg.SignalProxy = pg.SignalProxy(self.figure.sigRangeChanged,
                                                                               rateLimit=20, slot=self.on_lim_changed)

        self.setup_ui()

        self.load_config()

        self.setup_ui_actions()

        if filename and os.path.exists(filename):
            if self.load_data(filename):
                self.set_config_value('open', 'location', os.path.split(filename)[0])

    def setup_ui(self) -> None:
        ax: pg.AxisItem
        label: str
        if self._is_dark:
            self.figure.setBackground(QBrush(pg.mkColor(0, 0, 0)))
            for label, ax_d in self._canvas.axes.items():
                ax = ax_d['item']
                ax.setPen('d')
                ax.setTextPen('d')
        else:
            self.figure.setBackground(QBrush(pg.mkColor(255, 255, 255)))
            for label, ax_d in self._canvas.axes.items():
                ax = ax_d['item']
                ax.setPen('k')
                ax.setTextPen('k')

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
        self.hide_cursors()

        self.set_plot_line_appearance()
        self.set_marks_appearance()
        self.set_crosshair_lines_appearance()

        # customize menu
        titles_to_leave: List[str] = [
            self._canvas.ctrl.alphaGroup.parent().title(),
            self._canvas.ctrl.gridGroup.parent().title(),
        ]
        action: QAction
        for action in self._canvas.ctrlMenu.actions():
            if action.text() not in titles_to_leave:
                self._canvas.ctrlMenu.removeAction(action)
        self._canvas.vb.menu = self._canvas.ctrlMenu
        self._canvas.ctrlMenu = None
        self._canvas.vb.menu.addAction(self._view_all_action)
        self._canvas.ctrl.autoAlphaCheck.setChecked(False)
        self._canvas.ctrl.autoAlphaCheck.hide()
        self.figure.sceneObj.contextMenu = None

        self.translate_ui()

    def translate_ui(self) -> None:
        self.figure.setLabel('bottom',
                             text=_translate("plot axes labels", 'Frequency'),
                             units=_translate('unit', 'Hz'))
        self.figure.setLabel('left',
                             text=_translate("plot axes labels", 'Voltage'),
                             units=_translate('unit', 'V'))

        self.toolbar.open_action.setIconText(_translate("plot toolbar action", "Open"))
        self.toolbar.open_action.setToolTip(_translate("plot toolbar action", "Load spectrometer data"))
        self.toolbar.clear_action.setIconText(_translate("plot toolbar action", "Clear"))
        self.toolbar.clear_action.setToolTip(_translate("plot toolbar action", "Clear lines and markers"))
        self.toolbar.differentiate_action.setIconText(_translate("plot toolbar action",
                                                                 "Calculate second derivative"))
        self.toolbar.differentiate_action.setToolTip(_translate("plot toolbar action",
                                                                "Calculate finite-step second derivative"))
        self.toolbar.switch_data_action.setIconText(_translate("plot toolbar action", "Show Absorption"))
        self.toolbar.switch_data_action.setToolTip(_translate("plot toolbar action",
                                                              "Switch Y data between absorption and voltage"))
        self.toolbar.save_data_action.setIconText(_translate("plot toolbar action", "Save Data"))
        self.toolbar.save_data_action.setToolTip(_translate("plot toolbar action", "Export the visible data"))
        self.toolbar.copy_figure_action.setIconText(_translate("plot toolbar action", "Copy Figure"))
        self.toolbar.copy_figure_action.setToolTip(_translate("plot toolbar action", "Copy the plot as an image"))
        self.toolbar.save_figure_action.setIconText(_translate("plot toolbar action", "Save Figure"))
        self.toolbar.save_figure_action.setToolTip(_translate("plot toolbar action", "Save the plot as an image"))
        self.toolbar.trace_action.setIconText(_translate("plot toolbar action", "Mark"))
        self.toolbar.trace_action.setToolTip(_translate("plot toolbar action",
                                                        "Mark data points (hold Shift to delete)"))
        self.toolbar.copy_trace_action.setIconText(_translate("plot toolbar action", "Copy Marked"))
        self.toolbar.copy_trace_action.setToolTip(_translate("plot toolbar action",
                                                             "Copy marked points values into clipboard"))
        self.toolbar.save_trace_action.setIconText(_translate("plot toolbar action", "Save Marked"))
        self.toolbar.save_trace_action.setToolTip(_translate("plot toolbar action", "Save marked points values"))
        self.toolbar.clear_trace_action.setIconText(_translate("plot toolbar action", "Clear Marked"))
        self.toolbar.clear_trace_action.setToolTip(_translate("plot toolbar action", "Clear marked points"))
        self.toolbar.configure_action.setIconText(_translate("plot toolbar action", "Configure"))
        self.toolbar.configure_action.setToolTip(_translate("plot toolbar action", "Edit parameters"))

        self.toolbar.parameters_title = _translate('plot config window title', 'Figure options')

        self.toolbar.add_shortcuts_to_tooltips()

        self._view_all_action.setText(_translate("plot context menu action", "View All"))
        self._canvas.ctrl.alphaGroup.parent().setTitle(_translate("plot context menu action", "Alpha"))
        self._canvas.ctrl.gridGroup.parent().setTitle(_translate("plot context menu action", "Grid"))
        self._canvas.ctrl.xGridCheck.setText(_translate("plot context menu action", "Show X Grid"))
        self._canvas.ctrl.yGridCheck.setText(_translate("plot context menu action", "Show Y Grid"))
        self._canvas.ctrl.label.setText(_translate("plot context menu action", "Opacity"))
        self._canvas.ctrl.alphaGroup.setTitle(_translate("plot context menu action", "Alpha"))
        self._canvas.ctrl.autoAlphaCheck.setText(_translate("plot context menu action", "Auto"))

        self._canvas.vb.menu.setTitle(_translate('menu', 'Plot Options'))

    def load_config(self) -> None:
        self._loading = True
        # common settings
        if self.settings.contains('windowGeometry'):
            self.restoreGeometry(cast(QByteArray, self.settings.value('windowGeometry', QByteArray())))
        else:
            window_frame: QRect = self.frameGeometry()
            desktop_center: QPoint = QScreen().availableGeometry().center()
            window_frame.moveCenter(desktop_center)
            self.move(window_frame.topLeft())
        self.restoreState(cast(QByteArray, self.settings.value('windowState', QByteArray())))

        self.check_frequency_persists.setChecked(self.get_config_value('frequency', 'persists', False, bool))
        self.check_voltage_persists.setChecked(self.get_config_value('voltage', 'persists', False, bool))

        self.spin_threshold.setValue(self.get_config_value('lineSearch', 'threshold', 12.0, float))

        if self.get_config_value('display', 'unit', self._VOLTAGE_DATA, str) == self._GAMMA_DATA:
            self._data_type = self._GAMMA_DATA
        else:
            self._data_type = self._VOLTAGE_DATA
        self.toolbar.switch_data_action.setChecked(self._data_type == self._GAMMA_DATA)
        self.display_gamma_or_voltage()

        self._loading = False
        return

    def setup_ui_actions(self) -> None:
        self.toolbar.open_action.triggered.connect(lambda: cast(None, self.load_data()))
        self.toolbar.clear_action.triggered.connect(self.clear)
        self.toolbar.differentiate_action.triggered.connect(self.calculate_second_derivative)
        self.toolbar.switch_data_action.toggled.connect(self.on_switch_data_action_toggled)
        self.toolbar.save_data_action.triggered.connect(self.save_data)
        self.toolbar.copy_figure_action.triggered.connect(self.copy_figure)
        self.toolbar.save_figure_action.triggered.connect(self.save_figure)
        self.toolbar.copy_trace_action.triggered.connect(self.copy_found_lines)
        self.toolbar.save_trace_action.triggered.connect(self.save_found_lines)
        self.toolbar.clear_trace_action.triggered.connect(self.clear_found_lines)
        self.toolbar.configure_action.triggered.connect(self.edit_parameters)

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
        self.button_clear_lines.clicked.connect(self.clear_automatically_found_lines)
        self.button_prev_line.clicked.connect(self.prev_found_line)
        self.button_next_line.clicked.connect(self.next_found_line)

        self.model_found_lines.modelReset.connect(self.adjust_table_columns)  # type: ignore

        self.table_found_lines.doubleClicked.connect(self.on_table_cell_double_clicked)

        line: PlotDataItem
        for line in (self.automatically_found_lines, self.user_found_lines):
            line.sigPointsClicked.connect(self.on_points_clicked)

        self._view_all_action.triggered.connect(lambda: cast(None, self._canvas.vb.autoRange(padding=0.0)))

        self.figure.sceneObj.sigMouseClicked.connect(self.on_plot_clicked)

    def adjust_table_columns(self) -> None:
        self.model_found_lines.header = (
                [_translate('main window', 'Frequency [MHz]')] +
                ([_translate('main window', 'Voltage [mV]'), _translate('main window', 'Absorption [cm⁻¹ × 10⁻⁶]')]
                 * (self.table_found_lines.horizontalHeader().count() // 2))
        )
        for i in range(self.table_found_lines.horizontalHeader().count()):
            self.table_found_lines.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # change visibility of the found lines table columns
        if self.toolbar.switch_data_action.isChecked():
            self.table_found_lines.hideColumn(1)
            self.table_found_lines.showColumn(2)
        else:
            self.table_found_lines.hideColumn(2)
            self.table_found_lines.showColumn(1)

    def on_xlim_changed(self, xlim: Iterable[float]) -> None:
        min_freq, max_freq = min(xlim), max(xlim)
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

    def on_ylim_changed(self, ylim: Iterable[float]) -> None:
        min_voltage, max_voltage = min(ylim), max(ylim)
        self._loading = True
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self._loading = False
        self.set_voltage_range(lower_value=min_voltage,
                               upper_value=max_voltage)

    def on_points_clicked(self, item: PlotDataItem, points: Iterable[pg.SpotItem], ev: MouseClickEvent) -> None:
        if item.xData is None or item.yData is None:
            return
        if not self.trace_mode:
            return
        if ev.button() != Qt.LeftButton:
            return

        point: pg.SpotItem
        if ev.modifiers() == Qt.ShiftModifier:
            items: np.ndarray = item.scatter.data['item']
            index: np.ndarray = np.full(items.shape, True, np.bool_)
            for point in points:
                index &= (items != point)
            item.setData(item.xData[index], item.yData[index])
            if item.voltage_data.size:
                item.voltage_data = item.voltage_data[index]
            if item.gamma_data.size:
                item.gamma_data = item.gamma_data[index]

            # update the table
            if self.user_found_lines.xData is not None and self.user_found_lines.yData is not None:
                if self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
                    if (self.automatically_found_lines.xData is not None
                            and self.automatically_found_lines.voltage_data.size
                            and self.automatically_found_lines.gamma_data.size):
                        self.model_found_lines.set_data(np.column_stack((
                            np.concatenate((self.automatically_found_lines.xData,
                                            self.user_found_lines.xData)),
                            np.concatenate((self.automatically_found_lines.voltage_data,
                                            self.user_found_lines.voltage_data)),
                            np.concatenate((self.automatically_found_lines.gamma_data,
                                            self.user_found_lines.gamma_data)),
                        )))
                    else:
                        self.model_found_lines.set_data(np.column_stack((
                            self.user_found_lines.xData,
                            self.user_found_lines.voltage_data,
                            self.user_found_lines.gamma_data,
                        )))
                else:
                    if (self.automatically_found_lines.xData is not None
                            and self.automatically_found_lines.voltage_data.size):
                        self.model_found_lines.set_data(np.column_stack((
                            np.concatenate((self.automatically_found_lines.xData, self.user_found_lines.xData)),
                            np.concatenate((self.automatically_found_lines.voltage_data,
                                            self.user_found_lines.voltage_data)),
                        )))
                    else:
                        self.model_found_lines.set_data(np.column_stack((
                            self.user_found_lines.xData,
                            self.user_found_lines.voltage_data,
                        )))
            else:
                if self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
                    if (self.automatically_found_lines.xData is not None
                            and self.automatically_found_lines.voltage_data.size
                            and self.automatically_found_lines.gamma_data.size):
                        self.model_found_lines.set_data(np.column_stack((
                            self.automatically_found_lines.xData,
                            self.automatically_found_lines.voltage_data,
                            self.automatically_found_lines.gamma_data,
                        )))
                    else:
                        self.model_found_lines.clear()
                else:
                    if (self.automatically_found_lines.xData is not None
                            and self.automatically_found_lines.voltage_data.size):
                        self.model_found_lines.set_data(np.column_stack((
                            self.automatically_found_lines.xData,
                            self.automatically_found_lines.voltage_data,
                        )))
                    else:
                        self.model_found_lines.clear()

            self.toolbar.copy_trace_action.setEnabled(not self.model_found_lines.is_empty)
            self.toolbar.save_trace_action.setEnabled(not self.model_found_lines.is_empty)
            self.toolbar.clear_trace_action.setEnabled(not self.model_found_lines.is_empty)

        elif ev.modifiers() == Qt.NoModifier:
            found_lines_frequencies: np.ndarray = self.model_found_lines.all_data[:, 0]
            selected_points: List[int] = [cast(int, np.argmin(np.abs(point.pos().x() - found_lines_frequencies)))
                                          for point in points]
            self.on_points_selected(selected_points)

    def on_button_find_lines_clicked(self) -> None:
        self.status_bar.showMessage(f'Found {self.find_lines(self.spin_threshold.value())} lines')

    def on_mouse_moved(self, event: Tuple[QPointF]) -> None:
        if self._plot_line.xData is None and self._plot_line.yData is None:
            return
        pos: QPointF = event[0]
        if self.figure.sceneBoundingRect().contains(pos):
            point: QPointF = self._canvas.vb.mapSceneToView(pos)
            if self.figure.visibleRange().contains(point):
                self.status_bar.clearMessage()
                self._crosshair_v_line.setPos(point.x())
                self._crosshair_h_line.setPos(point.y())
                self._crosshair_h_line.setVisible(self.settings.show_crosshair)
                self._crosshair_v_line.setVisible(self.settings.show_crosshair)
                self._cursor_x.setVisible(True)
                self._cursor_y.setVisible(True)
                self._cursor_x.setValue(point.x())
                self._cursor_y.setValue(point.y())

                if self.settings.show_coordinates_at_crosshair:
                    self._cursor_balloon.setPos(point)
                    self._cursor_balloon.setHtml(self._cursor_x.text() + '<br>' + self._cursor_y.text())
                    balloon_border: QRectF = self._cursor_balloon.boundingRect()
                    sx: float
                    sy: float
                    sx, sy = self._canvas.vb.viewPixelSize()
                    balloon_width: float = balloon_border.width() * sx
                    balloon_height: float = balloon_border.height() * sy
                    anchor_x: float = 0.0 if point.x() - self.figure.visibleRange().left() < balloon_width else 1.0
                    anchor_y: float = 0.0 if self.figure.visibleRange().bottom() - point.y() < balloon_height else 1.0
                    self._cursor_balloon.setAnchor((anchor_x, anchor_y))
                self._cursor_balloon.setVisible(self.settings.show_coordinates_at_crosshair)
            else:
                self.hide_cursors()
        else:
            self.hide_cursors()

    def on_plot_clicked(self, event: MouseClickEvent) -> None:
        pos: QPointF = event.scenePos()
        if not self.trace_mode:
            return
        if event.modifiers() != Qt.NoModifier or event.button() != Qt.LeftButton:
            return
        if not self.figure.sceneBoundingRect().contains(pos):
            return
        x_span: float = cast(float, np.ptp(self._canvas.axes['bottom']['item'].range))
        y_span: float = cast(float, np.ptp(self._canvas.axes['left']['item'].range))
        point: QPointF = self._canvas.vb.mapSceneToView(pos)
        if self._plot_line.xData is None or not self._plot_line.xData.size:
            return
        distance: np.ndarray = np.min(np.hypot((self._plot_line.xData - point.x()) / x_span,
                                               (self._plot_line.yData - point.y()) / y_span))
        if distance > 0.01:
            return
        closest_point_index: int = cast(int, np.argmin(np.hypot((self._plot_line.xData - point.x()) / x_span,
                                                                (self._plot_line.yData - point.y()) / y_span)))
        if self.user_found_lines.xData is None or self.user_found_lines.yData.size is None:
            self.user_found_lines.setData(
                [self._plot_line.xData[closest_point_index]], [self._plot_line.yData[closest_point_index]]
            )
            if self._plot_line.voltage_data.size > closest_point_index:
                self.user_found_lines.voltage_data = np.array([self._plot_line.voltage_data[closest_point_index]])
            if self._plot_line.gamma_data.size > closest_point_index:
                self.user_found_lines.gamma_data = np.array([self._plot_line.gamma_data[closest_point_index]])
        else:
            # avoid the same point to be marked several times
            if np.any((self.user_found_lines.xData == self._plot_line.xData[closest_point_index])
                      & (self.user_found_lines.yData == self._plot_line.yData[closest_point_index])):
                return
            if (self.automatically_found_lines.xData is not None
                    and self.automatically_found_lines.yData.size is not None
                    and np.any((self.automatically_found_lines.xData == self._plot_line.xData[closest_point_index])
                               & (self.automatically_found_lines.yData == self._plot_line.yData[closest_point_index]))):
                return
            if self._plot_line.voltage_data.size > closest_point_index:
                self.user_found_lines.voltage_data = np.append(self.user_found_lines.voltage_data,
                                                               self._plot_line.voltage_data[closest_point_index])
            if self._plot_line.gamma_data.size > closest_point_index:
                self.user_found_lines.gamma_data = np.append(self.user_found_lines.gamma_data,
                                                             self._plot_line.gamma_data[closest_point_index])

            if self._data_type == self._VOLTAGE_DATA:
                self.user_found_lines.setData(
                    np.append(self.user_found_lines.xData, self._plot_line.xData[closest_point_index]),
                    self.user_found_lines.voltage_data
                )
            elif self._data_type == self._GAMMA_DATA:
                self.user_found_lines.setData(
                    np.append(self.user_found_lines.xData, self._plot_line.xData[closest_point_index]),
                    self.user_found_lines.gamma_data
                )
        if self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
            self.model_found_lines.append_data([self._plot_line.xData[closest_point_index],
                                                self._plot_line.voltage_data[closest_point_index],
                                                self._plot_line.gamma_data[closest_point_index],
                                                ])
        else:
            self.model_found_lines.append_data([self._plot_line.xData[closest_point_index],
                                                self._plot_line.voltage_data[closest_point_index],
                                                ])
        if self.settings.copy_frequency:
            copy_to_clipboard(str(1e-6 * self._plot_line.xData[closest_point_index]))
        self.toolbar.copy_trace_action.setEnabled(True)
        self.toolbar.save_trace_action.setEnabled(True)
        self.toolbar.clear_trace_action.setEnabled(True)

    def on_lim_changed(self, arg: Tuple[PlotWidget, List[List[float]]]) -> None:
        if self._ignore_scale_change:
            return
        rect: List[List[float]] = arg[1]
        xlim: List[float]
        ylim: List[float]
        xlim, ylim = rect
        self._ignore_scale_change = True
        self.on_xlim_changed(xlim)
        self.on_ylim_changed(ylim)
        self._ignore_scale_change = False

    def on_points_selected(self, rows: List[int]) -> None:
        self.table_found_lines.clearSelection()
        sm: QItemSelectionModel = self.table_found_lines.selectionModel()
        row: int
        for row in rows:
            index: QModelIndex = self.model_found_lines.index(row, 0)
            sm.select(index,
                      cast(QItemSelectionModel.SelectionFlags, QItemSelectionModel.Select | QItemSelectionModel.Rows))
            self.table_found_lines.scrollTo(index)

    def spin_frequency_min_changed(self, new_value: float) -> None:
        if self._loading:
            return
        self._loading = True
        self.spin_frequency_max.setMinimum(new_value)
        self.spin_frequency_center.setValue(0.5 * (new_value + self.spin_frequency_max.value()))
        self.spin_frequency_span.setValue(self.spin_frequency_max.value() - new_value)
        self.set_frequency_range(lower_value=new_value, upper_value=self.spin_frequency_max.value())
        self._loading = False

    def spin_frequency_max_changed(self, new_value: float) -> None:
        if self._loading:
            return
        self._loading = True
        self.spin_frequency_min.setMaximum(new_value)
        self.spin_frequency_center.setValue(0.5 * (self.spin_frequency_min.value() + new_value))
        self.spin_frequency_span.setValue(new_value - self.spin_frequency_min.value())
        self.set_frequency_range(lower_value=self.spin_frequency_min.value(), upper_value=new_value)
        self._loading = False

    def spin_frequency_center_changed(self, new_value: float) -> None:
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value()
        min_freq = new_value - 0.5 * freq_span
        max_freq = new_value + 0.5 * freq_span
        self._loading = True
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def spin_frequency_span_changed(self, new_value: float) -> None:
        if self._loading:
            return
        freq_center = self.spin_frequency_center.value()
        min_freq = freq_center - 0.5 * new_value
        max_freq = freq_center + 0.5 * new_value
        self._loading = True
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def button_zoom_x_clicked(self, factor: float) -> None:
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value() * factor
        freq_center = self.spin_frequency_center.value()
        min_freq = freq_center - 0.5 * freq_span
        max_freq = freq_center + 0.5 * freq_span
        self._loading = True
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_span.setValue(freq_span)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def button_move_x_clicked(self, shift: float) -> None:
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value()
        freq_center = self.spin_frequency_center.value() + shift
        min_freq = freq_center - 0.5 * freq_span
        max_freq = freq_center + 0.5 * freq_span
        self._loading = True
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_center.setValue(freq_center)
        self.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def check_frequency_persists_toggled(self, new_value: bool) -> None:
        if self._loading:
            return
        self.set_config_value('frequency', 'persists', new_value)

    def spin_voltage_min_changed(self, new_value: float) -> None:
        if self._loading:
            return
        self._loading = True
        self.spin_voltage_max.setMinimum(new_value)
        self.set_voltage_range(lower_value=new_value, upper_value=self.spin_voltage_max.value())
        self._loading = False

    def spin_voltage_max_changed(self, new_value: float) -> None:
        if self._loading:
            return
        self._loading = True
        self.spin_voltage_min.setMaximum(new_value)
        self.set_voltage_range(lower_value=self.spin_voltage_min.value(), upper_value=new_value)
        self._loading = False

    def button_zoom_y_clicked(self, factor: float) -> None:
        if self._loading:
            return
        min_voltage = self.spin_voltage_min.value()
        max_voltage = self.spin_voltage_max.value()
        voltage_span = abs(max_voltage - min_voltage) * factor
        voltage_center = (max_voltage + min_voltage) * 0.5
        min_voltage = voltage_center - 0.5 * voltage_span
        max_voltage = voltage_center + 0.5 * voltage_span
        self._loading = True
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.set_voltage_range(upper_value=max_voltage, lower_value=min_voltage)
        self._loading = False

    def on_check_voltage_persists_toggled(self, new_value: bool) -> None:
        if self._loading:
            return
        self.set_config_value('voltage', 'persists', new_value)

    def edit_parameters(self) -> None:
        preferences_dialog: Preferences = Preferences(self.settings, self)
        preferences_dialog.exec()
        self.set_plot_line_appearance()
        self.set_marks_appearance()
        self.set_crosshair_lines_appearance()
        if (self._data_mode == self.PSK_DATA_MODE
                and self._plot_line.xData is not None and self._plot_line.xData.size > 1):
            step: int = int(round(self.settings.jump / ((self._plot_line.xData[-1] - self._plot_line.xData[0])
                                                        / (self._plot_line.xData.size - 1))))
            self.toolbar.differentiate_action.setEnabled(step != 0)

    def hide_cursors(self) -> None:
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)
        self._cursor_x.setVisible(False)
        self._cursor_y.setVisible(False)
        self._cursor_balloon.setVisible(False)

    @property
    def line(self) -> PlotDataItem:
        return self._plot_line

    @property
    def label(self) -> Optional[str]:
        return cast(str, self._plot_line.name())

    def set_frequency_range(self, lower_value: float, upper_value: float) -> None:
        self.figure.plotItem.setXRange(lower_value, upper_value, padding=0.0)

    def set_voltage_range(self, lower_value: float, upper_value: float) -> None:
        self.figure.plotItem.setYRange(lower_value, upper_value, padding=0.0)

    def set_plot_line_appearance(self) -> None:
        self._plot_line.setPen(pg.mkPen(self.settings.line_color, width=0.5 * self.settings.line_thickness))
        self._canvas.replot()

    def set_marks_appearance(self) -> None:
        pen: QPen = pg.mkPen(self.settings.mark_pen, width=0.5 * self.settings.mark_pen_thickness)
        brush: QBrush = pg.mkBrush(self.settings.mark_brush)
        self.automatically_found_lines.setSymbolPen(pen)
        self.automatically_found_lines.setSymbolBrush(brush)
        self.automatically_found_lines.setSymbolSize(self.settings.mark_size)
        self.user_found_lines.setSymbolPen(pen)
        self.user_found_lines.setSymbolBrush(brush)
        self.user_found_lines.setSymbolSize(self.settings.mark_size)
        self._canvas.replot()

    def set_crosshair_lines_appearance(self) -> None:
        pen: QPen = pg.mkPen(self.settings.crosshair_lines_color, width=0.5 * self.settings.crosshair_lines_thickness)
        self._crosshair_v_line.setPen(pen)
        self._crosshair_h_line.setPen(pen)
        self._canvas.replot()

    def find_lines(self, threshold: float) -> int:
        if self._data_mode == 0 or self.model_signal.size < 2:
            return 0

        from scipy import interpolate  # type: ignore

        x: Final[np.ndarray] = self._plot_line.xData
        y: Final[np.ndarray] = self._plot_line.yData
        if x.size < 2 or y.size < 2:
            return 0

        found_lines: np.ndarray
        if self._data_mode == self.FS_DATA_MODE:
            # re-scale the signal to the actual frequency mesh
            x_model: np.ndarray = np.arange(self.model_signal.size, dtype=x.dtype) * 0.1
            interpol = interpolate.interp1d(x_model, self.model_signal, kind=2)
            x_model_new: np.ndarray = np.arange(x_model[0], x_model[-1],
                                                x[1] - x[0])
            y_model_new: np.ndarray = interpol(x_model_new)
            found_lines = detection.peaks_positions(x,
                                                    detection.correlation(y_model_new,
                                                                          x,
                                                                          y),
                                                    threshold=1.0 / threshold)
        elif self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
            found_lines = detection.peaks_positions(x,
                                                    y,
                                                    threshold=1.0 / threshold)
        else:
            return 0

        self._ignore_scale_change = True
        if found_lines.size:
            self.automatically_found_lines.setData(x[found_lines],
                                                   y[found_lines])
            self.automatically_found_lines.voltage_data = self._plot_line.voltage_data[found_lines]
            if self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
                self.automatically_found_lines.gamma_data = self._plot_line.gamma_data[found_lines]
            else:
                self.automatically_found_lines.gamma_data = np.empty(0)
        else:
            self.automatically_found_lines.setData(np.empty(0), np.empty(0))
            self.automatically_found_lines.voltage_data = np.empty(0)
            self.automatically_found_lines.gamma_data = np.empty(0)

        # update the table
        if self.user_found_lines.xData is not None and self.user_found_lines.yData is not None:
            if self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
                self.model_found_lines.set_data(np.column_stack((
                    np.concatenate((self.automatically_found_lines.xData, self.user_found_lines.xData)),
                    np.concatenate((self.automatically_found_lines.voltage_data,
                                    self.user_found_lines.voltage_data)),
                    np.concatenate((self.automatically_found_lines.gamma_data, self.user_found_lines.gamma_data)),
                )))
            else:
                self.model_found_lines.set_data(np.column_stack((
                    np.concatenate((self.automatically_found_lines.xData, self.user_found_lines.xData)),
                    np.concatenate((self.automatically_found_lines.voltage_data,
                                    self.user_found_lines.voltage_data)),
                )))
        else:
            if self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
                self.model_found_lines.set_data(np.column_stack((
                    self.automatically_found_lines.xData,
                    self.automatically_found_lines.voltage_data,
                    self.automatically_found_lines.gamma_data,
                )))
            else:
                self.model_found_lines.set_data(np.column_stack((
                    self.automatically_found_lines.xData,
                    self.automatically_found_lines.voltage_data,
                )))

        self.toolbar.copy_trace_action.setEnabled(not self.model_found_lines.is_empty)
        self.toolbar.save_trace_action.setEnabled(not self.model_found_lines.is_empty)
        self.toolbar.clear_trace_action.setEnabled(not self.model_found_lines.is_empty)

        self._ignore_scale_change = False

        return cast(int, found_lines.size)

    def prev_found_line(self) -> None:
        if self.model_signal.size < 2:
            return

        init_frequency: float = self.spin_frequency_center.value()

        prev_line_freq: np.ndarray = np.full(len(self.automatically_found_lines), np.nan)
        index: int
        line: pg.ScatterPlotItem
        for index, line in enumerate(self.automatically_found_lines):
            line_data: np.ndarray = line.getData()[0]
            if line_data is None or not line_data.size:
                continue
            i: int = cast(int, np.searchsorted(line_data, init_frequency, side='right') - 2)
            if 0 <= i < line_data.size and line_data[i] != init_frequency:
                prev_line_freq[index] = line_data[i]
            else:
                prev_line_freq[index] = np.nan
        prev_line_freq = prev_line_freq[~np.isnan(prev_line_freq)]
        if prev_line_freq.size:
            self.spin_frequency_center.setValue(prev_line_freq[np.argmin(init_frequency - prev_line_freq)])

    def next_found_line(self) -> None:
        if self.model_signal.size < 2:
            return

        init_frequency: float = self.spin_frequency_center.value()

        next_line_freq: np.ndarray = np.full(len(self.automatically_found_lines), np.nan)
        index: int
        line: pg.ScatterPlotItem
        for index, line in enumerate(self.automatically_found_lines):
            line_data: np.ndarray = line.getData()[0]
            if line_data is None or not line_data.size:
                continue
            i: int = cast(int, np.searchsorted(line_data, init_frequency, side='left') + 1)
            if i < line_data.size and line_data[i] != init_frequency:
                next_line_freq[index] = line_data[i]
            else:
                next_line_freq[index] = np.nan
        next_line_freq = next_line_freq[~np.isnan(next_line_freq)]
        if next_line_freq.size:
            self.spin_frequency_center.setValue(next_line_freq[np.argmin(next_line_freq - init_frequency)])

    def on_table_cell_double_clicked(self, index: QModelIndex) -> None:
        self.spin_frequency_center.setValue(self.model_found_lines.item(index.row(), 0))

    def stringify_table_plain_text(self, whole_table: bool = True) -> str:
        """
        Convert selected cells to string for copying as plain text
        :return: the plain text representation of the selected table lines
        """
        text_matrix: List[List[str]]
        if whole_table:
            text_matrix = [[self.model_found_lines.formatted_item(row, column)
                            for column in range(self.model_found_lines.columnCount())
                            if not self.table_found_lines.isColumnHidden(column)]
                           for row in range(self.model_found_lines.rowCount(available_count=True))]
        else:
            si: QModelIndex
            rows: List[int] = sorted(list(set(si.row() for si in self.table_found_lines.selectedIndexes())))
            cols: List[int] = sorted(list(set(si.column() for si in self.table_found_lines.selectedIndexes())))
            text_matrix = [['' for _ in range(len(cols))]
                           for _ in range(len(rows))]
            for si in self.table_found_lines.selectedIndexes():
                text_matrix[rows.index(si.row())][cols.index(si.column())] = \
                    self.model_found_lines.formatted_item(si.row(), si.column())
        row_texts: List[str]
        text: List[str] = [self.settings.csv_separator.join(row_texts) for row_texts in text_matrix]
        return self.settings.line_end.join(text)

    def stringify_table_html(self, whole_table: bool = True) -> str:
        """
        Convert selected cells to string for copying as rich text
        :return: the rich text representation of the selected table lines
        """
        text_matrix: List[List[str]]
        if whole_table:
            text_matrix = [[('<td>' + self.model_found_lines.formatted_item(row, column) + '</td>')
                            for column in range(self.model_found_lines.columnCount())
                            if not self.table_found_lines.isColumnHidden(column)]
                           for row in range(self.model_found_lines.rowCount(available_count=True))]
        else:
            si: QModelIndex
            rows: List[int] = sorted(list(set(si.row() for si in self.table_found_lines.selectedIndexes())))
            cols: List[int] = sorted(list(set(si.column() for si in self.table_found_lines.selectedIndexes())))
            text_matrix = [['' for _ in range(len(cols))]
                           for _ in range(len(rows))]
            for si in self.table_found_lines.selectedIndexes():
                text_matrix[rows.index(si.row())][cols.index(si.column())] = \
                    '<td>' + self.model_found_lines.formatted_item(si.row(), si.column()) + '</td>'
        row_texts: List[str]
        text: List[str] = [('<tr>' + self.settings.csv_separator.join(row_texts) + '</tr>')
                           for row_texts in text_matrix]
        text.insert(0, '<table>')
        text.append('</table>')
        return self.settings.line_end.join(text)

    def copy_found_lines(self) -> None:
        copy_to_clipboard(self.stringify_table_plain_text(), self.stringify_table_html(), Qt.RichText)

    def save_found_lines(self) -> None:
        filename, _filter = self.save_file_dialog(_filter='CSV (*.csv);;XLSX (*.xlsx)')
        if not filename:
            return

        filename_parts: Tuple[str, str] = os.path.splitext(filename)
        f: np.ndarray = self.model_found_lines.all_data[:, 0] * 1e-6
        v: np.ndarray = self.model_found_lines.all_data[:, 1] * 1e3
        g: np.ndarray = self.model_found_lines.all_data[:, 2]
        data: np.ndarray = np.vstack((f, v, g)).transpose()
        if 'CSV' in _filter:
            if filename_parts[1] != '.csv':
                filename += '.csv'
            sep: str = self.settings.csv_separator
            # noinspection PyTypeChecker
            np.savetxt(filename, data,
                       delimiter=sep,
                       header=(sep.join((_translate("plot axes labels", 'Frequency'),
                                         _translate("plot axes labels", 'Voltage'),
                                         _translate("plot axes labels", 'Absorption'))) + '\n'
                               + sep.join((pg.siScale(1e6)[1] + _translate('unit', 'Hz'),
                                           pg.siScale(1e-3)[1] + _translate('unit', 'V'),
                                           _translate('unit', 'cm⁻¹')))),
                       fmt=('%.3f', '%.6f', '%.6e'), encoding='utf-8')
        elif 'XLSX' in _filter:
            if filename_parts[1] != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                df: pd.DataFrame = pd.DataFrame(data)
                df.to_excel(writer, index=False,
                            header=[_translate('main window', 'Frequency [MHz]'),
                                    _translate('main window', 'Voltage [mV]'),
                                    _translate('main window', 'Absorption [cm⁻¹]')],
                            sheet_name=self._plot_line.name() or _translate('workbook', 'Sheet1'))

    def clear_automatically_found_lines(self) -> None:
        self.automatically_found_lines.clear()
        self._canvas.replot()

        if self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE):
            self.model_found_lines.set_data(np.column_stack((
                self.user_found_lines.xData,
                self.user_found_lines.voltage_data,
                self.user_found_lines.gamma_data,
            )))
        else:
            self.model_found_lines.set_data(np.column_stack((
                self.user_found_lines.xData,
                self.user_found_lines.voltage_data,
            )))
        self.toolbar.copy_trace_action.setEnabled(True)
        self.toolbar.save_trace_action.setEnabled(True)
        self.toolbar.clear_trace_action.setEnabled(True)

    def clear_found_lines(self) -> None:
        self.automatically_found_lines.clear()
        self.user_found_lines.clear()
        self.model_found_lines.clear()
        self.toolbar.copy_trace_action.setEnabled(False)
        self.toolbar.save_trace_action.setEnabled(False)
        self.toolbar.clear_trace_action.setEnabled(False)
        self._canvas.replot()

    def clear(self) -> None:
        close: QMessageBox = QMessageBox()
        close.setText(_translate('main window', 'Are you sure?'))
        close.setIcon(QMessageBox.Question)
        close.setWindowIcon(self.windowIcon())
        close.setWindowTitle(self.windowTitle())
        close.setStandardButtons(cast(QMessageBox.StandardButtons,
                                      QMessageBox.Yes | QMessageBox.Cancel))
        if close.exec() != QMessageBox.Yes:
            return

        self._plot_line.clear()
        self.clear_found_lines()
        if self.legend_item is not None:
            self.legend_item.clear()
            # self._legend.setVisible(False)
        self.toolbar.trace_action.setChecked(False)
        self.toolbar.clear_action.setEnabled(False)
        self.toolbar.differentiate_action.setEnabled(False)
        self.toolbar.save_data_action.setEnabled(False)
        self.toolbar.copy_figure_action.setEnabled(False)
        self.toolbar.save_figure_action.setEnabled(False)
        self.toolbar.trace_action.setEnabled(False)
        self.toolbar.copy_trace_action.setEnabled(False)
        self.toolbar.save_trace_action.setEnabled(False)
        self.toolbar.clear_trace_action.setEnabled(False)
        self.box_find_lines.setEnabled(False)
        self._cursor_balloon.setVisible(False)
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)
        self._cursor_x.setVisible(True)
        self._cursor_y.setVisible(True)
        self._canvas.replot()

    def update_legend(self) -> None:
        self.legend_item.clear()
        if self._plot_line.name():
            self.legend_item.addItem(self._plot_line, self._plot_line.name())
        self.legend.setMinimumWidth(self.legend_item.boundingRect().width())

    def load_data(self, filename: str = '') -> bool:
        if not filename:
            _filter: str
            _formats: List[str] = [
                'PSK Spectrometer (*.conf *.scandat)',
                'Fast Sweep Spectrometer (*.fmd)',
            ]
            filename, _filter = self.open_file_dialog(_filter=';;'.join(_formats))
        v: np.ndarray
        f: np.ndarray
        g: np.ndarray = np.empty(0)
        jump: float
        fn: str
        if filename.casefold().endswith('.scandat'):
            fn = os.path.splitext(filename)[0]
            f, v, g, jump = load_data_scandat(filename, self)
            if f.size and v.size:
                self.settings.display_processing = True
                if jump > 0.0:
                    self._data_mode = self.PSK_WITH_JUMP_DATA_MODE
                else:
                    self._data_mode = self.PSK_DATA_MODE
        elif filename.casefold().endswith(('.csv', '.conf')):
            fn = os.path.splitext(filename)[0]
            f, v, g, jump = load_data_csv(filename)
            if f.size and v.size:
                self.settings.display_processing = True
                if jump > 0.0:
                    self._data_mode = self.PSK_WITH_JUMP_DATA_MODE
                else:
                    self._data_mode = self.PSK_DATA_MODE
        elif filename.casefold().endswith(('.fmd', '.frd')):
            fn = os.path.splitext(filename)[0]
            f, v = load_data_fs(filename)
            if f.size and v.size:
                self.settings.display_processing = False
                self._data_mode = self.FS_DATA_MODE
        else:
            return False

        if not (f.size and v.size):
            return False

        new_label: str = os.path.split(fn)[-1]

        if self._data_mode == self.FS_DATA_MODE:
            self.toolbar.switch_data_action.setChecked(False)

        self._plot_line.setData(f,
                                (g if self.toolbar.switch_data_action.isChecked() else v),
                                name=new_label)
        self._plot_line.gamma_data = g
        self._plot_line.voltage_data = v

        min_frequency: float = f[0]
        max_frequency: float = f[-1]

        self.update_legend()

        self.toolbar.clear_action.setEnabled(True)
        self.toolbar.differentiate_action.setEnabled(self._data_mode == self.PSK_DATA_MODE)
        self.toolbar.switch_data_action.setEnabled(self._data_mode in (self.PSK_DATA_MODE,
                                                                       self.PSK_WITH_JUMP_DATA_MODE))
        self.toolbar.save_data_action.setEnabled(True)
        self.toolbar.copy_figure_action.setEnabled(True)
        self.toolbar.save_figure_action.setEnabled(True)
        self.toolbar.trace_action.setEnabled(True)
        self.box_find_lines.setEnabled(bool(self.model_signal.size))

        self._loading = True
        self.spin_frequency_min.setMaximum(max(max_frequency, self.spin_frequency_min.value()))
        self.spin_frequency_max.setMinimum(min(min_frequency, self.spin_frequency_max.value()))
        if not self.check_frequency_persists.isChecked():
            self.spin_frequency_min.setValue(min_frequency)
            self.spin_frequency_max.setValue(max_frequency)
            self.spin_frequency_span.setValue(max_frequency - min_frequency)
            self.spin_frequency_center.setValue(0.5 * (max_frequency + min_frequency))
        self._loading = False

        self.display_gamma_or_voltage()

        self.set_frequency_range(lower_value=self.spin_frequency_min.value(),
                                 upper_value=self.spin_frequency_max.value())
        self.set_voltage_range(lower_value=self.spin_voltage_min.value(),
                               upper_value=self.spin_voltage_max.value())

        return True

    @property
    def trace_mode(self) -> bool:
        return self.toolbar.trace_action.isChecked()

    def actions_off(self) -> None:
        self.toolbar.trace_action.setChecked(False)

    def calculate_second_derivative(self) -> None:
        self.clear_found_lines()
        x: np.ndarray = self._plot_line.xData
        step: int = int(round(self.settings.jump / ((x[-1] - x[0]) / (x.size - 1))))
        self._plot_line.voltage_data = (self._plot_line.voltage_data[step:-step]
                                        - (self._plot_line.voltage_data[2 * step:]
                                           + self._plot_line.voltage_data[:-2 * step]) / 2.)
        self._plot_line.gamma_data = (self._plot_line.gamma_data[step:-step]
                                      - (self._plot_line.gamma_data[2 * step:]
                                         + self._plot_line.gamma_data[:-2 * step]) / 2.)
        self._plot_line.xData = x[step:-step]
        self.toolbar.differentiate_action.setEnabled(False)
        self._data_mode = self.PSK_WITH_JUMP_DATA_MODE
        self.display_gamma_or_voltage()

    def on_switch_data_action_toggled(self, new_state: bool) -> None:
        self._data_type = self._GAMMA_DATA if new_state else self._VOLTAGE_DATA
        self.set_config_value('display', 'unit', self._data_type)
        self.display_gamma_or_voltage(new_state)

    def display_gamma_or_voltage(self, display_gamma: Optional[bool] = None) -> None:
        if display_gamma is None:
            display_gamma = self.toolbar.switch_data_action.isChecked()

        if display_gamma:
            if self._plot_line.xData is not None and self._plot_line.gamma_data.size:  # something is loaded
                self._plot_line.setData(self._plot_line.xData, self._plot_line.gamma_data)

                self._loading = True
                min_gamma: float = np.min(self._plot_line.gamma_data)
                max_gamma: float = np.max(self._plot_line.gamma_data)
                if not self.check_voltage_persists.isChecked():
                    self.on_ylim_changed((min_gamma, max_gamma))
                self.spin_voltage_min.setMaximum(max(max_gamma, self.spin_voltage_min.value()))
                self.spin_voltage_max.setMinimum(min(min_gamma, self.spin_voltage_max.value()))
                self._loading = False

            if (self.automatically_found_lines.xData is not None
                    and self.automatically_found_lines.gamma_data.size):  # something is marked
                self.automatically_found_lines.setData(self.automatically_found_lines.xData,
                                                       self.automatically_found_lines.gamma_data)
            if (self.user_found_lines.xData is not None
                    and self.user_found_lines.gamma_data.size):  # something is marked
                self.user_found_lines.setData(self.user_found_lines.xData, self.user_found_lines.gamma_data)
        else:
            if self._plot_line.xData is not None and self._plot_line.voltage_data.size:  # something is loaded
                self._plot_line.setData(self._plot_line.xData, self._plot_line.voltage_data)

                self._loading = True
                min_voltage: float = np.min(self._plot_line.voltage_data)
                max_voltage: float = np.max(self._plot_line.voltage_data)
                if not self.check_voltage_persists.isChecked():
                    self.on_ylim_changed((min_voltage, max_voltage))
                self.spin_voltage_min.setMaximum(max(max_voltage, self.spin_voltage_min.value()))
                self.spin_voltage_max.setMinimum(min(min_voltage, self.spin_voltage_max.value()))
                self._loading = False

            if (self.automatically_found_lines.xData is not None
                    and self.automatically_found_lines.voltage_data.size):  # something is marked
                self.automatically_found_lines.setData(self.automatically_found_lines.xData,
                                                       self.automatically_found_lines.voltage_data)
            if (self.user_found_lines.xData is not None
                    and self.user_found_lines.voltage_data.size):  # something is marked
                self.user_found_lines.setData(self.user_found_lines.xData, self.user_found_lines.voltage_data)

        a: pg.AxisItem = self._canvas.getAxis('left')
        if display_gamma:
            self.check_voltage_persists.setText(_translate('main window', 'Keep absorption range'))

            a.enableAutoSIPrefix(False)
            a.setLabel(text=_translate("plot axes labels", 'Absorption'),
                       units=_translate('unit', 'cm<sup>−1</sup>'))
            a.scale = 1.0
            a.autoSIPrefixScale = 1.0

            self._cursor_y.suffix = _translate('unit', 'cm<sup>−1</sup>')
            self._cursor_y.siPrefix = False
            self._cursor_y.setFormatStr('{mantissa:.{decimals}f}×10<sup>{exp}</sup>{suffixGap}{suffix}')
            opts = {
                'suffix': _translate('unit', 'cm⁻¹'),
                'siPrefix': False,
                'format': '{value:.{decimals}e}{suffixGap}{suffix}'
            }

        else:
            self.check_voltage_persists.setText(_translate('main window', 'Keep voltage range'))

            a.enableAutoSIPrefix(True)
            a.setLabel(text=_translate("plot axes labels", 'Voltage'),
                       units=_translate('unit', 'V'),
                       )

            self._cursor_y.suffix = _translate('unit', 'V')
            self._cursor_y.siPrefix = True
            self._cursor_y.setFormatStr('{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}')
            opts = {
                'suffix': _translate('unit', 'V'),
                'siPrefix': True,
                'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'
            }
        self.spin_voltage_min.setOpts(**opts)
        self.spin_voltage_max.setOpts(**opts)

        self.hide_cursors()

        # change visibility of the found lines table columns
        if display_gamma:
            self.table_found_lines.hideColumn(1)
            self.table_found_lines.showColumn(2)
        else:
            self.table_found_lines.hideColumn(2)
            self.table_found_lines.showColumn(1)

    def save_data(self) -> None:
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
        good: np.ndarray = (min_mark <= x) & (x <= max_mark)
        x = x[good]
        y = y[good]
        del good
        data: np.ndarray
        if 'CSV' in _filter:
            if filename_parts[1] != '.csv':
                filename += '.csv'
            sep: str = self.settings.csv_separator
            if self.toolbar.switch_data_action.isChecked():
                data = np.vstack((x * 1e-6, y)).transpose()
                # noinspection PyTypeChecker
                np.savetxt(filename, data,
                           delimiter=sep,
                           header=(sep.join((_translate("plot axes labels", 'Frequency'),
                                             _translate("plot axes labels", 'Absorption')))
                                   + '\n'
                                   + sep.join((pg.siScale(1e6)[1] + _translate('unit', 'Hz'),
                                               _translate('unit', 'cm⁻¹')))),
                           fmt=('%.3f', '%.6e'), encoding='utf-8')
            else:
                data = np.vstack((x * 1e-6, y * 1e3)).transpose()
                # noinspection PyTypeChecker
                np.savetxt(filename, data,
                           delimiter=sep,
                           header=(sep.join((_translate("plot axes labels", 'Frequency'),
                                             _translate("plot axes labels", 'Voltage')))
                                   + '\n'
                                   + sep.join((pg.siScale(1e6)[1] + _translate('unit', 'Hz'),
                                               pg.siScale(1e-3)[1] + _translate('unit', 'V')))),
                           fmt=('%.3f', '%.6f'), encoding='utf-8')
        elif 'XLSX' in _filter:
            if filename_parts[1] != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                df: pd.DataFrame
                if self.toolbar.switch_data_action.isChecked():
                    data = np.vstack((x * 1e-6, y)).transpose()
                    df = pd.DataFrame(data)
                    df.to_excel(writer, index=False, header=[_translate('main window', 'Frequency [MHz]'),
                                                             _translate('main window', 'Absorption [cm⁻¹]')],
                                sheet_name=self._plot_line.name() or _translate('workbook', 'Sheet1'))
                else:
                    data = np.vstack((x * 1e-6, y * 1e3)).transpose()
                    df = pd.DataFrame(data)
                    df.to_excel(writer, index=False, header=[_translate('main window', 'Frequency [MHz]'),
                                                             _translate('main window', 'Voltage [mV]')],
                                sheet_name=self._plot_line.name() or _translate('workbook', 'Sheet1'))

    def copy_figure(self) -> None:
        # TODO: add legend to the figure to save
        exporter = pg.exporters.ImageExporter(self._canvas)
        self.hide_cursors()
        exporter.export(copy=True)

    def save_figure(self) -> None:
        # TODO: add legend to the figure to save
        exporter = pg.exporters.ImageExporter(self._canvas)
        _filter: str = \
            _translate('file dialog', 'Image files') + ' (' + ' '.join(exporter.getSupportedImageFormats()) + ')'
        filename, _filter = self.save_file_dialog(_filter=_filter)
        if not filename:
            return
        self.hide_cursors()
        exporter.export(filename)

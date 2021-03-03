# -*- coding: utf-8 -*-

import os
from typing import Any, Callable, List, Optional, Tuple, Type

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtCore import QCoreApplication, QPointF, QSettings, Qt
from PyQt5.QtGui import QBrush, QPalette
from PyQt5.QtWidgets import QFileDialog, QStatusBar, QAction
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

import detection
from data_model import DataModel
from toolbar import NavigationToolbar
from utils import copy_to_clipboard
from valuelabel import ValueLabel

TRACE_AVERAGING_RANGE: float = 25.

pg.ViewBox.suggestPadding = lambda *_: 0.0


class Plot:
    settings: QSettings
    _is_dark: bool
    _legend_box: Optional[pg.GraphicsLayoutWidget]
    _legend: Optional[pg.LegendItem]
    _figure: pg.PlotWidget
    _canvas: pg.PlotItem
    _toolbar: NavigationToolbar
    _status_bar: Optional[QStatusBar]
    _found_lines_data_model: Optional[DataModel]
    _plot_line: pg.PlotDataItem
    _min_frequency: float
    _max_frequency: float
    _min_voltage: float
    _max_voltage: float
    _ignore_scale_change: bool
    on_xlim_changed_callback: Optional[Callable]
    on_ylim_changed_callback: Optional[Callable]
    on_data_loaded_callback: Optional[Callable]

    def __init__(self, figure: pg.PlotWidget, toolbar: NavigationToolbar, *,
                 status_bar: Optional[QStatusBar] = None,
                 legend: Optional[pg.GraphicsLayoutWidget] = None,
                 settings: Optional[QSettings] = None,
                 found_lines_data_model: Optional[DataModel] = None,
                 **kwargs):
        if settings is None:
            self.settings = QSettings("SavSoft", "Fast Sweep Viewer")
        else:
            self.settings = settings

        self._is_dark = QPalette().color(QPalette.Window).lightness() < 128

        self._legend_box = legend
        self._legend = None

        self._figure = figure
        self._canvas = figure.getPlotItem()
        self._view_all_action: QAction = QAction()

        self._toolbar = toolbar

        self._status_bar = status_bar
        self._cursor_x = ValueLabel(self._status_bar, siPrefix=True, decimals=6)
        self._cursor_y = ValueLabel(self._status_bar, siPrefix=True, decimals=3)

        self._found_lines_data_model = found_lines_data_model

        self._plot_line = self._figure.plot(np.empty(0), name='', pen=pg.intColor(0))
        self._plot_line.yData = np.empty(0)

        self._min_frequency = np.nan
        self._max_frequency = np.nan
        self._min_voltage = np.nan
        self._max_voltage = np.nan

        self._ignore_scale_change = False

        self.on_xlim_changed_callback = kwargs.pop('on_xlim_changed', None)
        self.on_ylim_changed_callback = kwargs.pop('on_ylim_changed', None)
        self.on_data_loaded_callback = kwargs.pop('on_data_loaded', None)

        try:
            self.model_signal: np.ndarray = np.loadtxt('averaged fs signal filtered.csv')
        except (OSError, BlockingIOError):
            self.model_signal: np.ndarray = np.empty(0)
        self.user_found_lines: pg.PlotDataItem = \
            self._canvas.scatterPlot(np.empty(0),
                                     pen=pg.intColor(0), brush=pg.intColor(0))
        self.automatically_found_lines: pg.PlotDataItem = \
            self._canvas.scatterPlot(np.empty(0),
                                     pen=pg.intColor(0), brush=pg.intColor(0))

        # cross hair
        self._crosshair_v_line = pg.InfiniteLine(angle=90, movable=False)
        self._crosshair_h_line = pg.InfiniteLine(angle=0, movable=False)

        self._mouse_moved_signal_proxy = pg.SignalProxy(self._figure.scene().sigMouseMoved,
                                                        rateLimit=10, slot=self.on_mouse_moved)
        self._axis_range_changed_signal_proxy = pg.SignalProxy(self._figure.sigRangeChanged,
                                                               rateLimit=20, slot=self.on_lim_changed)

        self.setup_ui()

    def setup_ui(self):
        if self._is_dark:
            self._figure.setBackground(QBrush(pg.mkColor(0, 0, 0)))
            label: str
            for label, ax_d in self._canvas.axes.items():
                ax: pg.AxisItem = ax_d['item']
                ax.setPen('d')
                ax.setTextPen('d')
        else:
            self._figure.setBackground(QBrush(pg.mkColor(255, 255, 255)))
            label: str
            for label, ax_d in self._canvas.axes.items():
                ax: pg.AxisItem = ax_d['item']
                ax.setPen('k')
                ax.setTextPen('k')
        if self._legend_box is not None:
            self._legend = pg.LegendItem(offset=(0, 0))
            self._legend_box.setCentralItem(self._legend)
            if self._is_dark:
                self._legend_box.setBackground(QBrush(pg.mkColor(0, 0, 0, 0)))
                self._legend.setLabelTextColor(255, 255, 255, 255)
            else:
                self._legend_box.setBackground(QBrush(pg.mkColor(255, 255, 255, 0)))
                self._legend.setLabelTextColor(0, 0, 0, 255)
            # self._legend_box.sceneObj.sigMouseClicked.connect(self.on_legend_click)

        self._toolbar.open_action.triggered.connect(self.load_data)
        self._toolbar.clear_action.triggered.connect(self.clear)
        self._toolbar.save_data_action.triggered.connect(self.save_data)
        self._toolbar.copy_figure_action.triggered.connect(self.copy_figure)
        self._toolbar.save_figure_action.triggered.connect(self.save_figure)
        self._toolbar.copy_trace_action.triggered.connect(self.copy_found_lines)
        self._toolbar.save_trace_action.triggered.connect(self.save_found_lines)
        self._toolbar.clear_trace_action.triggered.connect(self.clear_found_lines)
        self._toolbar.configure_action.triggered.connect(self._toolbar.edit_parameters)

        self._status_bar.addWidget(self._cursor_x)
        self._status_bar.addWidget(self._cursor_y)

        self._figure.plotItem.addItem(self._crosshair_v_line, ignoreBounds=True)
        self._figure.plotItem.addItem(self._crosshair_h_line, ignoreBounds=True)
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)

        self.translate_ui()

        self._toolbar.load_parameters()

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
        self._view_all_action.triggered.connect(lambda: self._canvas.vb.autoRange(padding=0))
        self._canvas.vb.menu.addAction(self._view_all_action)
        self._figure.sceneObj.contextMenu = None

        self._figure.sceneObj.sigMouseClicked.connect(self.on_plot_clicked)

        def remove_points(item: pg.PlotDataItem, points: List[pg.SpotItem], ev: MouseClickEvent):
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
            # elif self._found_lines_data_model.all_data.shape[1] > 1:
            #     point: pg.SpotItem
            #     selected_points: List[QPointF] = [point.pos() for point in points]
            #     # TODO: highlight the table row that stores the point data
            #     #  emit signal with the data

        line: pg.PlotDataItem
        for line in (self.automatically_found_lines, self.user_found_lines):
            line.sigPointsClicked.connect(remove_points)

    def translate_ui(self):
        _translate: Callable[[str, str, Optional[str], int], str] = QCoreApplication.translate

        self._figure.setLabel('bottom',
                              text=_translate("plot axes labels", 'Frequency'),
                              units=_translate('unit', 'Hz'),
                              unitPrefix=_translate('unit prefix', 'M'))
        self._figure.setLabel('left',
                              text=_translate("plot axes labels", 'Voltage'),
                              units=_translate('unit', 'V'),
                              unitPrefix=_translate('unit prefix', 'm'))

        self._toolbar.open_action.setIconText(_translate("plot toolbar action", "Open"))
        self._toolbar.open_action.setToolTip(_translate("plot toolbar action", "Load spectrometer data"))
        self._toolbar.clear_action.setIconText(_translate("plot toolbar action", "Clear"))
        self._toolbar.clear_action.setToolTip(_translate("plot toolbar action", "Clear lines and markers"))
        self._toolbar.save_data_action.setIconText(_translate("plot toolbar action", "Save Data"))
        self._toolbar.save_data_action.setToolTip(_translate("plot toolbar action", "Export the visible data"))
        self._toolbar.copy_figure_action.setIconText(_translate("plot toolbar action", "Copy Figure"))
        self._toolbar.copy_figure_action.setToolTip(_translate("plot toolbar action", "Copy the plot as an image"))
        self._toolbar.save_figure_action.setIconText(_translate("plot toolbar action", "Save Figure"))
        self._toolbar.save_figure_action.setToolTip(_translate("plot toolbar action", "Save the plot into clipboard"))
        self._toolbar.trace_action.setIconText(_translate("plot toolbar action", "Mark"))
        self._toolbar.trace_action.setToolTip(_translate("plot toolbar action", "Mark data points"))
        self._toolbar.copy_trace_action.setIconText(_translate("plot toolbar action", "Copy Marked"))
        self._toolbar.copy_trace_action.setToolTip(_translate("plot toolbar action",
                                                              "Copy marked points values into clipboard"))
        self._toolbar.save_trace_action.setIconText(_translate("plot toolbar action", "Save Marked"))
        self._toolbar.save_trace_action.setToolTip(_translate("plot toolbar action", "Save marked points values"))
        self._toolbar.clear_trace_action.setIconText(_translate("plot toolbar action", "Clear Marked"))
        self._toolbar.clear_trace_action.setToolTip(_translate("plot toolbar action", "Clear marked points"))
        self._toolbar.configure_action.setIconText(_translate("plot toolbar action", "Configure"))
        self._toolbar.configure_action.setToolTip(_translate("plot toolbar action", "Edit curve parameters"))

        self._view_all_action.setText(_translate("plot context menu action", "View All"))
        self._canvas.ctrl.alphaGroup.parent().setTitle(_translate("plot context menu action", "Alpha"))
        self._canvas.ctrl.gridGroup.parent().setTitle(_translate("plot context menu action", "Grid"))

        self._cursor_x.suffix = _translate('unit', 'Hz')
        self._cursor_y.suffix = _translate('unit', 'V')

        self._canvas.ctrlMenu.setTitle(_translate('menu', 'Plot Options'))

    def on_mouse_moved(self, event: Tuple[QPointF]):
        pos: QPointF = event[0]
        if self._figure.sceneBoundingRect().contains(pos):
            point: QPointF = self._canvas.vb.mapSceneToView(pos)
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
        if self.trace_mode and event.modifiers() == Qt.NoModifier and self._figure.sceneBoundingRect().contains(pos):
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
                if self.user_found_lines.xData is None \
                        or self.user_found_lines.yData.size is None:
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
                    self.user_found_lines.setData(
                        np.append(self.user_found_lines.xData,
                                  self._plot_line.xData[closest_point_index]),
                        np.append(self.user_found_lines.yData,
                                  self._plot_line.yData[closest_point_index])
                    )
                self._found_lines_data_model.append_data([self._plot_line.xData[closest_point_index],
                                                          self._plot_line.yData[closest_point_index]])
                self._toolbar.copy_trace_action.setEnabled(True)
                self._toolbar.save_trace_action.setEnabled(True)
                self._toolbar.clear_trace_action.setEnabled(True)

    def on_lim_changed(self, *args):
        rect: List[List[float]] = args[0][1]
        if self._ignore_scale_change:
            return
        xlim: List[float]
        ylim: List[float]
        xlim, ylim = rect
        self._ignore_scale_change = True
        if self.on_xlim_changed_callback is not None and callable(self.on_xlim_changed_callback):
            self.on_xlim_changed_callback(xlim)
        if self.on_ylim_changed_callback is not None and callable(self.on_ylim_changed_callback):
            self.on_ylim_changed_callback(ylim)
        self._ignore_scale_change = False

    @property
    def line(self):
        return self._plot_line

    @property
    def label(self):
        return self._plot_line.name()

    def set_frequency_range(self, lower_value: float, upper_value: float):
        self._figure.plotItem.setXRange(lower_value, upper_value, padding=0.0)

    def set_voltage_range(self, lower_value: float, upper_value: float):
        self._figure.plotItem.setYRange(lower_value, upper_value, padding=0.0)

    def find_lines(self, threshold: float):
        if self.model_signal.size < 2:
            return

        from scipy import interpolate

        self._ignore_scale_change = True
        if self._plot_line.xData.size < 2 or self._plot_line.yData.size < 2:
            return
        # re-scale the signal to the actual frequency mesh
        x_model: np.ndarray = np.arange(self.model_signal.size, dtype=self._plot_line.xData.dtype) * 0.1
        f = interpolate.interp1d(x_model, self.model_signal, kind=2)
        x_model_new: np.ndarray = np.arange(x_model[0], x_model[-1],
                                            self._plot_line.xData[1] - self._plot_line.xData[0])
        y_model_new: np.ndarray = f(x_model_new)
        found_lines = detection.peaks_positions(self._plot_line.xData,
                                                detection.correlation(y_model_new,
                                                                      self._plot_line.xData,
                                                                      self._plot_line.yData),
                                                threshold=1.0 / threshold)
        if found_lines.size:
            self.automatically_found_lines.setData(self._plot_line.xData[found_lines],
                                                   self._plot_line.yData[found_lines])
        else:
            self.automatically_found_lines.setData(np.empty(0), np.empty(0))

        # update the table
        if self.user_found_lines.xData is not None and self.user_found_lines.yData is not None:
            self._found_lines_data_model.set_data(np.column_stack((
                np.concatenate((self.automatically_found_lines.xData, self.user_found_lines.xData)),
                np.concatenate((self.automatically_found_lines.yData, self.user_found_lines.yData)),
            )))
        else:
            self._found_lines_data_model.set_data(np.column_stack((
                self.automatically_found_lines.xData,
                self.automatically_found_lines.yData,
            )))

        if not self._found_lines_data_model.is_empty:
            self._toolbar.copy_trace_action.setEnabled(True)
            self._toolbar.save_trace_action.setEnabled(True)
            self._toolbar.clear_trace_action.setEnabled(True)

        self._ignore_scale_change = False

    def prev_found_line(self, init_frequency: float) -> float:
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
            return prev_line_freq[np.argmin(init_frequency - prev_line_freq)]
        else:
            return init_frequency

    def next_found_line(self, init_frequency: float) -> float:
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
            return next_line_freq[np.argmin(next_line_freq - init_frequency)]
        else:
            return init_frequency

    def stringify_table_plain_text(self) -> str:
        """
        Convert table cells to string for copying as plain text
        :return: the plain text representation of the table
        """
        text_matrix: List[List[str]] = [[self._found_lines_data_model.formatted_item(row, column)
                                         for column in range(self._found_lines_data_model.columnCount())]
                                        for row in range(self._found_lines_data_model.rowCount(available_count=True))]
        row_texts: List[str]
        text: List[str] = [self.settings.csv_separator.join(row_texts) for row_texts in text_matrix]
        return self.settings.line_end.join(text)

    def stringify_table_html(self) -> str:
        """
        Convert table cells to string for copying as rich text
        :return: the rich text representation of the table
        """
        text_matrix: List[List[str]] = [[('<td>' + self._found_lines_data_model.formatted_item(row, column) + '</td>')
                                         for column in range(self._found_lines_data_model.columnCount())]
                                        for row in range(self._found_lines_data_model.rowCount(available_count=True))]
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
        x: np.ndarray = self._found_lines_data_model.all_data[:, 0] * 1e-6
        y: np.ndarray = self._found_lines_data_model.all_data[:, 1]
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
        self._found_lines_data_model.clear()
        self._toolbar.copy_trace_action.setEnabled(False)
        self._toolbar.save_trace_action.setEnabled(False)
        self._toolbar.clear_trace_action.setEnabled(False)
        self._canvas.replot()

    def clear(self):
        self._plot_line.clear()
        self.clear_found_lines()
        if self._legend is not None:
            self._legend.clear()
            # self._legend.setVisible(False)
        self._toolbar.trace_action.setChecked(False)
        self._toolbar.clear_action.setEnabled(False)
        self._toolbar.save_data_action.setEnabled(False)
        self._toolbar.copy_figure_action.setEnabled(False)
        self._toolbar.save_figure_action.setEnabled(False)
        self._toolbar.trace_action.setEnabled(False)
        self._toolbar.copy_trace_action.setEnabled(False)
        self._toolbar.save_trace_action.setEnabled(False)
        self._toolbar.clear_trace_action.setEnabled(False)
        self._toolbar.configure_action.setEnabled(False)
        self._canvas.replot()

    def update_legend(self):
        if self._legend is not None:
            self._legend.clear()
            if self._plot_line.name():
                self._legend.addItem(self._plot_line, self._plot_line.name())
            self._legend_box.setMinimumWidth(self._legend.boundingRect().width())

    def load_data(self):
        filename: str
        _filter: str
        filename, _filter = self.open_file_dialog(_filter="Spectrometer Settings (*.fmd);;All Files (*)")
        fn = os.path.splitext(filename)[0]
        if os.path.exists(fn + '.fmd'):
            with open(fn + '.fmd', 'r') as fin:
                line: str
                for line in fin:
                    if line and not line.startswith('*'):
                        t = list(map(lambda w: w.strip(), line.split(':', maxsplit=1)))
                        if len(t) > 1:
                            if t[0].lower() == 'FStart [GHz]'.lower():
                                self._min_frequency = float(t[1]) * 1e6
                            elif t[0].lower() == 'FStop [GHz]'.lower():
                                self._max_frequency = float(t[1]) * 1e6
        else:
            return
        if os.path.exists(fn + '.frd'):
            new_label: str = os.path.split(fn)[-1]

            y: np.ndarray = np.loadtxt(fn + '.frd', usecols=(0,))
            x: np.ndarray = np.linspace(self._min_frequency, self._max_frequency,
                                        num=y.size, endpoint=False)
            self._plot_line.setData(x, y, name=new_label)

            self._min_voltage = np.min(self._plot_line.yData)
            self._max_voltage = np.max(self._plot_line.yData)

            self._ignore_scale_change = True
            self._figure.setXRange(self._min_frequency, self._max_frequency)
            self._figure.setYRange(self._min_voltage, self._max_voltage)
            self._ignore_scale_change = False

            self.update_legend()

            self._toolbar.clear_action.setEnabled(True)
            self._toolbar.save_data_action.setEnabled(True)
            self._toolbar.copy_figure_action.setEnabled(True)
            self._toolbar.save_figure_action.setEnabled(True)
            self._toolbar.trace_action.setEnabled(True)
            self._toolbar.configure_action.setEnabled(True)

            if self.on_data_loaded_callback is not None and callable(self.on_data_loaded_callback):
                self.on_data_loaded_callback((self._min_frequency, self._max_frequency,
                                              self._min_voltage, self._max_voltage))

            return
        return

    @property
    def trace_mode(self):
        return self._toolbar.trace_action.isChecked()

    def actions_off(self):
        self._toolbar.trace_action.setChecked(False)

    def save_data(self):
        if self._plot_line.yData is None:
            return
        filename, _filter = self.save_file_dialog(_filter='CSV (*.csv);;XLSX (*.xlsx)')
        if not filename:
            return
        filename_parts: Tuple[str, str] = os.path.splitext(filename)
        x: np.ndarray = self._plot_line.xData
        y: np.ndarray = self._plot_line.yData
        _max_mark: float
        _min_mark: float
        _min_mark, _max_mark = self._canvas.axes['bottom']['item'].range
        good: np.ndarray = (_min_mark <= x & x <= _max_mark)
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

    def get_config_value(self, section: str, key: str, default, _type: Type):
        if section not in self.settings.childGroups():
            return default
        self.settings.beginGroup(section)
        # print(section, key)
        try:
            v = self.settings.value(key, default, _type)
        except TypeError:
            v = default
        self.settings.endGroup()
        return v

    def set_config_value(self, section: str, key: str, value: Any):
        self.settings.beginGroup(section)
        # print(section, key, value, type(value))
        self.settings.setValue(key, value)
        self.settings.endGroup()

    def open_file_dialog(self, _filter: str = '') -> Tuple[str, str]:
        directory: str = self.get_config_value('open', 'location', '', str)
        # native dialog misbehaves when running inside snap but Qt dialog is tortoise-like in NT
        options: QFileDialog.Option = QFileDialog.DontUseNativeDialog if os.name != 'nt' else QFileDialog.DontUseSheet
        filename: str
        _filter: str
        filename, _filter = QFileDialog.getOpenFileName(filter=_filter,
                                                        directory=directory,
                                                        options=options)
        if os.path.split(filename)[0]:
            self.set_config_value('open', 'location', os.path.split(filename)[0])
        return filename, _filter

    def save_file_dialog(self, _filter: str = '') -> Tuple[str, str]:
        directory: str = self.get_config_value('save', 'location', '', str)
        initial_filter: str = self.get_config_value('save', 'filter', '', str)
        # native dialog misbehaves when running inside snap but Qt dialog is tortoise-like in NT
        options: QFileDialog.Option = QFileDialog.DontUseNativeDialog if os.name != 'nt' else QFileDialog.DontUseSheet
        filename: str
        _filter: str
        filename, _filter = QFileDialog.getSaveFileName(filter=_filter,
                                                        directory=directory,
                                                        initialFilter=initial_filter,
                                                        options=options)
        if os.path.split(filename)[0]:
            self.set_config_value('save', 'location', os.path.split(filename)[0])
        self.set_config_value('save', 'filter', _filter)
        return filename, _filter

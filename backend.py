# -*- coding: utf-8 -*-

import os
import sys
from typing import Callable, List, Optional, Dict, Tuple, Any, Type

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtCore import QCoreApplication, QSettings, QSize, Qt, QPointF
from PyQt5.QtGui import QBrush, QIcon, QPalette, QPixmap
from PyQt5.QtWidgets import QAction, QFileDialog, QMessageBox, QToolBar, QStatusBar
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

import detection
import figureoptions
from valuelabel import ValueLabel

LINES_COUNT: int = 2

TRACE_AVERAGING_RANGE: float = 25.

IMAGE_EXT: str = '.svg'

pg.ViewBox.suggestPadding = lambda *_: 0.0


def nonemin(x):
    m = np.nan
    if np.iterable(x):
        for _ in x:
            if _ is not None:
                _2 = float(np.nanmin((m, _)))
                if np.isnan(m) or m > _2:
                    m = _2
        return m
    else:
        return x


def nonemax(x):
    m = np.nan
    if np.iterable(x):
        for _ in x:
            if _ is not None:
                _2 = float(np.nanmax((m, _)))
                if np.isnan(m) or m < _2:
                    m = _2
        return m
    else:
        return x


# https://www.reddit.com/r/learnpython/comments/4kjie3/how_to_include_gui_images_with_pyinstaller/d3gjmom
def resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(getattr(sys, '_MEIPASS'), relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


def load_icon(filename: str) -> QIcon:
    is_dark: bool = QPalette().color(QPalette.Window).lightness() < 128
    icon: QIcon = QIcon()
    icon.addPixmap(QPixmap(resource_path(os.path.join('img', 'dark' if is_dark else 'light', filename + IMAGE_EXT))),
                   QIcon.Normal, QIcon.Off)
    return icon


class NavigationToolbar(QToolBar):
    def __init__(self, parent, *,
                 parameters_title: str = 'Figure options',
                 parameters_icon: Optional[QIcon] = None):
        super().__init__('Navigation Toolbar', parent)
        self.setObjectName('NavigationToolbar')

        self.parameters_title: str = parameters_title
        self.parameters_icon: Optional[QIcon] = parameters_icon

        self.open_action: QAction = QAction(self)
        self.clear_action: QAction = QAction(self)
        self.save_data_action: QAction = QAction(self)
        self.save_figure_action: QAction = QAction(self)
        self.trace_action: QAction = QAction(self)
        self.trace_multiple_action: QAction = QAction(self)
        self.copy_trace_action: QAction = QAction(self)
        self.save_trace_action: QAction = QAction(self)
        self.clear_trace_action: QAction = QAction(self)
        self.configure_action: QAction = QAction(self)

        # TODO: add keyboard shortcuts
        a: QAction
        i: str
        for a, i in zip([self.open_action,
                         self.clear_action,
                         self.save_data_action,
                         self.save_figure_action,
                         self.trace_action,
                         self.trace_multiple_action,
                         self.copy_trace_action,
                         self.save_trace_action,
                         self.clear_trace_action,
                         self.configure_action],
                        ['open', 'delete',
                         'saveTable',
                         'saveImage',
                         'selectObject', 'selectMultiple',
                         'copySelected', 'saveSelected', 'clearSelected',
                         'configure']):
            a.setIcon(load_icon(i.lower()))

        self.addAction(self.open_action)
        self.addAction(self.clear_action)
        self.addSeparator()
        self.addAction(self.save_data_action)
        self.addAction(self.save_figure_action)
        self.addSeparator()
        self.addAction(self.trace_action)
        self.addAction(self.trace_multiple_action)
        self.addAction(self.copy_trace_action)
        self.addAction(self.save_trace_action)
        self.addAction(self.clear_trace_action)
        self.addSeparator()
        self.addAction(self.configure_action)

        self.clear_action.setEnabled(False)
        self.save_data_action.setEnabled(False)
        self.save_figure_action.setEnabled(False)
        self.trace_action.setEnabled(False)
        self.trace_multiple_action.setEnabled(False)
        self.copy_trace_action.setEnabled(False)
        self.save_trace_action.setEnabled(False)
        self.clear_trace_action.setEnabled(False)
        self.configure_action.setEnabled(False)

        self.trace_action.setCheckable(True)
        self.trace_multiple_action.setCheckable(True)

        # Aesthetic adjustments - we need to set these explicitly in PyQt5
        # otherwise the layout looks different - but we don't want to set it if
        # not using HiDPI icons otherwise they look worse than before.
        self.setIconSize(QSize(24, 24))
        self.layout().setSpacing(12)

    def load_parameters(self):
        # figureoptions.load_settings(ax, self)
        pass

    def edit_parameters(self):
        ax, = self.canvas.figure.get_axes()
        figureoptions.figure_edit(ax, self, title=self.parameters_title, icon=self.parameters_icon)


class Plot:
    settings: QSettings
    _is_dark: bool
    _legend_box: Optional[pg.GraphicsLayoutWidget]
    _legend: Optional[pg.LegendItem]
    _figure: pg.PlotWidget
    _canvas: pg.PlotItem
    _toolbar: NavigationToolbar
    _status_bar: Optional[QStatusBar]
    _plot_lines: List[pg.PlotDataItem]
    _plot_lines_labels: List[str]
    _plot_frequencies: List[np.ndarray]
    _plot_voltages: List[np.ndarray]
    _min_frequency: Optional[float]
    _max_frequency: Optional[float]
    _min_voltage: Optional[float]
    _max_voltage: Optional[float]
    _ignore_scale_change: bool
    on_xlim_changed_callback: Optional[Callable]
    on_ylim_changed_callback: Optional[Callable]
    on_data_loaded_callback: Optional[Callable]

    def __init__(self, figure: pg.PlotWidget, toolbar: NavigationToolbar, *,
                 status_bar: Optional[QStatusBar] = None,
                 legend: Optional[pg.GraphicsLayoutWidget] = None,
                 settings: Optional[QSettings] = None,
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

        self._toolbar = toolbar

        self._status_bar = status_bar
        self._cursor_x = ValueLabel(self._status_bar, siPrefix=True, decimals=6)
        self._cursor_y = ValueLabel(self._status_bar, siPrefix=True, decimals=3)

        self._plot_lines = [self._figure.plot(np.empty(0), name='', pen=pg.intColor(5 * i))
                            for i in range(LINES_COUNT)]
        self._plot_lines_labels = [''] * LINES_COUNT
        self._plot_frequencies = [np.empty(0)] * LINES_COUNT
        self._plot_voltages = [np.empty(0)] * LINES_COUNT

        self._min_frequency = None
        self._max_frequency = None
        self._min_voltage = None
        self._max_voltage = None

        self._ignore_scale_change = False

        self.on_xlim_changed_callback = kwargs.pop('on_xlim_changed', None)
        self.on_ylim_changed_callback = kwargs.pop('on_ylim_changed', None)
        self.on_data_loaded_callback = kwargs.pop('on_data_loaded', None)

        try:
            self.model_signal: np.ndarray = np.loadtxt('averaged fs signal filtered.csv')
        except (OSError, BlockingIOError):
            self.model_signal: np.ndarray = np.empty(0)
        self.found_lines: List[pg.ScatterPlotItem] = \
            [self._canvas.scatterPlot(np.empty(0),
                                      pen=pg.intColor(5 * i), brush=pg.intColor(5 * i))
             for i in range(LINES_COUNT)]

        # cross hair
        self._crosshair_v_line = pg.InfiniteLine(angle=90, movable=False)
        self._crosshair_h_line = pg.InfiniteLine(angle=0, movable=False)

        self._mouse_moved_signal_proxy = pg.SignalProxy(self._figure.scene().sigMouseMoved,
                                                        rateLimit=10, slot=self.mouse_moved)
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
            self._legend_box.sceneObj.sigMouseClicked.connect(self.on_legend_click)

        self._toolbar.open_action.triggered.connect(self.load_data)
        self._toolbar.clear_action.triggered.connect(self.clear)
        self._toolbar.save_data_action.triggered.connect(
            lambda: self.save_data(*self.save_file_dialog(_filter="CSV (*.csv);;XLSX (*.xlsx)")))
        self._toolbar.save_figure_action.triggered.connect(self.save_figure)
        self._toolbar.trace_action.toggled.connect(self.plot_trace_action_toggled)
        self._toolbar.trace_multiple_action.toggled.connect(self.plot_trace_multiple_action_toggled)
        self._toolbar.configure_action.triggered.connect(self._toolbar.edit_parameters)

        self._status_bar.addWidget(self._cursor_x)
        self._status_bar.addWidget(self._cursor_y)

        self._figure.plotItem.addItem(self._crosshair_v_line, ignoreBounds=True)
        self._figure.plotItem.addItem(self._crosshair_h_line, ignoreBounds=True)
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)

        self.translate_ui()

        self._toolbar.load_parameters()
        # self.load_settings()

        # customize menu
        titles_to_leave: List[str] = [
            self._canvas.ctrl.alphaGroup.parent().title(),
            self._canvas.ctrl.gridGroup.parent().title(),
        ]
        for action in self._canvas.ctrlMenu.actions():
            if action.text() not in titles_to_leave:
                self._canvas.ctrlMenu.removeAction(action)

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
        self._toolbar.save_data_action.setToolTip(_translate("plot toolbar action", "Export the selected data"))
        self._toolbar.save_figure_action.setIconText(_translate("plot toolbar action", "Save Figure"))
        self._toolbar.save_figure_action.setToolTip(_translate("plot toolbar action", "Save the plot as an image"))
        self._toolbar.trace_action.setIconText(_translate("plot toolbar action", "Mark"))
        self._toolbar.trace_action.setToolTip(_translate("plot toolbar action", "Mark a data point"))
        self._toolbar.trace_multiple_action.setIconText(_translate("plot toolbar action", "Mark Multiple"))
        self._toolbar.trace_multiple_action.setToolTip(_translate("plot toolbar action", "Mark several data points"))
        self._toolbar.copy_trace_action.setIconText(_translate("plot toolbar action", "Copy Marked"))
        self._toolbar.copy_trace_action.setToolTip(_translate("plot toolbar action",
                                                              "Copy marked points values into clipboard"))
        self._toolbar.save_trace_action.setIconText(_translate("plot toolbar action", "Save Marked"))
        self._toolbar.save_trace_action.setToolTip(_translate("plot toolbar action", "Save marked points values"))
        self._toolbar.clear_trace_action.setIconText(_translate("plot toolbar action", "Clear Marked"))
        self._toolbar.clear_trace_action.setToolTip(_translate("plot toolbar action", "Clear marked points values"))
        self._toolbar.configure_action.setIconText(_translate("plot toolbar action", "Configure"))
        self._toolbar.configure_action.setToolTip(_translate("plot toolbar action", "Edit curve parameters"))

        self._cursor_x.suffix = _translate('unit', 'Hz')
        self._cursor_y.suffix = _translate('unit', 'V')

        self._canvas.ctrlMenu.setTitle(_translate('menu', 'Plot Options'))

    def on_legend_click(self, event: MouseClickEvent):
        # rotate lines
        _modifiers: Qt.KeyboardModifiers = event.modifiers()
        if _modifiers == Qt.NoModifier:
            self._plot_lines_labels = self._plot_lines_labels[1:] + [self._plot_lines_labels[0]]
            self._plot_frequencies = self._plot_frequencies[1:] + [self._plot_frequencies[0]]
            self._plot_voltages = self._plot_voltages[1:] + [self._plot_voltages[0]]
        else:
            self._plot_lines_labels = [self._plot_lines_labels[-1]] + self._plot_lines_labels[:-1]
            self._plot_frequencies = [self._plot_frequencies[-1]] + self._plot_frequencies[:-1]
            self._plot_voltages = [self._plot_voltages[-1]] + self._plot_voltages[:-1]
        self.draw_data()
        self.update_legend()
        event.accept()

    def mouse_moved(self, event: Tuple[QPointF]):
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

    def load_settings(self):
        attrs: List[str] = ['top', 'bottom', 'left', 'right']
        defaults: Dict[str, float] = {attr: vars(self._figure.subplotpars)[attr] for attr in attrs}
        self._figure.subplots_adjust(**{attr: self.get_config_value('margins', attr, defaults[attr], float)
                                        for attr in attrs})

    @property
    def lines(self):
        return self._plot_lines

    @property
    def labels(self):
        return self._plot_lines_labels

    def set_frequency_range(self, lower_value: float, upper_value: float):
        self._figure.plotItem.setXRange(lower_value, upper_value, padding=0.0)

    def set_voltage_range(self, lower_value: float, upper_value: float):
        self._figure.plotItem.setYRange(lower_value, upper_value, padding=0.0)

    def draw_data(self):
        self._ignore_scale_change = True
        i: int
        x: np.ndarray
        y: np.ndarray
        for i, (x, y) in enumerate(zip(self._plot_frequencies, self._plot_voltages)):
            if not x.size or not y.size:
                self._plot_lines[i].clear()
                continue
            if (self._plot_lines[i].xData is None
                    and self._min_frequency is not None and self._max_frequency is not None
                    and self._min_voltage is not None and self._max_voltage is not None):
                self._figure.setXRange(self._min_frequency, self._max_frequency)
                self._figure.setYRange(self._min_voltage, self._max_voltage)
            self._plot_lines[i].setData(x, y, name=self._plot_lines_labels[i])
        self._ignore_scale_change = False

    def find_lines(self, threshold: float):
        if self.model_signal.size < 2:
            return

        from scipy import interpolate

        self._ignore_scale_change = True
        for i, (x, y) in enumerate(zip(self._plot_frequencies, self._plot_voltages)):
            if x.size < 2 or y.size < 2:
                continue
            # re-scale the signal to the actual frequency mesh
            x_model: np.ndarray = np.arange(self.model_signal.size, dtype=x.dtype) * 0.1
            f = interpolate.interp1d(x_model, self.model_signal, kind=2)
            x_model_new: np.ndarray = np.arange(x_model[0], x_model[-1], x[1] - x[0])
            y_model_new: np.ndarray = f(x_model_new)
            found_lines = detection.peaks_positions(x, detection.correlation(y_model_new, x, y),
                                                    threshold=1.0 / threshold)
            if found_lines.size:
                self.found_lines[i].setData(x[found_lines], y[found_lines])
            else:
                self.found_lines[i].setData(np.empty(0), np.empty(0))
        self._ignore_scale_change = False

    def prev_found_line(self, init_frequency: float) -> float:
        if self.model_signal.size < 2:
            return init_frequency

        prev_line_freq: np.ndarray = np.full(len(self.found_lines), np.nan)
        index: int
        line: pg.ScatterPlotItem
        for index, line in enumerate(self.found_lines):
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

        next_line_freq: np.ndarray = np.full(len(self.found_lines), np.nan)
        index: int
        line: pg.ScatterPlotItem
        for index, line in enumerate(self.found_lines):
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

    def clear_found_lines(self):
        line: pg.ScatterPlotItem
        for line in self.found_lines:
            line.clear()

    def clear(self):
        self._plot_voltages = [np.empty(0)] * LINES_COUNT
        self._plot_frequencies = [np.empty(0)] * LINES_COUNT
        line: pg.PlotDataItem
        for line in self._plot_lines:
            line.clear()
        self._plot_lines_labels = [''] * LINES_COUNT
        self.clear_found_lines()
        if self._legend is not None:
            self._legend.clear()
            # self._legend.setVisible(False)
        self._toolbar.trace_action.setChecked(False)
        self._toolbar.trace_multiple_action.setChecked(False)
        self._toolbar.clear_action.setEnabled(False)
        self._toolbar.save_data_action.setEnabled(False)
        self._toolbar.save_figure_action.setEnabled(False)
        self._toolbar.trace_action.setEnabled(False)
        self._toolbar.trace_multiple_action.setEnabled(False)
        self._toolbar.copy_trace_action.setEnabled(False)
        self._toolbar.save_trace_action.setEnabled(False)
        self._toolbar.clear_trace_action.setEnabled(False)
        self._toolbar.configure_action.setEnabled(False)
        self._canvas.replot()

    def update_legend(self):
        if self._legend is not None:
            self._legend.clear()
            lbl: str
            for i, lbl in enumerate(self._plot_lines_labels):
                if lbl:
                    self._legend.addItem(self._plot_lines[i], lbl)
            self._legend_box.setMinimumWidth(self._legend.boundingRect().width())

    def load_data(self):
        filename: str
        _filter: str
        filename, _filter = self.open_file_dialog(_filter="Spectrometer Settings (*.fmd);;All Files (*)")
        fn = os.path.splitext(filename)[0]
        _min_frequency: Optional[float] = self._min_frequency
        _max_frequency: Optional[float] = self._max_frequency
        if os.path.exists(fn + '.fmd'):
            with open(fn + '.fmd', 'r') as fin:
                line: str
                for line in fin:
                    if line and not line.startswith('*'):
                        t = list(map(lambda w: w.strip(), line.split(':', maxsplit=1)))
                        if len(t) > 1:
                            if t[0].lower() == 'FStart [GHz]'.lower():
                                _min_frequency = float(t[1]) * 1e6
                            elif t[0].lower() == 'FStop [GHz]'.lower():
                                _max_frequency = float(t[1]) * 1e6
        else:
            return
        if os.path.exists(fn + '.frd'):
            self._plot_voltages = self._plot_voltages[1:] + [np.loadtxt(fn + '.frd', usecols=(0,))]
            self._plot_frequencies = self._plot_frequencies[1:] + [np.linspace(_min_frequency, _max_frequency,
                                                                               num=self._plot_voltages[-1].size,
                                                                               endpoint=False)]
            new_label_base: str = os.path.split(fn)[-1]
            new_label: str = new_label_base
            i: int = 1
            while new_label in self._plot_lines_labels[1:]:
                i += 1
                new_label = f'{new_label_base} ({i})'
            self._plot_lines_labels = self._plot_lines_labels[1:] + [new_label]
            self._min_frequency = nonemin((_min_frequency, self._min_frequency))
            self._max_frequency = nonemax((_max_frequency, self._max_frequency))
            self._min_voltage = nonemin((self._min_voltage, np.min(self._plot_voltages[-1])))
            self._max_voltage = nonemax((self._max_voltage, np.max(self._plot_voltages[-1])))
            self.draw_data()

            self.update_legend()

            self._toolbar.clear_action.setEnabled(True)
            self._toolbar.save_data_action.setEnabled(True)
            self._toolbar.save_figure_action.setEnabled(True)
            self._toolbar.trace_action.setEnabled(True)
            self._toolbar.trace_multiple_action.setEnabled(True)
            self._toolbar.copy_trace_action.setEnabled(True)
            self._toolbar.save_trace_action.setEnabled(True)
            self._toolbar.clear_trace_action.setEnabled(True)
            self._toolbar.configure_action.setEnabled(True)

            if self.on_data_loaded_callback is not None and callable(self.on_data_loaded_callback):
                self.on_data_loaded_callback((self._min_frequency, self._max_frequency,
                                              self._min_voltage, self._max_voltage))

            return
        return

    @property
    def trace_mode(self):
        return self._toolbar.trace_action.isChecked()

    @property
    def trace_multiple_mode(self):
        return self._toolbar.trace_multiple_action.isChecked()

    def actions_off(self):
        self._toolbar.trace_action.setChecked(False)
        self._toolbar.trace_multiple_action.setChecked(False)

    def plot_trace_action_toggled(self, new_value: bool):
        if new_value:
            self._toolbar.trace_multiple_action.setChecked(False)
            self._figure.setFocus()

    def plot_trace_multiple_action_toggled(self, new_value: bool):
        if new_value:
            self._toolbar.trace_action.setChecked(False)
            self._figure.setFocus()

    def save_data(self, filename: str, _filter: str):
        if self._plot_voltages[-1].size == 0 or not filename:
            return
        filename_parts: Tuple[str, str] = os.path.splitext(filename)
        if 'CSV' in _filter:
            if filename_parts[1] != '.csv':
                filename += '.csv'
            x: np.ndarray = self._plot_frequencies[-1]
            y: np.ndarray = self._plot_voltages[-1]
            _max_mark: float
            _min_mark: float
            _min_mark, _max_mark = self._canvas.axes['bottom']['item'].range
            good: np.ndarray = (_min_mark <= x & x <= _max_mark)
            x = x[good]
            y = y[good]
            del good
            data: np.ndarray = np.vstack((x, y)).transpose()
            sep: str = '\t'
            # noinspection PyTypeChecker
            np.savetxt(filename, data,
                       delimiter=sep,
                       header=sep.join(('frequency', 'voltage')) + os.linesep + sep.join(('MHz', 'mV')),
                       fmt='%s')
        elif 'XLSX' in _filter:
            if filename_parts[1] != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                x: np.ndarray
                y: np.ndarray
                i: int
                for i, (x, y) in enumerate(zip(self._plot_frequencies, self._plot_voltages)):
                    if not self._plot_lines_labels[i]:
                        continue
                    _max_mark: float
                    _min_mark: float
                    _min_mark, _max_mark = self._canvas.axes['bottom']['item'].range
                    good: np.ndarray = (_min_mark <= x & x <= _max_mark)
                    x = x[good]
                    y = y[good]
                    del good
                    data: np.ndarray = np.vstack((x, y)).transpose()
                    df: pd.DataFrame = pd.DataFrame(data)
                    df.to_excel(writer, index=False, header=['Frequency [MHz]', 'Voltage [mV]'],
                                sheet_name=self._plot_lines_labels[i])

    def save_figure(self):
        # TODO: add legend to the figure to save
        filetypes: Dict[str, List[str]] = self._figure.get_supported_filetypes_grouped()
        # noinspection PyTypeChecker
        sorted_filetypes: List[Tuple[str, List[str]]] = sorted(filetypes.items())

        filters: str = ';;'.join([
            f'{name} ({" ".join([("*." + ext) for ext in extensions])})'
            for name, extensions in sorted_filetypes
        ])

        figure_file_name: str
        _filter: str
        figure_file_name, _filter = self.save_file_dialog(_filter=filters)
        if figure_file_name:
            try:
                self._figure.savefig(figure_file_name)
            except Exception as e:
                QMessageBox.critical(self._figure.parent(), "Error saving file", str(e),
                                     QMessageBox.Ok, QMessageBox.NoButton)

    @staticmethod
    def save_arbitrary_data(data, filename: str, _filter: str, *,
                            csv_header: str = '', csv_sep: str = '\t',
                            xlsx_header=None, sheet_name: str = 'Markings'):
        if not filename:
            return
        if xlsx_header is None:
            xlsx_header = True
        filename_parts: Tuple[str, str] = os.path.splitext(filename)
        if 'CSV' in _filter:
            if filename_parts[1].lower() != '.csv':
                filename += '.csv'
            if isinstance(data, dict):
                joined_data: Optional[np.ndarray] = None
                for key, value in data.items():
                    if joined_data is None:
                        joined_data = np.vstack(value).transpose()
                    else:
                        joined_data = np.vstack((joined_data, np.vstack(value).transpose()))
                data = joined_data
            else:
                data = np.vstack(data).transpose()
            # noinspection PyTypeChecker
            np.savetxt(filename, data,
                       delimiter=csv_sep,
                       header=csv_header,
                       fmt='%s')
        elif 'XLSX' in _filter:
            if filename_parts[1].lower() != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                if isinstance(data, dict):
                    for sheet_name in data:
                        sheet_data = np.vstack(data[sheet_name]).transpose()
                        df = pd.DataFrame(sheet_data)
                        df.to_excel(writer, index=False, header=xlsx_header,
                                    sheet_name=sheet_name)
                else:
                    data = np.vstack(data).transpose()
                    df = pd.DataFrame(data)
                    df.to_excel(writer, index=False, header=xlsx_header,
                                sheet_name=sheet_name)

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

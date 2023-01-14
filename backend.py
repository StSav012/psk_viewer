# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Callable, Final, Iterable, cast

import numpy as np
import pandas as pd  # type: ignore
import pyqtgraph as pg  # type: ignore
import pyqtgraph.exporters  # type: ignore
from numpy.typing import NDArray
from pyqtgraph import PlotWidget
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent  # type: ignore
from qtpy.QtCore import (QByteArray, QCoreApplication, QItemSelectionModel, QModelIndex,
                         QPoint, QPointF, QRect, QRectF, Qt)
from qtpy.QtGui import QBrush, QCloseEvent, QPalette, QPen
from qtpy.QtWidgets import QAction, QHeaderView, QMessageBox, QWidget

import detection
from gui import GUI
from plot_data_item import PlotDataItem
from preferences import Preferences
from toolbar import NavigationToolbar
from utils import (copy_to_clipboard, ensure_extension, load_data_csv, load_data_fs, load_data_scandat, resource_path,
                   superscript_number)

__all__ = ['App']

_translate = QCoreApplication.translate

pg.ViewBox.suggestPadding = lambda *_: 0.0


def tick_strings(self: pg.AxisItem, values: Iterable[float], scale: float, spacing: float) -> list[str]:
    """ improve formatting of `AxisItem.tickStrings` """

    if self.logMode:
        return cast(list[str], self.logTickStrings(values, scale, spacing))

    places: int = max(0, int(np.ceil(-np.log10(spacing * scale))))
    strings: list[str] = []
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


class App(GUI):
    PSK_DATA_MODE: Final[int] = 1
    PSK_WITH_JUMP_DATA_MODE: Final[int] = 2
    FS_DATA_MODE: Final[int] = -1

    def __init__(self, filename: str = '',
                 parent: QWidget | None = None, flags: Qt.WindowType = Qt.WindowType.Window) -> None:
        super().__init__(parent, flags)

        self._data_mode: int = 0

        self._is_dark: bool = self.palette().color(QPalette.ColorRole.Window).lightness() < 128

        self.toolbar: NavigationToolbar = NavigationToolbar(self, parameters_icon='configure')
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self._canvas: pg.PlotItem = self.figure.getPlotItem()
        self._view_all_action: QAction = QAction()

        self._ghost_line: pg.PlotDataItem = self.figure.plot(np.empty(0), name='')
        self._plot_line: pg.PlotDataItem = self.figure.plot(np.empty(0), name='')
        self._ghost_data: PlotDataItem = PlotDataItem()
        self._plot_data: PlotDataItem = PlotDataItem()

        self._ignore_scale_change: bool = False

        self.model_signal: NDArray[np.float64]
        try:
            self.model_signal = pd.read_csv(resource_path('averaged fs signal filtered.csv')).values.ravel()
        except (OSError, BlockingIOError):
            self.model_signal = np.empty(0)
            self.box_find_lines.hide()
        self.box_find_lines.setDisabled(True)
        self.user_found_lines: pg.PlotDataItem = self._canvas.scatterPlot(np.empty(0), symbol='o', pxMode=True)
        self.automatically_found_lines: pg.PlotDataItem = self._canvas.scatterPlot(np.empty(0), symbol='o', pxMode=True)
        self.user_found_lines_data: NDArray[np.float64] = np.empty(0)
        self.automatically_found_lines_data: NDArray[np.float64] = np.empty(0)

        # cross-hair
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

        self.figure.plotItem.addItem(self._crosshair_v_line, ignoreBounds=True)
        self.figure.plotItem.addItem(self._crosshair_h_line, ignoreBounds=True)
        self.hide_cursors()

        self.set_plot_line_appearance()
        self.set_marks_appearance()
        self.set_crosshair_lines_appearance()

        # customize menu
        titles_to_leave: list[str] = [
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
        self.toolbar.open_ghost_action.setIconText(_translate("plot toolbar action", "Open Ghost"))
        self.toolbar.open_ghost_action.setToolTip(_translate("plot toolbar action",
                                                             "Load spectrometer data as a background curve"))
        self.toolbar.clear_ghost_action.setIconText(_translate("plot toolbar action", "Clear Ghost"))
        self.toolbar.clear_ghost_action.setToolTip(_translate("plot toolbar action", "Clear the background curve"))
        self.toolbar.differentiate_action.setIconText(_translate("plot toolbar action",
                                                                 "Calculate second derivative"))
        self.toolbar.differentiate_action.setToolTip(_translate("plot toolbar action",
                                                                "Calculate finite-step second derivative"))
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

    def closeEvent(self, event: QCloseEvent) -> None:
        """ senseless joke in the loop """
        close: QMessageBox = QMessageBox()
        close.setText(_translate('main window', 'Are you sure?'))
        close.setIcon(QMessageBox.Icon.Question)
        close.setWindowIcon(self.windowIcon())
        close.setWindowTitle(_translate('main window', 'Spectrometer Data Viewer'))
        close.setStandardButtons(QMessageBox.StandardButton.Yes
                                 | QMessageBox.StandardButton.No
                                 | QMessageBox.StandardButton.Cancel)
        close_code: QMessageBox.StandardButton = (QMessageBox.StandardButton.No
                                                  if self._plot_data.frequency_span > 0.0
                                                  else QMessageBox.StandardButton.Yes)
        while close_code == QMessageBox.StandardButton.No:
            close_code = close.exec()

        if close_code == QMessageBox.StandardButton.Yes:
            self.settings.setValue('windowGeometry', self.saveGeometry())
            self.settings.setValue('windowState', self.saveState())
            self.settings.sync()
            event.accept()
        elif close_code == QMessageBox.StandardButton.Cancel:
            event.ignore()

    def load_config(self) -> None:
        self._loading = True
        # common settings
        if self.settings.contains('windowGeometry'):
            self.restoreGeometry(cast(QByteArray, self.settings.value('windowGeometry', QByteArray())))
        else:
            window_frame: QRect = self.frameGeometry()
            app: QCoreApplication = QCoreApplication.instance()
            desktop_center: QPoint = app.primaryScreen().availableGeometry().center()
            window_frame.moveCenter(desktop_center)
            self.move(window_frame.topLeft())
        self.restoreState(cast(QByteArray, self.settings.value('windowState', QByteArray())))

        self.check_frequency_persists.setChecked(self.get_config_value('frequency', 'persists', False, bool))
        self.check_voltage_persists.setChecked(self.get_config_value('voltage', 'persists', False, bool))

        self.spin_threshold.setValue(self.get_config_value('lineSearch', 'threshold', 12.0, float))

        if self.get_config_value('display', 'unit', PlotDataItem.VOLTAGE_DATA, str) == PlotDataItem.GAMMA_DATA:
            self._plot_data.data_type = PlotDataItem.GAMMA_DATA
        else:
            self._plot_data.data_type = PlotDataItem.VOLTAGE_DATA
        self.switch_data_action.setChecked(self._plot_data.data_type == PlotDataItem.GAMMA_DATA)
        self.display_gamma_or_voltage()

        self._loading = False
        return

    def setup_ui_actions(self) -> None:
        self.toolbar.open_action.triggered.connect(lambda: cast(None, self.load_data()))
        self.toolbar.clear_action.triggered.connect(self.clear)
        self.toolbar.open_ghost_action.triggered.connect(lambda: cast(None, self.load_ghost_data()))
        self.toolbar.clear_ghost_action.triggered.connect(self.clear_ghost)
        self.toolbar.differentiate_action.toggled.connect(self.calculate_second_derivative)
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

        self.switch_data_action.toggled.connect(self.on_switch_data_action_toggled)
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

        line: pg.PlotDataItem
        for line in (self.automatically_found_lines, self.user_found_lines):
            line.sigPointsClicked.connect(self.on_points_clicked)

        self._view_all_action.triggered.connect(lambda: cast(None, self._canvas.vb.autoRange(padding=0.0)))

        self.figure.sceneObj.sigMouseClicked.connect(self.on_plot_clicked)

    def adjust_table_columns(self) -> None:
        self.model_found_lines.header = (
                [_translate('main window', 'Frequency [MHz]')] +
                ([_translate('main window', 'Voltage [mV]'), _translate('main window', 'Absorption [cm⁻¹]')]
                 * (self.table_found_lines.horizontalHeader().count() // 2))
        )
        for i in range(self.table_found_lines.horizontalHeader().count()):
            self.table_found_lines.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        # change visibility of the found lines' table columns
        if self.switch_data_action.isChecked():
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

    def on_points_clicked(self, item: pg.PlotDataItem, points: Iterable[pg.SpotItem], ev: MouseClickEvent) -> None:
        if item.xData is None or item.yData is None:
            return
        if not self.trace_mode:
            return
        if ev.button() != Qt.MouseButton.LeftButton:
            return

        point: pg.SpotItem
        if ev.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            items: NDArray[np.float64] = item.scatter.data['item']
            index: NDArray[np.float64] = np.full(items.shape, True, np.bool_)
            for point in points:
                index &= (items != point)
                self.automatically_found_lines_data \
                    = self.automatically_found_lines_data[self.automatically_found_lines_data != point.pos().x()]
                self.user_found_lines_data = \
                    self.user_found_lines_data[self.user_found_lines_data != point.pos().x()]

            item.setData(item.xData[index], item.yData[index])

            # update the table
            self.model_found_lines.set_lines(self._plot_data,
                                             (self.automatically_found_lines_data,
                                              self.user_found_lines_data))

            self.toolbar.copy_trace_action.setEnabled(not self.model_found_lines.is_empty)
            self.toolbar.save_trace_action.setEnabled(not self.model_found_lines.is_empty)
            self.toolbar.clear_trace_action.setEnabled(not self.model_found_lines.is_empty)

        elif ev.modifiers() == Qt.KeyboardModifier.NoModifier:
            found_lines_frequencies: NDArray[np.float64] = self.model_found_lines.all_data[:, 0]
            selected_points: list[int] = [cast(int, np.argmin(np.abs(point.pos().x() - found_lines_frequencies)))
                                          for point in points]
            self.on_points_selected(selected_points)

    def on_button_find_lines_clicked(self) -> None:
        self.status_bar.showMessage(f'Found {self.find_lines(self.spin_threshold.value())} lines')

    def on_mouse_moved(self, event: tuple[QPointF]) -> None:
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
        if event.modifiers() != Qt.KeyboardModifier.NoModifier or event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.figure.sceneBoundingRect().contains(pos):
            return
        x_span: float = cast(float, np.ptp(self._canvas.axes['bottom']['item'].range))
        y_span: float = cast(float, np.ptp(self._canvas.axes['left']['item'].range))
        point: QPointF = self._canvas.vb.mapSceneToView(pos)
        if self._plot_line.xData is None or not self._plot_line.xData.size:
            return
        distance: NDArray[np.float64] = np.min(np.hypot((self._plot_line.xData - point.x()) / x_span,
                                               (self._plot_line.yData - point.y()) / y_span))
        if distance > 0.01:
            return
        closest_point_index: int = cast(int, np.argmin(np.hypot((self._plot_line.xData - point.x()) / x_span,
                                                                (self._plot_line.yData - point.y()) / y_span)))

        # avoid the same point to be marked several times
        if (self.user_found_lines.xData is not None
                and self.user_found_lines.yData.size
                and np.any((self.user_found_lines.xData == self._plot_line.xData[closest_point_index])
                           & (self.user_found_lines.yData == self._plot_line.yData[closest_point_index]))):
            return
        if (self.automatically_found_lines.xData is not None
                and self.automatically_found_lines.yData.size
                and np.any((self.automatically_found_lines.xData == self._plot_line.xData[closest_point_index])
                           & (self.automatically_found_lines.yData == self._plot_line.yData[closest_point_index]))):
            return

        self.user_found_lines_data = np.append(self.user_found_lines_data, self._plot_line.xData[closest_point_index])

        self.user_found_lines.setData(
            self.user_found_lines_data,
            self._plot_line.yData[self.model_found_lines.frequency_indices(self._plot_data,
                                                                           self.user_found_lines_data)]
        )

        self.model_found_lines.add_line(self._plot_data, self._plot_line.xData[closest_point_index])
        if self.settings.copy_frequency:
            copy_to_clipboard(str(1e-6 * self._plot_line.xData[closest_point_index]))
        self.toolbar.copy_trace_action.setEnabled(True)
        self.toolbar.save_trace_action.setEnabled(True)
        self.toolbar.clear_trace_action.setEnabled(True)

    def on_lim_changed(self, arg: tuple[PlotWidget, list[list[float]]]) -> None:
        if self._ignore_scale_change:
            return
        rect: list[list[float]] = arg[1]
        xlim: list[float]
        ylim: list[float]
        xlim, ylim = rect
        self._ignore_scale_change = True
        self.on_xlim_changed(xlim)
        self.on_ylim_changed(ylim)
        self._ignore_scale_change = False

    def on_points_selected(self, rows: list[int]) -> None:
        self.table_found_lines.clearSelection()
        sm: QItemSelectionModel = self.table_found_lines.selectionModel()
        row: int
        for row in rows:
            index: QModelIndex = self.model_found_lines.index(row, 0)
            sm.select(index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
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
        self.model_found_lines.set_format([(3, 1e-6), (4, 1e3), (4, np.nan, self.settings.fancy_table_numbers)])
        if self._data_mode == self.PSK_DATA_MODE and self._plot_data.frequency_span > 0.0:
            jump: float = round(self.settings.jump / self._plot_data.frequency_step) * self._plot_data.frequency_step
            self.toolbar.differentiate_action.setEnabled(0. < jump < 0.25 * self._plot_data.frequency_span)
            if not (0. < jump < 0.25 * self._plot_data.frequency_span):
                self.toolbar.differentiate_action.blockSignals(True)
                self.toolbar.differentiate_action.setChecked(False)
                self.toolbar.differentiate_action.blockSignals(False)
        self.display_gamma_or_voltage()

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
    def label(self) -> str | None:
        return self._plot_line.name()

    def set_frequency_range(self, lower_value: float, upper_value: float) -> None:
        self.figure.plotItem.setXRange(lower_value, upper_value, padding=0.0)

    def set_voltage_range(self, lower_value: float, upper_value: float) -> None:
        self.figure.plotItem.setYRange(lower_value, upper_value, padding=0.0)

    def set_plot_line_appearance(self) -> None:
        self._plot_line.setPen(pg.mkPen(self.settings.line_color, width=0.5 * self.settings.line_thickness))
        self._ghost_line.setPen(pg.mkPen(self.settings.ghost_line_color, width=0.5 * self.settings.line_thickness))
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

        x: Final[NDArray[np.float64]] = self._plot_line.xData
        y: Final[NDArray[np.float64]] = self._plot_line.yData
        if x.size < 2 or y.size < 2:
            return 0

        found_lines: NDArray[np.float64]
        if self._data_mode == self.FS_DATA_MODE:
            # re-scale the signal to the actual frequency mesh
            x_model: NDArray[np.float64] = np.arange(self.model_signal.size, dtype=x.dtype) * 0.1
            interpol = interpolate.interp1d(x_model, self.model_signal, kind=2)
            x_model_new: NDArray[np.float64] = np.arange(x_model[0], x_model[-1],
                                                         x[1] - x[0])
            y_model_new: NDArray[np.float64] = interpol(x_model_new)
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
            self.automatically_found_lines_data = x[found_lines]
            self.automatically_found_lines.setData(x[found_lines],
                                                   y[found_lines])
        else:
            self.automatically_found_lines.setData(np.empty(0), np.empty(0))
            self.automatically_found_lines_data = np.empty(0)

        # update the table
        self.model_found_lines.set_lines(self._plot_data,
                                         (self.automatically_found_lines_data, self.user_found_lines_data))

        self.toolbar.copy_trace_action.setEnabled(not self.model_found_lines.is_empty)
        self.toolbar.save_trace_action.setEnabled(not self.model_found_lines.is_empty)
        self.toolbar.clear_trace_action.setEnabled(not self.model_found_lines.is_empty)

        self.button_clear_lines.setEnabled(found_lines.size)
        self.button_next_line.setEnabled(found_lines.size)
        self.button_prev_line.setEnabled(found_lines.size)

        self._ignore_scale_change = False

        return found_lines.size

    def prev_found_line(self) -> None:
        if self.model_signal.size < 2:
            return

        init_frequency: float = self.spin_frequency_center.value()

        line_data: NDArray[np.float64] = self.automatically_found_lines.xData
        if line_data is None or not line_data.size:
            return
        i: int = cast(int, np.searchsorted(line_data, init_frequency, side='right') - 2)
        if 0 <= i < line_data.size and line_data[i] != init_frequency:
            self.spin_frequency_center.setValue(line_data[i])
            self.ensure_y_fits()

    def next_found_line(self) -> None:
        if self.model_signal.size < 2:
            return

        init_frequency: float = self.spin_frequency_center.value()

        line_data: NDArray[np.float64] = self.automatically_found_lines.xData
        if line_data is None or not line_data.size:
            return
        i: int = cast(int, np.searchsorted(line_data, init_frequency, side='left') + 1)
        if i < line_data.size and line_data[i] != init_frequency:
            self.spin_frequency_center.setValue(line_data[i])
            self.ensure_y_fits()

    def on_table_cell_double_clicked(self, index: QModelIndex) -> None:
        self.spin_frequency_center.setValue(self.model_found_lines.item(index.row(), 0))
        self.ensure_y_fits()

    def ensure_y_fits(self) -> None:
        if self._plot_line.xData is None or self._plot_line.xData.size < 2:
            return
        if self._plot_line.yData is None or self._plot_line.yData.size < 2:
            return
        x: pg.AxisItem = self._canvas.getAxis('bottom')
        y: pg.AxisItem = self._canvas.getAxis('left')
        visible_points: NDArray[np.float64] \
            = self._plot_line.yData[(self._plot_line.xData >= min(x.range)) & (self._plot_line.xData <= max(x.range))]
        if np.any(visible_points < min(y.range)):
            minimum: float = np.min(visible_points)
            self.set_voltage_range(minimum - 0.05 * (max(y.range) - minimum), max(y.range))
        if np.any(visible_points > max(y.range)):
            maximum: float = np.max(visible_points)
            self.set_voltage_range(min(y.range), maximum + 0.05 * (maximum - min(y.range)))

    def copy_found_lines(self) -> None:
        copy_to_clipboard(self.table_found_lines.stringify_table_plain_text(),
                          self.table_found_lines.stringify_table_html(),
                          Qt.TextFormat.RichText)

    def save_found_lines(self) -> None:
        def save_csv(fn: str) -> None:
            sep: str = self.settings.csv_separator
            # noinspection PyTypeChecker
            np.savetxt(fn, data,
                       delimiter=sep,
                       header=(sep.join((_translate("plot axes labels", 'Frequency'),
                                         _translate("plot axes labels", 'Voltage'),
                                         _translate("plot axes labels", 'Absorption'))) + '\n'
                               + sep.join((pg.siScale(1e6)[1] + _translate('unit', 'Hz'),
                                           pg.siScale(1e-3)[1] + _translate('unit', 'V'),
                                           _translate('unit', 'cm⁻¹')))),
                       fmt=('%.3f', '%.6f', '%.6e'), encoding='utf-8')

        def save_xlsx(fn: str) -> None:
            with pd.ExcelWriter(fn) as writer:
                df: pd.DataFrame = pd.DataFrame(data)
                df.to_excel(writer, index=False,
                            header=[_translate('main window', 'Frequency [MHz]'),
                                    _translate('main window', 'Voltage [mV]'),
                                    _translate('main window', 'Absorption [cm⁻¹]')],
                            sheet_name=self._plot_line.name() or _translate('workbook', 'Sheet1'))

        import importlib.util

        supported_formats: dict[str, str] = {'.csv': f'{self.tr("Text with separators")}(*.csv)'}
        supported_formats_callbacks: dict[str, Callable[[str], None]] = {'.csv': save_csv}
        if importlib.util.find_spec('openpyxl') is not None:
            supported_formats['.xlsx'] = f'{self.tr("Microsoft Excel")}(*.xlsx)'
            supported_formats_callbacks['.xlsx'] = save_xlsx

        filename, _filter = self.save_file_dialog(_filter=';;'.join(supported_formats.values()))
        if not filename:
            return

        f: NDArray[np.float64] = self.model_found_lines.all_data[:, 0] * 1e-6
        v: NDArray[np.float64] = self.model_found_lines.all_data[:, 1] * 1e3
        g: NDArray[np.float64] = self.model_found_lines.all_data[:, 2]
        data: NDArray[np.float64] = np.vstack((f, v, g)).transpose()

        filename_ext: str = os.path.splitext(filename)[1]
        # set the extension from the format picked (if any)
        e: str
        for e in supported_formats:
            if _filter == supported_formats[e]:
                filename_ext = e
                filename = ensure_extension(filename, filename_ext)
                break
        if filename_ext in supported_formats_callbacks:
            supported_formats_callbacks[filename_ext](filename)

    def clear_automatically_found_lines(self) -> None:
        self.automatically_found_lines.clear()
        self.automatically_found_lines_data = np.empty(0)
        self._canvas.replot()

        self.model_found_lines.set_lines(self._plot_data, self.user_found_lines_data)
        self.toolbar.copy_trace_action.setEnabled(self.model_found_lines.is_empty)
        self.toolbar.save_trace_action.setEnabled(self.model_found_lines.is_empty)
        self.toolbar.clear_trace_action.setEnabled(self.model_found_lines.is_empty)
        self.button_clear_lines.setEnabled(False)
        self.button_next_line.setEnabled(False)
        self.button_prev_line.setEnabled(False)

    def clear_found_lines(self) -> None:
        self.automatically_found_lines.clear()
        self.automatically_found_lines_data = np.empty(0)
        self.user_found_lines.clear()
        self.user_found_lines_data = np.empty(0)
        self.model_found_lines.clear()
        self.toolbar.copy_trace_action.setEnabled(False)
        self.toolbar.save_trace_action.setEnabled(False)
        self.toolbar.clear_trace_action.setEnabled(False)
        self.button_clear_lines.setEnabled(False)
        self.button_next_line.setEnabled(False)
        self.button_prev_line.setEnabled(False)
        self._canvas.replot()

    def clear(self) -> None:
        close: QMessageBox = QMessageBox()
        close.setText(_translate('main window', 'Are you sure?'))
        close.setIcon(QMessageBox.Icon.Question)
        close.setWindowIcon(self.windowIcon())
        close.setWindowTitle(_translate('main window', 'Spectrometer Data Viewer'))
        close.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if close.exec() != QMessageBox.StandardButton.Yes:
            return

        self._ghost_line.clear()
        self._plot_line.clear()
        self._ghost_data.clear()
        self._plot_data.clear()
        self.clear_found_lines()
        self.toolbar.trace_action.setChecked(False)
        self.toolbar.clear_action.setEnabled(False)
        self.toolbar.open_ghost_action.setEnabled(False)
        self.toolbar.clear_ghost_action.setEnabled(False)
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
        self.status_bar.clearMessage()
        self.setWindowTitle(_translate('main window', 'Spectrometer Data Viewer'))

    def clear_ghost(self) -> None:
        self._ghost_line.clear()
        self._ghost_data.clear()
        self.toolbar.clear_ghost_action.setEnabled(False)
        self._canvas.replot()

    def load_data(self, filename: str = '') -> bool:
        self.clear_ghost()

        if not filename:
            _filter: str
            _formats: list[str] = [
                'PSK Spectrometer (*.conf *.scandat)',
                'Fast Sweep Spectrometer (*.fmd)',
            ]
            filename, _filter = self.open_file_dialog(_filter=';;'.join(_formats))
        v: NDArray[np.float64]
        f: NDArray[np.float64]
        g: NDArray[np.float64] = np.empty(0)
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
            self.switch_data_action.setChecked(False)

        self._plot_line.setData(f,
                                (g if self.switch_data_action.isChecked() else v),
                                name=new_label)
        self._plot_data.set_data(frequency_data=f, gamma_data=g, voltage_data=v)

        min_frequency: float = f[0]
        max_frequency: float = f[-1]

        self.toolbar.clear_action.setEnabled(True)
        step: int = int(round(self.settings.jump / ((max_frequency - min_frequency) / (f.size - 1))))
        self.toolbar.differentiate_action.setEnabled(self._data_mode == self.PSK_DATA_MODE
                                                     and 0 < step < 0.25 * f.size)
        self.switch_data_action.setEnabled(self._data_mode in (self.PSK_DATA_MODE, self.PSK_WITH_JUMP_DATA_MODE))
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

        self.setWindowTitle(_translate('main window', '%s — Spectrometer Data Viewer') % filename)

        self.toolbar.open_ghost_action.setEnabled(True)

        return True

    def load_ghost_data(self, filename: str = '') -> bool:
        if not filename:
            _filter: str
            _formats: list[str] = [
                'PSK Spectrometer (*.conf *.scandat)',
                'Fast Sweep Spectrometer (*.fmd)',
            ]
            filename, _filter = self.open_file_dialog(_filter=';;'.join(_formats))
        v: NDArray[np.float64]
        f: NDArray[np.float64]
        g: NDArray[np.float64] = np.empty(0)
        jump: float
        fn: str
        if filename.casefold().endswith('.scandat'):
            fn = os.path.splitext(filename)[0]
            f, v, g, jump = load_data_scandat(filename, self)
            if f.size and v.size:
                if jump > 0.0:
                    if self._data_mode != self.PSK_WITH_JUMP_DATA_MODE:
                        return False
                else:
                    if self._data_mode != self.PSK_DATA_MODE:
                        return False
        elif filename.casefold().endswith(('.csv', '.conf')):
            fn = os.path.splitext(filename)[0]
            f, v, g, jump = load_data_csv(filename)
            if f.size and v.size:
                if jump > 0.0:
                    if self._data_mode != self.PSK_WITH_JUMP_DATA_MODE:
                        return False
                else:
                    if self._data_mode != self.PSK_DATA_MODE:
                        return False
        elif filename.casefold().endswith(('.fmd', '.frd')):
            fn = os.path.splitext(filename)[0]
            f, v = load_data_fs(filename)
            if f.size and v.size:
                if self._data_mode != self.FS_DATA_MODE:
                    return False
        else:
            return False

        if not (f.size and v.size):
            return False

        new_label: str = os.path.split(fn)[-1]

        self._ghost_line.setData(f,
                                 (g if self.switch_data_action.isChecked() else v),
                                 name=new_label)
        self._ghost_data.set_data(frequency_data=f, gamma_data=g, voltage_data=v)

        self.toolbar.clear_ghost_action.setEnabled(True)

        self.display_gamma_or_voltage()

        return True

    @property
    def trace_mode(self) -> bool:
        return self.toolbar.trace_action.isChecked()

    def actions_off(self) -> None:
        self.toolbar.trace_action.setChecked(False)

    def calculate_second_derivative(self) -> None:
        self._data_mode = self.PSK_WITH_JUMP_DATA_MODE
        self.display_gamma_or_voltage()

    def on_switch_data_action_toggled(self, new_state: bool) -> None:
        self._plot_data.data_type = PlotDataItem.GAMMA_DATA if new_state else PlotDataItem.VOLTAGE_DATA
        self._ghost_data.data_type = PlotDataItem.GAMMA_DATA if new_state else PlotDataItem.VOLTAGE_DATA
        self.set_config_value('display', 'unit', self._plot_data.data_type)
        self.display_gamma_or_voltage(new_state)

    def display_gamma_or_voltage(self, display_gamma: bool | None = None) -> None:
        if display_gamma is None:
            display_gamma = self.switch_data_action.isChecked()

        if self.toolbar.differentiate_action.isChecked():
            self._plot_data.jump = self.settings.jump
            self._ghost_data.jump = self.settings.jump
        else:
            self._plot_data.jump = np.nan
            self._ghost_data.jump = np.nan

        if display_gamma:
            self.box_voltage.setWindowTitle(_translate('main window', 'Absorption'))
        else:
            self.box_voltage.setWindowTitle(_translate('main window', 'Voltage'))

        if self._plot_data:  # something is loaded
            self._plot_line.setData(self._plot_data.x_data, self._plot_data.y_data)

            self._loading = True
            y_data: NDArray[np.float64] = self._plot_data.y_data
            min_y: float = np.min(y_data)
            max_y: float = np.max(y_data)
            if not self.check_voltage_persists.isChecked():
                self.on_ylim_changed((min_y, max_y))
            self.spin_voltage_min.setMaximum(max(max_y, self.spin_voltage_min.value()))
            self.spin_voltage_max.setMinimum(min(min_y, self.spin_voltage_max.value()))
            self._loading = False

        if self._ghost_data:  # something is loaded
            self._ghost_line.setData(self._ghost_data.x_data, self._ghost_data.y_data)

        if self.automatically_found_lines_data.size:  # something is marked
            self.automatically_found_lines.setData(
                self.automatically_found_lines_data,
                self._plot_data.y_data[
                    self.model_found_lines.frequency_indices(self._plot_data, self.automatically_found_lines_data)])
        if self.user_found_lines_data.size:  # something is marked
            self.user_found_lines.setData(
                self.user_found_lines_data,
                self._plot_data.y_data[
                    self.model_found_lines.frequency_indices(self._plot_data, self.user_found_lines_data)])

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

        # change visibility of the found lines' table columns
        if display_gamma:
            self.table_found_lines.hideColumn(1)
            self.table_found_lines.showColumn(2)
        else:
            self.table_found_lines.hideColumn(2)
            self.table_found_lines.showColumn(1)

    def save_data(self) -> None:
        if self._plot_line.yData is None:
            return

        def save_csv(fn: str) -> None:
            data: NDArray[np.float64]
            sep: str = self.settings.csv_separator
            if self.switch_data_action.isChecked():
                data = np.vstack((x * 1e-6, y)).transpose()
                # noinspection PyTypeChecker
                np.savetxt(fn, data,
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

        def save_xlsx(fn: str) -> None:
            data: NDArray[np.float64]
            with pd.ExcelWriter(fn) as writer:
                df: pd.DataFrame
                if self.switch_data_action.isChecked():
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

        import importlib.util

        supported_formats: dict[str, str] = {'.csv': f'{self.tr("Text with separators")}(*.csv)'}
        supported_formats_callbacks: dict[str, Callable[[str], None]] = {'.csv': save_csv}
        if importlib.util.find_spec('openpyxl') is not None:
            supported_formats['.xlsx'] = f'{self.tr("Microsoft Excel")}(*.xlsx)'
            supported_formats_callbacks['.xlsx'] = save_xlsx

        filename, _filter = self.save_file_dialog(_filter=';;'.join(supported_formats.values()))
        if not filename:
            return
        x: NDArray[np.float64] = self._plot_line.xData
        y: NDArray[np.float64] = self._plot_line.yData
        max_mark: float
        min_mark: float
        min_mark, max_mark = self._canvas.axes['bottom']['item'].range
        good: NDArray[np.float64] = (min_mark <= x) & (x <= max_mark)
        x = x[good]
        y = y[good]
        del good

        filename_ext: str = os.path.splitext(filename)[1]
        # set the extension from the format picked (if any)
        e: str
        for e in supported_formats:
            if _filter == supported_formats[e]:
                filename_ext = e
                filename = ensure_extension(filename, filename_ext)
                break
        if filename_ext in supported_formats_callbacks:
            supported_formats_callbacks[filename_ext](filename)

    def copy_figure(self) -> None:
        exporter = pg.exporters.ImageExporter(self._canvas)
        self.hide_cursors()
        exporter.export(copy=True)

    def save_figure(self) -> None:
        exporter = pg.exporters.ImageExporter(self._canvas)
        _filter: str = \
            _translate('file dialog', 'Image files') + ' (' + ' '.join(exporter.getSupportedImageFormats()) + ')'
        filename, _filter = self.save_file_dialog(_filter=_filter)
        if not filename:
            return
        self.hide_cursors()
        exporter.export(filename)

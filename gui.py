# -*- coding: utf-8 -*-

import os
from typing import Tuple

import pyqtgraph as pg
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QAbstractItemView, QCheckBox, QDockWidget, QFileDialog, QFormLayout, \
    QGridLayout, QMainWindow, QMessageBox, QPushButton, QStatusBar, QTableView, QVBoxLayout, QWidget

from data_model import DataModel
from settings import Settings
from toolbar import NavigationToolbar
from utils import load_icon
from valuelabel import ValueLabel


class GUI(QMainWindow):
    def __init__(self, flags=Qt.WindowFlags()):
        super().__init__(flags=flags)
        self.settings = Settings("SavSoft", "Spectrometer Viewer")

        # prevent config from being re-written while loading
        self._loading = True

        self.central_widget: QWidget = QWidget(self, flags=Qt.WindowFlags())
        self.grid_layout: QGridLayout = QGridLayout(self.central_widget)

        # Frequency box
        self.box_frequency: QDockWidget = QDockWidget(self.central_widget)
        self.box_frequency.setObjectName('box_frequency')
        self.group_frequency: QWidget = QWidget(self.box_frequency)
        self.v_layout_frequency: QVBoxLayout = QVBoxLayout(self.group_frequency)
        self.form_layout_frequency: QFormLayout = QFormLayout()
        self.grid_layout_frequency: QGridLayout = QGridLayout()

        self.spin_frequency_min: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_frequency_max: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_frequency_center: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_frequency_span: pg.SpinBox = pg.SpinBox(self.group_frequency)
        self.spin_frequency_span.setMinimum(0.01)

        self.check_frequency_persists: QCheckBox = QCheckBox(self.group_frequency)

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
        self.box_voltage.setObjectName('box_voltage')
        self.group_voltage: QWidget = QWidget(self.box_voltage)
        self.v_layout_voltage: QVBoxLayout = QVBoxLayout(self.group_voltage)
        self.form_layout_voltage: QFormLayout = QFormLayout()
        self.grid_layout_voltage: QGridLayout = QGridLayout()

        self.spin_voltage_min: pg.SpinBox = pg.SpinBox(self.group_voltage)
        self.spin_voltage_max: pg.SpinBox = pg.SpinBox(self.group_voltage)

        self.check_voltage_persists: QCheckBox = QCheckBox(self.group_voltage)

        # Zoom Y
        self.button_zoom_y_out_coarse: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_out_fine: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_in_fine: QPushButton = QPushButton(self.group_voltage)
        self.button_zoom_y_in_coarse: QPushButton = QPushButton(self.group_voltage)

        # Find Lines box
        self.box_find_lines: QDockWidget = QDockWidget(self.central_widget)
        self.box_find_lines.setObjectName('box_find_lines')
        self.group_find_lines: QWidget = QWidget(self.box_find_lines)
        self.v_layout_find_lines: QVBoxLayout = QVBoxLayout(self.group_find_lines)
        self.form_layout_find_lines: QFormLayout = QFormLayout()
        self.grid_layout_find_lines: QGridLayout = QGridLayout()
        self.spin_threshold: pg.SpinBox = pg.SpinBox(self.group_find_lines)
        self.spin_threshold.setMinimum(1.0)
        self.spin_threshold.setMaximum(1000.0)
        self.button_find_lines: QPushButton = QPushButton(self.group_find_lines)
        self.button_clear_lines: QPushButton = QPushButton(self.group_find_lines)
        self.button_prev_line: QPushButton = QPushButton(self.group_find_lines)
        self.button_next_line: QPushButton = QPushButton(self.group_find_lines)

        # Found Lines table
        self.box_found_lines: QDockWidget = QDockWidget(self.central_widget)
        self.box_found_lines.setObjectName('box_found_lines')
        self.table_found_lines: QTableView = QTableView(self.box_found_lines)
        self.model_found_lines: DataModel = DataModel(self)

        self.status_bar: QStatusBar = QStatusBar()

        # plot
        self.figure: pg.PlotWidget = pg.PlotWidget(self.central_widget)
        self.figure.setFocusPolicy(Qt.ClickFocus)
        self.plot_toolbar: NavigationToolbar = NavigationToolbar(self, parameters_icon='configure')
        self.legend: pg.GraphicsLayoutWidget = pg.GraphicsLayoutWidget()
        self.box_legend: QDockWidget = QDockWidget(self.central_widget)
        self.box_legend.setObjectName('box_legend')
        self._cursor_x: ValueLabel = ValueLabel(self.status_bar, siPrefix=True, decimals=6)
        self._cursor_y: ValueLabel = ValueLabel(self.status_bar, siPrefix=True, decimals=3)

        self.setup_ui_appearance()

    def setup_ui_appearance(self):
        _translate = QCoreApplication.translate

        pg.fn.SI_PREFIXES = _translate('si prefixes', 'y,z,a,f,p,n,µ,m, ,k,M,G,T,P,E,Z,Y').split(',')
        pg.fn.SI_PREFIXES_ASCII = pg.fn.SI_PREFIXES
        pg.fn.SI_PREFIX_EXPONENTS.update(dict([(s, (i - 8) * 3) for i, s in enumerate(pg.fn.SI_PREFIXES)]))
        if _translate('si prefix alternative micro', 'u'):
            pg.fn.SI_PREFIX_EXPONENTS[_translate('si prefix alternative micro', 'u')] = -6
        pg.fn.FLOAT_REGEX = pg.re.compile(
            r'(?P<number>[+-]?((((\d+(\.\d*)?)|(\d*\.\d+))([eE][+-]?\d+)?)'
            r'|(nan|NaN|NAN|inf|Inf|INF)))\s*'
            r'((?P<siPrefix>[u(' + '|'.join(pg.fn.SI_PREFIXES) + r')]?)(?P<suffix>\w.*))?$')
        pg.fn.INT_REGEX = pg.re.compile(r'(?P<number>[+-]?\d+)\s*'
                                        r'(?P<siPrefix>[u(' + '|'.join(pg.fn.SI_PREFIXES) + r')]?)(?P<suffix>.*)$')

        self.setWindowIcon(load_icon('main'))

        self.form_layout_frequency.addRow(_translate('main window', 'Minimum') + ':', self.spin_frequency_min)
        self.form_layout_frequency.addRow(_translate('main window', 'Maximum') + ':', self.spin_frequency_max)
        self.form_layout_frequency.addRow(_translate('main window', 'Center') + ':', self.spin_frequency_center)
        self.form_layout_frequency.addRow(_translate('main window', 'Span') + ':', self.spin_frequency_span)

        self.grid_layout_frequency.addWidget(self.check_frequency_persists, 0, 0, 1, 4)
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

        self.form_layout_voltage.addRow(_translate('main window', 'Minimum') + ':', self.spin_voltage_min)
        self.form_layout_voltage.addRow(_translate('main window', 'Maximum') + ':', self.spin_voltage_max)

        self.grid_layout_voltage.addWidget(self.check_voltage_persists, 0, 0, 1, 4)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_coarse, 1, 0)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_fine, 1, 1)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_fine, 1, 2)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_coarse, 1, 3)

        self.v_layout_voltage.addLayout(self.form_layout_voltage)
        self.v_layout_voltage.addLayout(self.grid_layout_voltage)

        self.form_layout_find_lines.addRow(_translate('main window', 'Search threshold') + ':', self.spin_threshold)
        self.grid_layout_find_lines.addWidget(self.button_find_lines, 0, 0, 1, 2)
        self.grid_layout_find_lines.addWidget(self.button_clear_lines, 1, 0, 1, 2)
        self.grid_layout_find_lines.addWidget(self.button_prev_line, 2, 0)
        self.grid_layout_find_lines.addWidget(self.button_next_line, 2, 1)

        self.v_layout_find_lines.addLayout(self.form_layout_find_lines)
        self.v_layout_find_lines.addLayout(self.grid_layout_find_lines)

        _value_label_interaction_flags = (Qt.LinksAccessibleByKeyboard
                                          | Qt.LinksAccessibleByMouse
                                          | Qt.TextBrowserInteraction
                                          | Qt.TextSelectableByKeyboard
                                          | Qt.TextSelectableByMouse)

        self.box_legend.setWidget(self.legend)
        self.box_legend.setFeatures(self.box_legend.features() & ~self.box_legend.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.box_legend)

        # TODO: adjust size when undocked
        self.box_frequency.setWidget(self.group_frequency)
        self.box_frequency.setFeatures(self.box_frequency.features() & ~self.box_frequency.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.box_frequency)

        self.box_voltage.setWidget(self.group_voltage)
        self.box_voltage.setFeatures(self.box_voltage.features() & ~self.box_voltage.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.box_voltage)

        self.box_find_lines.setWidget(self.group_find_lines)
        self.box_find_lines.setFeatures(self.box_find_lines.features() & ~self.box_find_lines.DockWidgetClosable)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.box_find_lines)

        self.box_found_lines.setWidget(self.table_found_lines)
        self.box_found_lines.setFeatures(self.box_found_lines.features() & ~self.box_found_lines.DockWidgetClosable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.box_found_lines)

        self.grid_layout.addWidget(self.figure)

        self.setCentralWidget(self.central_widget)
        self.setWindowTitle(_translate('main window', 'Spectrometer Data Viewer'))
        self.setStatusBar(self.status_bar)

        self.status_bar.addWidget(self._cursor_x)
        self.status_bar.addWidget(self._cursor_y)

        self._cursor_x.suffix = _translate('unit', 'Hz')
        self._cursor_y.suffix = _translate('unit', 'V')

        self.box_legend.setWindowTitle(_translate('main window', 'Legend'))

        self.box_frequency.setWindowTitle(_translate('main window', 'Frequency'))
        self.check_frequency_persists.setText(_translate('main window', 'Keep frequency range'))

        self.button_zoom_x_out_coarse.setText(_translate('main window', '−50%'))
        self.button_zoom_x_out_fine.setText(_translate('main window', '−10%'))
        self.button_zoom_x_in_fine.setText(_translate('main window', '+10%'))
        self.button_zoom_x_in_coarse.setText(_translate('main window', '+50%'))

        self.button_move_x_left_coarse.setText('−' + pg.siFormat(5e8, suffix=_translate('unit', 'Hz')))
        self.button_move_x_left_fine.setText('−' + pg.siFormat(5e7, suffix=_translate('unit', 'Hz')))
        self.button_move_x_right_fine.setText('+' + pg.siFormat(5e7, suffix=_translate('unit', 'Hz')))
        self.button_move_x_right_coarse.setText('+' + pg.siFormat(5e8, suffix=_translate('unit', 'Hz')))

        self.box_voltage.setWindowTitle(_translate('main window', 'Voltage'))
        self.check_voltage_persists.setText(_translate('main window', 'Keep voltage range'))

        self.button_zoom_y_out_coarse.setText(_translate('main window', '−50%'))
        self.button_zoom_y_out_fine.setText(_translate('main window', '−10%'))
        self.button_zoom_y_in_fine.setText(_translate('main window', '+10%'))
        self.button_zoom_y_in_coarse.setText(_translate('main window', '+50%'))

        self.box_find_lines.setWindowTitle(_translate('main window', 'Find Lines'))
        self.group_find_lines.setToolTip(_translate('main window',
                                                    'Try to detect lines automatically'))
        self.button_find_lines.setText(_translate('main window', 'Find Lines'))
        self.button_clear_lines.setText(_translate('main window', 'Clear Lines'))
        self.button_prev_line.setText(_translate('main window', 'Previous Line'))
        self.button_next_line.setText(_translate('main window', 'Next Line'))

        self.box_found_lines.setWindowTitle(_translate('main window', 'Found Lines'))
        self.model_found_lines.set_format([(3, 1e-6), (4, 1.)])
        self.table_found_lines.setModel(self.model_found_lines)
        self.table_found_lines.setMouseTracking(True)
        self.table_found_lines.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.table_found_lines.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_found_lines.setDropIndicatorShown(False)
        self.table_found_lines.setDragDropOverwriteMode(False)
        self.table_found_lines.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_found_lines.setCornerButtonEnabled(False)
        self.table_found_lines.setSortingEnabled(True)
        self.table_found_lines.setAlternatingRowColors(True)
        self.table_found_lines.horizontalHeader().setDefaultSectionSize(90)
        self.table_found_lines.horizontalHeader().setHighlightSections(False)
        self.table_found_lines.horizontalHeader().setStretchLastSection(True)
        self.table_found_lines.verticalHeader().setVisible(False)
        self.table_found_lines.verticalHeader().setHighlightSections(False)

        opts = {
            'suffix': _translate('unit', 'Hz'),
            'siPrefix': True,
            'decimals': 6,
            'dec': True,
            'compactHeight': False,
            'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'
        }
        self.spin_frequency_min.setOpts(**opts)
        self.spin_frequency_max.setOpts(**opts)
        self.spin_frequency_center.setOpts(**opts)
        self.spin_frequency_span.setOpts(**opts)
        opts = {
            'suffix': _translate('unit', 'V'),
            'siPrefix': True,
            'decimals': 3,
            'dec': True,
            'compactHeight': False,
            'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'
        }
        self.spin_voltage_min.setOpts(**opts)
        self.spin_voltage_max.setOpts(**opts)

        self.spin_threshold.setOpts(compactHeight=False)

        self.adjustSize()

    def closeEvent(self, event):
        """ senseless joke in the loop """
        _translate = QCoreApplication.translate
        close_code = QMessageBox.No
        while close_code == QMessageBox.No:
            close = QMessageBox()
            close.setText(_translate('main window', 'Are you sure?'))
            close.setIcon(QMessageBox.Question)
            close.setWindowIcon(self.windowIcon())
            close.setWindowTitle(self.windowTitle())
            close.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            close_code = close.exec()

            if close_code == QMessageBox.Yes:
                self.settings.setValue('windowGeometry', self.saveGeometry())
                self.settings.setValue('windowState', self.saveState())
                self.settings.sync()
                event.accept()
            elif close_code == QMessageBox.Cancel:
                event.ignore()
        return

    def get_config_value(self, section: str, key: str, default, _type):
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

    def set_config_value(self, section: str, key: str, value):
        if self._loading:
            return
        self.settings.beginGroup(section)
        if isinstance(value, pg.np.float64):
            value = float(value)
        # print(section, key, value, type(value))
        self.settings.setValue(key, value)
        self.settings.endGroup()

    def open_file_dialog(self, _filter=''):
        directory = self.get_config_value('open', 'location', '', str)
        # native dialog misbehaves when running inside snap but Qt dialog is tortoise-like in NT
        options = QFileDialog.DontUseNativeDialog if os.name != 'nt' else QFileDialog.DontUseSheet
        filename, _filter = QFileDialog.getOpenFileName(filter=_filter,
                                                        directory=directory,
                                                        options=options)
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

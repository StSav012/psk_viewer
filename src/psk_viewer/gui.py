import re
import sys
from pathlib import Path
from typing import Any, Final, TypeVar, cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from pyqtgraph import functions as fn
from qtpy.QtCore import (
    QCoreApplication,
    QLibraryInfo,
    QLocale,
    QObject,
    QTranslator,
    Qt,
)
from qtpy.QtGui import QAction
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDockWidget,
    QFormLayout,
    QGridLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .data_model import DataModel
from .found_lines_model import FoundLinesModel
from .settings import Settings
from .table_view import TableView
from .toolbar import NavigationToolbar
from .utils import find_qm_files, load_icon
from .valuelabel import ValueLabel

__all__ = ["GUI"]

_translate = QCoreApplication.translate
_T = TypeVar("_T")
_sentinel: Final[object] = object()


class GUI(QMainWindow):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)
        self.setObjectName("mainWindow")

        self.settings: Settings = Settings("SavSoft", "Spectrometer Viewer", self)

        # prevent config from being re-written while loading
        self._loading: bool = True

        self.central_widget: QWidget = QWidget(self)
        self.grid_layout: QGridLayout = QGridLayout(self.central_widget)

        # Frequency box
        self.box_frequency: QDockWidget = QDockWidget(self.central_widget)
        self.box_frequency.setObjectName("box_frequency")
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
        self.box_voltage.setObjectName("box_voltage")
        self.group_voltage: QWidget = QWidget(self.box_voltage)
        self.v_layout_voltage: QVBoxLayout = QVBoxLayout(self.group_voltage)
        self.form_layout_voltage: QFormLayout = QFormLayout()
        self.grid_layout_voltage: QGridLayout = QGridLayout()

        self.spin_voltage_min: pg.SpinBox = pg.SpinBox(self.group_voltage)
        self.spin_voltage_max: pg.SpinBox = pg.SpinBox(self.group_voltage)

        self.check_voltage_persists: QCheckBox = QCheckBox(self.group_voltage)

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

        self.toolbar: NavigationToolbar = NavigationToolbar(self)
        self.status_bar: QStatusBar = QStatusBar()

        # plot
        self.figure: pg.PlotWidget = pg.PlotWidget(self.central_widget)
        self._canvas: pg.PlotItem = self.figure.getPlotItem()
        self._cursor_x: ValueLabel = ValueLabel(
            self.status_bar, siPrefix=True, decimals=6
        )
        self._cursor_y: ValueLabel = ValueLabel(
            self.status_bar, siPrefix=True, decimals=3
        )

        self._view_all_action: QAction = QAction()

        self._setup_appearance()

    def _setup_appearance(self) -> None:
        fn.SI_PREFIXES = _translate(
            "si prefixes", "y,z,a,f,p,n,µ,m, ,k,M,G,T,P,E,Z,Y"
        ).split(",")
        fn.SI_PREFIXES_ASCII = fn.SI_PREFIXES
        fn.SI_PREFIX_EXPONENTS.update(
            dict([(s, (i - 8) * 3) for i, s in enumerate(fn.SI_PREFIXES)])
        )
        if _translate("si prefix alternative micro", "u"):
            fn.SI_PREFIX_EXPONENTS[_translate("si prefix alternative micro", "u")] = -6
        fn.FLOAT_REGEX = re.compile(
            r"(?P<number>[+-]?((((\d+(\.\d*)?)|(\d*\.\d+))([eE][+-]?\d+)?)"
            r"|(nan|NaN|NAN|inf|Inf|INF)))\s*"
            r"((?P<siPrefix>[u(" + "|".join(fn.SI_PREFIXES) + r")]?)(?P<suffix>\w.*))?$"
        )
        fn.INT_REGEX = re.compile(
            r"(?P<number>[+-]?\d+)\s*"
            r"(?P<siPrefix>[u(" + "|".join(fn.SI_PREFIXES) + r")]?)(?P<suffix>.*)$"
        )

        self.setWindowIcon(load_icon(self, "main"))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.form_layout_frequency.addRow(self.tr("Minimum:"), self.spin_frequency_min)
        self.form_layout_frequency.addRow(self.tr("Maximum:"), self.spin_frequency_max)
        self.form_layout_frequency.addRow(
            self.tr("Center:"), self.spin_frequency_center
        )
        self.form_layout_frequency.addRow(self.tr("Span:"), self.spin_frequency_span)

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

        self.form_layout_voltage.addRow(self.tr("Minimum:"), self.spin_voltage_min)
        self.form_layout_voltage.addRow(self.tr("Maximum:"), self.spin_voltage_max)

        self.grid_layout_voltage.addWidget(self.check_voltage_persists, 0, 0, 1, 4)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_coarse, 1, 0)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_fine, 1, 1)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_fine, 1, 2)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_coarse, 1, 3)

        self.v_layout_voltage.addWidget(self.switch_data_action)
        self.switch_data_action.setEnabled(False)
        self.switch_data_action.setCheckable(True)
        self.switch_data_action.setShortcut("Ctrl+`")
        self.switch_data_action.setText(self.tr("Show Absorption"))
        self.switch_data_action.setToolTip(
            self.tr("Switch Y data between absorption and voltage")
        )

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

        self.grid_layout.addWidget(self.figure)

        self.setCentralWidget(self.central_widget)
        if __version__:
            self.setWindowTitle(
                self.tr("Spectrometer Data Viewer (version {0})").format(__version__)
            )
        else:
            self.setWindowTitle(self.tr("Spectrometer Data Viewer"))
        self.setStatusBar(self.status_bar)

        self.status_bar.addWidget(self._cursor_x)
        self.status_bar.addWidget(self._cursor_y)

        self._cursor_x.suffix = _translate("unit", "Hz")
        self._cursor_y.suffix = _translate("unit", "V")

        self.box_frequency.setWindowTitle(self.tr("Frequency"))
        self.check_frequency_persists.setText(self.tr("Keep frequency range"))

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
        self.check_voltage_persists.setText(self.tr("Keep voltage range"))

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
        self.button_clear_automatically_found_lines.setEnabled(False)
        self.button_next_found_line.setEnabled(False)
        self.button_prev_found_line.setEnabled(False)

        self.box_found_lines.setWindowTitle(self.tr("Found Lines"))
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
            "suffix": _translate("unit", "Hz"),
            "siPrefix": True,
            "decimals": 6,
            "dec": True,
            "compactHeight": False,
            "format": "{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
        }
        self.spin_frequency_min.setOpts(**opts)
        self.spin_frequency_max.setOpts(**opts)
        self.spin_frequency_center.setOpts(**opts)
        self.spin_frequency_span.setOpts(**opts)
        opts = {
            "suffix": _translate("unit", "V"),
            "siPrefix": True,
            "decimals": 3,
            "dec": True,
            "compactHeight": False,
            "format": "{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
        }
        self.spin_voltage_min.setOpts(**opts)
        self.spin_voltage_max.setOpts(**opts)

        self.spin_threshold.setOpts(compactHeight=False)

        self.figure.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._install_translation()

        self.adjustSize()

    def _setup_translation(self) -> None:
        fn.SI_PREFIXES = _translate(
            "si prefixes", "y,z,a,f,p,n,µ,m, ,k,M,G,T,P,E,Z,Y"
        ).split(",")
        fn.SI_PREFIXES_ASCII = fn.SI_PREFIXES
        fn.SI_PREFIX_EXPONENTS.update(
            dict([(s, (i - 8) * 3) for i, s in enumerate(fn.SI_PREFIXES)])
        )
        if _translate("si prefix alternative micro", "u"):
            fn.SI_PREFIX_EXPONENTS[_translate("si prefix alternative micro", "u")] = -6

        cast(
            QLabel, self.form_layout_frequency.labelForField(self.spin_frequency_min)
        ).setText(self.tr("Minimum:"))
        cast(
            QLabel, self.form_layout_frequency.labelForField(self.spin_frequency_max)
        ).setText(self.tr("Maximum:"))
        cast(
            QLabel, self.form_layout_frequency.labelForField(self.spin_frequency_center)
        ).setText(self.tr("Center:"))
        cast(
            QLabel, self.form_layout_frequency.labelForField(self.spin_frequency_span)
        ).setText(self.tr("Span:"))

        cast(
            QLabel, self.form_layout_voltage.labelForField(self.spin_voltage_min)
        ).setText(self.tr("Minimum:"))
        cast(
            QLabel, self.form_layout_voltage.labelForField(self.spin_voltage_max)
        ).setText(self.tr("Maximum:"))

        self.switch_data_action.setText(self.tr("Show Absorption"))
        self.switch_data_action.setToolTip(
            self.tr("Switch Y data between absorption and voltage")
        )

        cast(
            QLabel, self.form_layout_find_lines.labelForField(self.spin_threshold)
        ).setText(self.tr("Search threshold:"))

        if __version__:
            self.setWindowTitle(
                self.tr("Spectrometer Data Viewer (version {0})").format(__version__)
            )
        else:
            self.setWindowTitle(self.tr("Spectrometer Data Viewer"))

        self._cursor_x.suffix = _translate("unit", "Hz")
        self._cursor_y.suffix = _translate("unit", "V")

        self.box_frequency.setWindowTitle(self.tr("Frequency"))
        self.check_frequency_persists.setText(self.tr("Keep frequency range"))

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
        self.check_voltage_persists.setText(self.tr("Keep voltage range"))

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

        self.spin_frequency_min.setSuffix(_translate("unit", "Hz"))
        self.spin_frequency_max.setSuffix(_translate("unit", "Hz"))
        self.spin_frequency_center.setSuffix(_translate("unit", "Hz"))
        self.spin_frequency_span.setSuffix(_translate("unit", "Hz"))

        self.spin_voltage_min.setSuffix(_translate("unit", "V"))
        self.spin_voltage_max.setSuffix(_translate("unit", "V"))

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

        self._canvas.vb.menu.setTitle(_translate("menu", "Plot Options"))

    def _install_translation(self) -> None:
        qt_translations_path: str = QLibraryInfo.path(
            QLibraryInfo.LibraryPath.TranslationsPath
        )
        qt_translator: QTranslator
        translator: QTranslator
        if self.settings.translation_path is not None:
            translator = QTranslator(self)
            if translator.load(str(self.settings.translation_path)):
                new_locale: QLocale = QLocale(translator.language())

                # remove existing translators
                for child in self.children():
                    if isinstance(child, QTranslator) and child is not translator:
                        QApplication.removeTranslator(child)

                qt_translator = QTranslator(self)
                if qt_translator.load(new_locale, "qtbase", "_", qt_translations_path):
                    QApplication.installTranslator(qt_translator)

                QApplication.installTranslator(translator)
                self.setLocale(new_locale)
        else:
            current_locale: QLocale = self.locale()
            ui_languages: frozenset[str] = frozenset(
                [
                    *current_locale.uiLanguages(),
                    *map(lambda s: s.replace("-", "_"), current_locale.uiLanguages()),
                ]
            )
            for qm_file in find_qm_files(
                root=qt_translations_path, exclude=[sys.exec_prefix]
            ):
                qt_translator = QTranslator(self)
                if (
                    qt_translator.load(str(qm_file))
                    and qt_translator.language() in ui_languages
                ):
                    QApplication.installTranslator(qt_translator)
            for qm_file in find_qm_files(
                root=Path(__file__).parent,
                exclude=[qt_translations_path, sys.exec_prefix],
            ):
                translator = QTranslator(self)
                if (
                    translator.load(str(qm_file))
                    and translator.language() in ui_languages
                ):
                    QApplication.installTranslator(translator)
        self._setup_translation()

    def get_config_value(
        self,
        section: str,
        key: str,
        default: _T,
        _type: type[_T] | _sentinel = _sentinel,
    ) -> _T:
        if section not in self.settings.childGroups():
            return default
        if _type is _sentinel:
            _type = type(default)
        with self.settings.section(section):
            # print(section, key)
            try:
                v: Any
                if issubclass(_type, QObject):
                    v = self.settings.value(key, default)
                else:
                    v = self.settings.value(key, default, _type)
                if not isinstance(v, _type):
                    v = _type(v)
                return v
            except (TypeError, ValueError):
                return default

    def set_config_value(self, section: str, key: str, value: object) -> None:
        if self._loading:
            return
        with self.settings.section(section):
            if isinstance(value, np.float64):
                value = float(value)
            if isinstance(value, Path):
                value = str(value)
            # print(section, key, value, type(value))
            self.settings.setValue(key, value)

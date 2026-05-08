import re
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Literal, TypeVar, cast

import numpy as np
import pyqtgraph as pg  # type: ignore
from pyqtgraph import functions as fn
from pyqtgraph.exporters import ImageExporter
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
    QApplication,
    QGridLayout,
    QMainWindow,
    QStatusBar,
    QWidget,
)

from ... import __version__
from ...settings import Settings
from ...utils import find_qm_files, load_icon
from ...widgets.file_dialog import OpenFileDialog, SaveFileDialog
from ...widgets.valuelabel import ValueLabel

__all__ = ["GUI"]

_translate = QCoreApplication.translate
_T = TypeVar("_T")


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
        self._loading: Lock = Lock()

        self.central_widget: QWidget = QWidget(self)
        self.grid_layout: QGridLayout = QGridLayout(self.central_widget)

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
        # cross-hair
        self._crosshair_v_line: pg.InfiniteLine = pg.InfiniteLine(
            angle=90, movable=False
        )
        self._crosshair_h_line: pg.InfiniteLine = pg.InfiniteLine(
            angle=0, movable=False
        )

        self._cursor_balloon: pg.TextItem = pg.TextItem()

        self._view_all_action: QAction = QAction()

        self._open_table_dialog: OpenFileDialog = OpenFileDialog(
            settings=self.settings,
            supported_mimetype_filters=[
                OpenFileDialog.SupportedMimetypeItem(
                    required_packages=[],
                    file_extension=".txt",
                ),
                OpenFileDialog.SupportedMimetypeItem(
                    required_packages=[],
                    file_extension=".csv",
                ),
                OpenFileDialog.SupportedMimetypeItem(
                    required_packages=["openpyxl"],
                    file_extension=".xlsx",
                ),
            ],
            parent=self,
        )
        self._open_data_dialog: OpenFileDialog = OpenFileDialog(
            settings=self.settings,
            supported_name_filters=[
                OpenFileDialog.SupportedNameFilterItem(
                    required_packages=[],
                    file_extensions=[".conf", ".scandat"],
                    name=_translate("file type", "PSK Spectrometer"),
                ),
                OpenFileDialog.SupportedNameFilterItem(
                    required_packages=[],
                    file_extensions=[".fmd"],
                    name=_translate("file type", "Fast Sweep Spectrometer"),
                ),
            ],
            parent=self,
        )
        self._save_table_dialog: SaveFileDialog = SaveFileDialog(
            settings=self.settings,
            supported_mimetype_filters=[
                SaveFileDialog.SupportedMimetypeItem(
                    required_packages=[],
                    file_extension=".csv",
                ),
                SaveFileDialog.SupportedMimetypeItem(
                    required_packages=["openpyxl"],
                    file_extension=".xlsx",
                ),
            ],
            parent=self,
        )
        self._save_image_dialog: SaveFileDialog = SaveFileDialog(
            settings=self.settings,
            supported_mimetype_filters=[
                SaveFileDialog.SupportedMimetypeItem(
                    required_packages=[],
                    file_extension=ext.lstrip("*"),
                )
                for ext in ImageExporter.getSupportedImageFormats()
            ],
            parent=self,
        )

    def _setup_appearance(self) -> None:
        self.setWindowIcon(load_icon(self, "main"))
        self.setCentralWidget(self.central_widget)

        self.setStatusBar(self.status_bar)

        self.status_bar.addWidget(self._cursor_x)
        self.status_bar.addWidget(self._cursor_y)

        self.grid_layout.addWidget(self.figure)
        self.figure.addItem(self._cursor_balloon)
        self.figure.plotItem.addItem(self._crosshair_v_line, ignoreBounds=True)
        self.figure.plotItem.addItem(self._crosshair_h_line, ignoreBounds=True)

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
        fn.FLOAT_REGEX = re.compile(
            r"(?P<number>[+-]?((((\d+(\.\d*)?)|(\d*\.\d+))([eE][+-]?\d+)?)"
            r"|(nan|NaN|NAN|inf|Inf|INF)))\s*"
            r"((?P<siPrefix>[u(" + "|".join(fn.SI_PREFIXES) + r")]?)(?P<suffix>\w.*))?$"
        )
        fn.INT_REGEX = re.compile(
            r"(?P<number>[+-]?\d+)\s*"
            r"(?P<siPrefix>[u(" + "|".join(fn.SI_PREFIXES) + r")]?)(?P<suffix>.*)$"
        )

        if __version__:
            self.setWindowTitle(
                self.tr("Spectrometer Data Viewer (version {0})").format(__version__)
            )
        else:
            self.setWindowTitle(self.tr("Spectrometer Data Viewer"))

        if (vb := self._canvas.vb) is not None and (menu := vb.menu) is not None:
            menu.setTitle(_translate("menu", "Plot Options"))

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
                        QApplication.removeTranslator(cast(QTranslator, child))

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
        _type: type[_T] | Literal[None] = None,
    ) -> _T:
        if section not in self.settings.childGroups():
            return default
        if _type is None:
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
        if self._loading.locked():
            return
        with self.settings.section(section):
            if isinstance(value, np.generic):
                value = value.item()
            elif isinstance(value, Path):
                value = str(value)
            # print(section, key, value, type(value))
            self.settings.setValue(key, value)

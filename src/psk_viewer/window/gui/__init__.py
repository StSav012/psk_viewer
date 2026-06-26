import abc
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

# noinspection PyPackageRequirements
import numpy as np
import pyqtgraph as pg  # type: ignore

# noinspection PyPackageRequirements
from numpy.typing import NDArray
from pyqtgraph import functions as fn
from pyqtgraph.exporters import ImageExporter
from qtpy.QtCore import (
    QCoreApplication,
    QEvent,
    QLibraryInfo,
    QLocale,
    QObject,
    QPointF,
    QRectF,
    QTranslator,
    Qt,
    Slot,
)
from qtpy.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QPalette,
    QPen,
    QShowEvent,
)
from qtpy.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QWidget,
)

from ... import __version__
from ...plot_data_item import PlotDataItem
from ...settings import Settings
from ...utils import DataMode, find_qm_files, load_icon, the
from ...widgets.file_dialog import OpenFileDialog, SaveFileDialog
from ...widgets.valuelabel import ValueLabel

__all__ = ["GUI"]

_translate = QCoreApplication.translate
_T = TypeVar("_T")


class QABCMeta(type(QObject), abc.ABCMeta):
    pass


class GUI(QMainWindow, abc.ABC, metaclass=QABCMeta):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)
        self.setObjectName("mainWindow")

        self._data_mode: DataMode = DataMode.unknown

        self.settings: Settings = Settings("SavSoft", "Spectrometer Viewer", self)

        # prevent config from being re-written while loading
        self._loading: Lock = Lock()
        self._ignore_scale_change: Lock = Lock()

        self.status_bar: QStatusBar = QStatusBar()

        # plot
        self.figure: pg.PlotWidget = pg.PlotWidget(self)
        self._canvas: pg.PlotItem = self.figure.getPlotItem()

        self._plot_line: pg.PlotDataItem = self.figure.plot(np.empty(0), name="")
        self._plot_data: PlotDataItem = PlotDataItem()
        self._ghost_line: pg.PlotDataItem = self.figure.plot(np.empty(0), name="")
        self._ghost_data: PlotDataItem = PlotDataItem()

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
                    required_packages=[],
                    file_extension=".rtf",
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

        self._mouse_moved_signal_proxy: pg.SignalProxy = pg.SignalProxy(
            cast(pg.GraphicsScene, self.figure.scene()).sigMouseMoved,
            rateLimit=10,
            slot=self.on_mouse_moved,
        )
        self._axis_range_changed_signal_proxy: pg.SignalProxy = pg.SignalProxy(
            self.figure.sigRangeChanged, rateLimit=20, slot=self.on_lim_changed
        )

        with suppress(AttributeError):
            # `colorSchemeChanged` exists starting from Qt6
            QGuiApplication.styleHints().colorSchemeChanged.connect(
                self.on_color_scheme_changed
            )

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.PaletteChange:
            self._setup_colors()
        return super().event(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        close_code: int
        if self._data_mode == DataMode.unknown:  # nothing is loaded
            close_code = QMessageBox.StandardButton.Yes
        else:
            # senseless joke in the loop
            close: QMessageBox = QMessageBox(self)
            close.setText(self.tr("Are you sure?"))
            close.setIcon(QMessageBox.Icon.Question)
            close.setWindowIcon(self.windowIcon())
            close.setWindowTitle(self.tr("Spectrometer Data Viewer"))
            close.setStandardButtons(
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel
            )
            close_code = QMessageBox.StandardButton.No
            while close_code == QMessageBox.StandardButton.No:
                close_code = close.exec()

        if close_code == QMessageBox.StandardButton.Yes:
            self.settings.save(self)
            self.settings.sync()

            from ... import windows

            windows.remove(self)

            event.accept()
        elif close_code == QMessageBox.StandardButton.Cancel:
            event.ignore()

    def showEvent(self, event: QShowEvent) -> None:

        from ... import windows

        windows.append(self)

        window: QMainWindow
        while windows:
            for window in windows:
                if window.isHidden():
                    window.close()
                    break
            else:
                break

        event.accept()

    def _setup_colors(self) -> None:
        if TYPE_CHECKING:
            from typing import TypedDict

            class AxisDict(TypedDict):
                item: pg.AxisItem
                pos: tuple[int, int]

        palette: QPalette = self.palette()
        base_color: QColor = (
            self.settings.axis_base_color
            if self.settings.axis_custom_colors
            else palette.base().color()
        )
        text_color: QColor = (
            self.settings.axis_text_color
            if self.settings.axis_custom_colors
            else palette.text().color()
        )
        self.figure.setBackground(pg.mkBrush(base_color))
        ax_d: AxisDict
        for ax_d in self._canvas.axes.values():
            ax: pg.AxisItem = ax_d["item"]
            pen: QPen = QPen()
            pen.setColor(text_color)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setWidthF(self.settings.axis_thickness)
            ax.setPen(pen)
            ax.setTextPen(text_color)
        self._cursor_balloon.setColor(text_color)

    def _setup_appearance(self) -> None:
        self.setWindowIcon(load_icon(self, "main"))
        self.setCentralWidget(self.figure)

        self.setStatusBar(self.status_bar)

        self.status_bar.addWidget(self._cursor_x)
        self.status_bar.addWidget(self._cursor_y)

        self.figure.addItem(self._cursor_balloon)
        self._canvas.addItem(self._crosshair_v_line, ignoreBounds=True)
        self._canvas.addItem(self._crosshair_h_line, ignoreBounds=True)
        self._canvas.getViewBox().setDefaultPadding(0.0)

    def _setup_translation(self) -> None:
        fn.SI_PREFIXES = _translate(
            "si prefixes", "y,z,a,f,p,n,µ,m, ,k,M,G,T,P,E,Z,Y"
        ).split(",")
        fn.SI_PREFIXES_ASCII = fn.SI_PREFIXES
        fn.SI_PREFIX_EXPONENTS.update(
            dict([(s, (i - 8) * 3) for i, s in enumerate(fn.SI_PREFIXES)])
        )
        if alt_micro := _translate("si prefix alternative micro", "u"):
            fn.SI_PREFIX_EXPONENTS[alt_micro] = -6
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

        if (menu := self._canvas.getViewBox().getMenu(self._canvas)) is not None:
            menu.setTitle(_translate("menu", "Plot Options"))

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
                root=Path(*Path(__file__).parts[: -(__package__.count(".") + 1)]),
                exclude=[qt_translations_path, sys.exec_prefix],
            ):
                translator = QTranslator(self)
                if (
                    translator.load(str(qm_file))
                    and translator.language() in ui_languages
                ):
                    QApplication.installTranslator(translator)

    @contextmanager
    def show_loading(self) -> Iterator[None]:
        last_cursor: QCursor = self.cursor()
        try:
            self.setDisabled(True)
            self.setCursor(Qt.CursorShape.WaitCursor)
            self.repaint()
            yield None
        finally:
            self.setCursor(last_cursor)
            self.setEnabled(True)

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

    @Slot(Qt.ColorScheme)
    def on_color_scheme_changed(self, _: Qt.ColorScheme) -> None:
        self._setup_colors()

    def set_axis_line_appearance(self) -> None:
        def _(axis: pg.AxisItem) -> None:
            styles: dict[QFont.Style, str] = {
                QFont.Style.StyleNormal: "normal",
                QFont.Style.StyleItalic: "italic",
                QFont.Style.StyleOblique: "oblique",
            }
            variants: dict[QFont.Capitalization, str] = {
                QFont.Capitalization.MixedCase: "normal",
                QFont.Capitalization.AllUppercase: "normal",  # see transforms below
                QFont.Capitalization.AllLowercase: "normal",  # see transforms below
                QFont.Capitalization.SmallCaps: "small-caps",
                QFont.Capitalization.Capitalize: "titling-caps",
            }
            transforms: dict[QFont.Capitalization, str] = {
                QFont.Capitalization.MixedCase: "none",
                QFont.Capitalization.AllUppercase: "uppercase",
                QFont.Capitalization.AllLowercase: "lowercase",
                QFont.Capitalization.SmallCaps: "none",  # see variants above
                QFont.Capitalization.Capitalize: "capitalize",
            }
            decorations: dict[tuple[bool, bool, bool], str] = {
                (False, False, False): "none",
                (False, False, True): "overline",
                (False, True, False): "underline",
                (False, True, True): "underline overline",
                (True, False, False): "line-through",
                (True, False, True): "overline line-through",
                (True, True, False): "underline line-through",
                (True, True, True): "underline overline line-through",
            }
            font: QFont = self.settings.axis_label_font
            axis.labelStyle.update(
                {
                    "font-family": font.family(),
                    "font-size": f"{font.pointSizeF()}pt",
                    "font-stretch": f"{font.stretch()}%",
                    "font-style": styles[font.style()],
                    "font-weight": f"{font.weight()}",
                    "font-variant-caps": variants[font.capitalization()],
                    "text-decoration-line": decorations[
                        (font.strikeOut(), font.underline(), font.overline())
                    ],
                    "text-transform": transforms[font.capitalization()],
                }
            )
            axis.setTickFont(self.settings.axis_tick_font)
            axis.setFont(self.settings.axis_label_font)
            pen: QPen = axis.pen()
            pen.setWidthF(self.settings.axis_thickness)
            axis.setPen(pen)

        _(self._canvas.getAxis("bottom"))
        _(self._canvas.getAxis("left"))

    def _setup_context_menu(self) -> None:
        with the(self._canvas) as canvas:
            # customize menu
            titles_to_leave: list[str] = [
                canvas.ctrl.alphaGroup.parent().title(),
                canvas.ctrl.gridGroup.parent().title(),
            ]
            action: QAction
            for action in canvas.ctrlMenu.actions():
                if action.text() not in titles_to_leave:
                    canvas.ctrlMenu.removeAction(action)
            canvas.vb.menu = canvas.ctrlMenu
            canvas.ctrlMenu = None
            canvas.getViewBox().getMenu(canvas).addAction(self._view_all_action)
            canvas.ctrl.autoAlphaCheck.setChecked(False)
            canvas.ctrl.autoAlphaCheck.hide()
        self.figure.sceneObj.contextMenu = None

    def on_lim_changed(self, arg: tuple[pg.PlotWidget, list[list[float]]]) -> None:
        if self._ignore_scale_change.locked():
            return
        rect: list[list[float]] = arg[1]
        xlim: list[float]
        ylim: list[float]
        xlim, ylim = rect
        with self._ignore_scale_change:
            self.on_xlim_changed(xlim)
            self.on_ylim_changed(ylim)

    @abc.abstractmethod
    def on_xlim_changed(self, xlim: list[float]) -> None: ...

    @abc.abstractmethod
    def on_ylim_changed(self, ylim: list[float | np.float64]) -> None: ...

    def ensure_y_fits(self) -> None:
        if (x := self._plot_line.xData) is None or x.size < 2:
            return
        if (y := self._plot_line.yData) is None or y.size < 2:
            return
        x_axis: pg.AxisItem = self._canvas.getAxis("bottom")
        y_axis: pg.AxisItem = self._canvas.getAxis("left")
        visible_points: NDArray[np.float64] = y[
            (x >= min(x_axis.range)) & (x <= max(x_axis.range))
        ]
        if np.any(visible_points < min(y_axis.range)):
            minimum: np.float64 = np.min(visible_points)
            # noinspection PyTypeChecker
            self.set_y_range(
                minimum - 0.05 * (max(y_axis.range) - minimum), max(y_axis.range)
            )
        if np.any(visible_points > max(y_axis.range)):
            maximum: np.float64 = np.max(visible_points)
            # noinspection PyTypeChecker
            self.set_y_range(
                min(y_axis.range), maximum + 0.05 * (maximum - min(y_axis.range))
            )

    @Slot(tuple)
    def on_mouse_moved(self, event: tuple[QPointF]) -> None:  # noqa: F821
        if self._plot_line.xData is None and self._plot_line.yData is None:
            return
        pos: QPointF = event[0]
        if self.figure.sceneBoundingRect().contains(pos):
            point: QPointF = self._canvas.getViewBox().mapSceneToView(pos)
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
                    self._cursor_balloon.setHtml(
                        self._cursor_x.text() + "<br>" + self._cursor_y.text()
                    )
                    balloon_border: QRectF = self._cursor_balloon.boundingRect()
                    sx: float
                    sy: float
                    sx, sy = self._canvas.getViewBox().viewPixelSize()
                    balloon_width: float = balloon_border.width() * sx
                    balloon_height: float = balloon_border.height() * sy
                    anchor_x: float = (
                        0.0
                        if point.x() - self.figure.visibleRange().left() < balloon_width
                        else 1.0
                    )
                    anchor_y: float = (
                        0.0
                        if self.figure.visibleRange().bottom() - point.y()
                        < balloon_height
                        else 1.0
                    )
                    self._cursor_balloon.setAnchor((anchor_x, anchor_y))
                self._cursor_balloon.setVisible(
                    self.settings.show_coordinates_at_crosshair
                )
            else:
                self.hide_cursors()
        else:
            self.hide_cursors()

    @Slot()
    def on_view_all_triggered(self) -> None:
        self._canvas.getViewBox().autoRange()

    def hide_cursors(self) -> None:
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)
        self._cursor_x.setVisible(False)
        self._cursor_y.setVisible(False)
        self._cursor_balloon.setVisible(False)

    def set_x_range(
        self, lower_value: float | np.float64, upper_value: float | np.float64
    ) -> None:
        self.figure.getPlotItem().setXRange(lower_value, upper_value)

    def set_y_range(
        self, lower_value: float | np.float64, upper_value: float | np.float64
    ) -> None:
        self.figure.getPlotItem().setYRange(lower_value, upper_value)

    def setup_left_axis(self) -> None:
        a: pg.AxisItem = self._canvas.getAxis("left")
        if self._plot_data.y_data_type == PlotDataItem.GAMMA_DATA:
            a.enableAutoSIPrefix(False)
            a.setLabel(
                text=_translate("plot axes labels", "Absorption"),
                units=_translate("unit", "cm<sup>−1</sup>"),
            )
            a.scale = 1.0
            a.autoSIPrefixScale = 1.0

            self._cursor_y.suffix = _translate("unit", "cm<sup>−1</sup>")
            self._cursor_y.siPrefix = False
            self._cursor_y.setFormatStr(
                "{mantissa:.{decimals}f}×10<sup>{exp}</sup>{suffixGap}{suffix}"
            )

        elif self._plot_data.y_data_type == PlotDataItem.VOLTAGE_DATA:
            a.enableAutoSIPrefix(True)
            a.setLabel(
                text=_translate("plot axes labels", "Voltage"),
                units=_translate("unit", "V"),
            )

            self._cursor_y.suffix = _translate("unit", "V")
            self._cursor_y.siPrefix = True
            self._cursor_y.setFormatStr(
                "{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}"
            )

        else:
            raise ValueError(f"Invalid data type: {self._plot_data.y_data_type!r}")

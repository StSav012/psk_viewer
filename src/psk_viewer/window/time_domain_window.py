from collections.abc import Callable, Collection
from pathlib import Path
from threading import Lock
from typing import cast

# noinspection PyPackageRequirements
import numpy as np
import pandas as pd  # type: ignore
import pyqtgraph as pg  # type: ignore

# noinspection PyPackageRequirements
from numpy.typing import NDArray
from pyqtgraph import GraphicsScene, PlotWidget
from pyqtgraph.exporters.ImageExporter import ImageExporter
from qtpy.QtCore import (
    QCoreApplication,
    QPointF,
    QRectF,
    Qt,
    Slot,
)
from qtpy.QtGui import (
    QAction,
    QCloseEvent,
    QFont,
    QGuiApplication,
    QPen,
    QScreen,
    QShowEvent,
)
from qtpy.QtWidgets import QDockWidget, QMainWindow, QMessageBox, QWidget

from ..plot_data_item import PlotDataItem
from ..utils import DataMode, SpectrometerData, load_data, the
from ..widgets.preferences import Preferences
from .gui.time_domain_gui import TimeDomainGUI

__all__ = ["TimeDomainWindow"]

_translate = QCoreApplication.translate


class TimeDomainWindow(TimeDomainGUI):
    supported_modes: Collection[DataMode] = (DataMode.TIME_DOMAIN,)

    def __init__(
        self,
        file_path: Path | None = None,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        self._data_mode: DataMode = DataMode.unknown

        self._ghost_line: pg.PlotDataItem = self.figure.plot(np.empty(0), name="")
        self._plot_line: pg.PlotDataItem = self.figure.plot(np.empty(0), name="")
        self._ghost_data: PlotDataItem = PlotDataItem()
        self._plot_data: PlotDataItem = PlotDataItem()

        self._ignore_scale_change: Lock = Lock()

        self._mouse_moved_signal_proxy: pg.SignalProxy = pg.SignalProxy(
            cast(GraphicsScene, self.figure.scene()).sigMouseMoved,
            rateLimit=10,
            slot=self.on_mouse_moved,
        )
        self._axis_range_changed_signal_proxy: pg.SignalProxy = pg.SignalProxy(
            self.figure.sigRangeChanged, rateLimit=20, slot=self.on_lim_changed
        )

        self.setup_ui()
        self._setup_colors()

        self.load_config()

        self.setup_ui_actions()

        if file_path is not None and file_path.exists():
            loaded: bool = self.load_data(file_path)
            if loaded:
                self.set_config_value("open", "location", file_path.parent)

    def setup_ui(self) -> None:
        self.hide_cursors()

        self.set_plot_line_appearance()
        self.set_axis_line_appearance()
        self.set_crosshair_lines_appearance()

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

            from .. import windows

            windows.remove(self)

            event.accept()
        elif close_code == QMessageBox.StandardButton.Cancel:
            event.ignore()

    def showEvent(self, event: QShowEvent) -> None:

        from .. import windows

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

    def load_config(self) -> None:
        with self._loading:
            # Fallback: Center the window
            screen: QScreen = QGuiApplication.primaryScreen()
            self.move(
                round(0.5 * (screen.size().width() - self.size().width())),
                round(0.5 * (screen.size().height() - self.size().height())),
            )

            self.settings.restore(self)

            self.box_time.load_config()
            self.box_voltage.load_config()

            if (
                self.get_config_value("display", "unit", PlotDataItem.VOLTAGE_DATA, str)
                == PlotDataItem.GAMMA_DATA
            ):
                self._plot_data.y_data_type = PlotDataItem.GAMMA_DATA
            else:
                self._plot_data.y_data_type = PlotDataItem.VOLTAGE_DATA
            self.display_gamma_or_voltage()

    def setup_ui_actions(self) -> None:
        self.toolbar.open_action.triggered.connect(self.on_open_action_triggered)
        self.toolbar.clear_action.triggered.connect(self.on_clear_action_triggered)
        self.toolbar.open_ghost_action.triggered.connect(
            self.on_open_ghost_action_triggered
        )
        self.toolbar.clear_ghost_action.triggered.connect(
            self.on_clear_ghost_action_triggered
        )
        self.toolbar.save_data_action.triggered.connect(self.on_save_data_triggered)
        self.toolbar.copy_figure_action.triggered.connect(self.on_copy_figure_triggered)
        self.toolbar.save_figure_action.triggered.connect(self.on_save_figure_triggered)
        self.toolbar.toolboxes_menu.menuAction().triggered.connect(
            self.on_toolboxes_menu_triggered
        )
        self.toolbar.configure_action.triggered.connect(
            self.on_configure_action_triggered
        )

        self.box_time.setup_ui_actions()
        self.box_time.changed.connect(self.on_time_box_changed)

        self.box_voltage.setup_ui_actions()
        self.box_voltage.changed.connect(self.on_voltage_box_changed)
        self.box_voltage.dataModeChanged.connect(self.on_voltage_box_data_mode_changed)

        self._view_all_action.triggered.connect(self.on_view_all_triggered)

    def on_lim_changed(self, arg: tuple[PlotWidget, list[list[float]]]) -> None:
        if self._ignore_scale_change.locked():
            return
        rect: list[list[float]] = arg[1]
        xlim: list[float]
        ylim: list[float]
        xlim, ylim = rect
        with self._ignore_scale_change:
            self.on_xlim_changed(xlim)
            self.on_ylim_changed(ylim)

    def on_xlim_changed(self, xlim: list[float]) -> None:
        min_time, max_time = min(xlim), max(xlim)
        self.box_time.set_range(min_time, max_time)
        self.set_x_range(*self.box_time.range)

    def on_ylim_changed(self, ylim: list[float | np.float64]) -> None:
        min_voltage, max_voltage = min(ylim), max(ylim)
        self.box_voltage.set_range(min_voltage, max_voltage)
        self.set_y_range(lower_value=min_voltage, upper_value=max_voltage)

    def set_x_range(
        self, lower_value: float | np.float64, upper_value: float | np.float64
    ) -> None:
        self.figure.getPlotItem().setXRange(lower_value, upper_value)

    def set_y_range(
        self, lower_value: float | np.float64, upper_value: float | np.float64
    ) -> None:
        self.figure.getPlotItem().setYRange(lower_value, upper_value)

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
    def on_mouse_moved(self, event: tuple[QPointF]) -> None:
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

    @Slot(float, float)
    def on_time_box_changed(self, min_time: float, max_time: float) -> None:
        if self._loading.locked():
            return
        with self._loading:
            self.set_x_range(
                lower_value=min_time,
                upper_value=max_time,
            )

    @Slot(float, float)
    def on_voltage_box_changed(self, min_y: float, max_y: float) -> None:
        if self._loading.locked():
            return
        with self._loading:
            self.set_y_range(
                lower_value=min_y,
                upper_value=max_y,
            )

    @Slot()
    def on_toolboxes_menu_triggered(self) -> None:
        def dock_for_action(action: QAction) -> QDockWidget | None:
            for child in self.findChildren(QDockWidget):
                if child.toggleViewAction() == action:
                    return child
            return None

        def set_dock_by_action_visible(action: QAction, visible: bool) -> None:
            if (w := dock_for_action(action)) is not None:
                w.setVisible(visible)

        with the(self.toolbar.toolboxes_menu) as menu:
            last_state: dict[int, bool] = getattr(menu, "last_state", {})
            current_state: dict[int, bool] = {}
            for a in menu.actions():
                current_state[id(a)] = a.isChecked()
            if any(current_state.values()):
                for a in menu.actions():
                    set_dock_by_action_visible(a, False)
            else:
                if any(last_state.values()):
                    for a in menu.actions():
                        set_dock_by_action_visible(a, last_state.get(id(a), True))
                else:
                    for a in menu.actions():
                        set_dock_by_action_visible(a, True)
            menu.last_state = current_state

    @Slot()
    def on_configure_action_triggered(self) -> None:
        preferences_dialog: Preferences = Preferences(self.settings, self)
        if preferences_dialog.exec() == Preferences.DialogCode.Rejected:
            return
        self._install_translation()
        self._setup_colors()
        self.set_plot_line_appearance()
        self.set_axis_line_appearance()
        self.set_crosshair_lines_appearance()
        self.display_gamma_or_voltage()

    def hide_cursors(self) -> None:
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)
        self._cursor_x.setVisible(False)
        self._cursor_y.setVisible(False)
        self._cursor_balloon.setVisible(False)

    @Slot()
    def on_open_action_triggered(self) -> None:
        self.load_data()

    @property
    def line(self) -> PlotDataItem:
        return self._plot_line

    @property
    def label(self) -> str | None:
        return self._plot_line.name()

    def set_plot_line_appearance(self) -> None:
        self._plot_line.setPen(
            pg.mkPen(self.settings.line_color, width=0.5 * self.settings.line_thickness)
        )
        self._ghost_line.setPen(
            pg.mkPen(
                self.settings.ghost_line_color, width=0.5 * self.settings.line_thickness
            )
        )
        self._canvas.replot()

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

    def set_crosshair_lines_appearance(self) -> None:
        pen: QPen = pg.mkPen(
            self.settings.crosshair_lines_color,
            width=0.5 * self.settings.crosshair_lines_thickness,
        )
        self._crosshair_v_line.setPen(pen)
        self._crosshair_h_line.setPen(pen)
        self._canvas.replot()

    @Slot()
    def on_clear_action_triggered(self) -> None:
        close: QMessageBox = QMessageBox()
        close.setText(self.tr("Are you sure?"))
        close.setIcon(QMessageBox.Icon.Question)
        close.setWindowIcon(self.windowIcon())
        close.setWindowTitle(self.tr("Spectrometer Data Viewer"))
        close.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if close.exec() != QMessageBox.StandardButton.Yes:
            return

        self._ghost_line.clear()
        self._plot_line.clear()
        self._ghost_data.clear()
        self._plot_data.clear()
        self.toolbar.clear_action.setEnabled(False)
        self.toolbar.open_ghost_action.setEnabled(False)
        self.toolbar.clear_ghost_action.setEnabled(False)
        self.toolbar.save_data_action.setEnabled(False)
        self.toolbar.copy_figure_action.setEnabled(False)
        self.toolbar.save_figure_action.setEnabled(False)
        self._cursor_balloon.setVisible(False)
        self._crosshair_h_line.setVisible(False)
        self._crosshair_v_line.setVisible(False)
        self._cursor_x.setVisible(True)
        self._cursor_y.setVisible(True)
        self._canvas.replot()
        self.status_bar.clearMessage()
        self.setWindowTitle(self.tr("Spectrometer Data Viewer"))
        self._data_mode = DataMode.unknown

    @Slot()
    def on_open_ghost_action_triggered(self) -> None:
        self.load_ghost_data()

    @Slot()
    def on_clear_ghost_action_triggered(self) -> None:
        self.clear_ghost()

    def clear_ghost(self) -> None:
        self._ghost_line.clear()
        self._ghost_data.clear()
        self.toolbar.clear_ghost_action.setEnabled(False)
        self._canvas.replot()

    def configure_interface_after_loading_data(self, t: NDArray[np.float64]) -> None:
        self.toolbar.clear_action.setEnabled(True)

        min_time: np.float64 = cast(np.float64, t[0])
        max_time: np.float64 = cast(np.float64, t[-1])

        self.box_time.switch_range(min_time, max_time)

        self.box_voltage.can_show_gamma = self._data_mode in (
            DataMode.PSK,
            DataMode.PSK_WITH_JUMP,
            DataMode.TIME_DOMAIN,
        )
        self.toolbar.save_data_action.setEnabled(True)
        self.toolbar.copy_figure_action.setEnabled(True)
        self.toolbar.save_figure_action.setEnabled(True)

    def load_data(self, filename: Path | None = None) -> bool:
        self.clear_ghost()

        if not filename and not (
            filename := self._open_data_dialog.get_open_filename()
        ):
            return False

        data: SpectrometerData | None = load_data(self, filename)
        if data is None:
            return False
        if self._data_mode == data.mode:
            return self.set_data(data)

        if data.mode in TimeDomainWindow.supported_modes:
            # noinspection PyTypeChecker
            w = TimeDomainWindow(parent=self.parent(), flags=self.windowFlags())
            r: bool = w.set_data(data)
            if r:
                w.show()
                if self._data_mode == DataMode.unknown:
                    self.close()
            else:
                w.deleteLater()
            return r

        from . import FrequencyDomainWindow

        if data.mode in FrequencyDomainWindow.supported_modes:
            # noinspection PyTypeChecker
            w = FrequencyDomainWindow(parent=self.parent(), flags=self.windowFlags())
            r: bool = w.set_data(data)
            if r:
                w.load_catalog()
                w.show()
                if self._data_mode == DataMode.unknown:
                    self.close()
            else:
                w.deleteLater()
            return r

        return False

    def set_data(self, data: SpectrometerData | None) -> bool:
        if data is None:
            return False

        filename: Path
        v: NDArray[np.float64]
        f: NDArray[np.float64]
        g: NDArray[np.float64]
        t: NDArray[np.float64]
        data_mode: DataMode
        filename, f, g, v, t, data_mode = data

        if data_mode not in TimeDomainWindow.supported_modes:
            return False

        if not (t.size and v.size):
            return False

        self.settings.display_processing = data_mode in (
            DataMode.PSK,
            DataMode.PSK_WITH_JUMP,
        )
        self._data_mode = data_mode

        self._plot_data.set_data(
            frequency_data=f, gamma_data=g, voltage_data=v, time_data=t
        )
        self.configure_interface_after_loading_data(t)

        self._plot_data.x_data_type = PlotDataItem.TIME_DATA
        self._ghost_data.x_data_type = PlotDataItem.TIME_DATA

        self._plot_line.setData(
            name=str(filename.parent / filename.stem),
        )

        self.display_gamma_or_voltage()

        self.set_x_range(*self.box_time.range)
        self.set_y_range(*self.box_voltage.range)

        self.setWindowTitle(self.tr("%s — Spectrometer Data Viewer") % filename)

        self.toolbar.open_ghost_action.setEnabled(True)

        return True

    def load_ghost_data(self, filename: Path | None = None) -> bool:
        if not filename and not (
            filename := self._open_data_dialog.get_open_filename()
        ):
            return False

        data: SpectrometerData | None = load_data(self, filename)
        if data is None:
            return False

        v: NDArray[np.float64]
        f: NDArray[np.float64]
        g: NDArray[np.float64]
        t: NDArray[np.float64]
        data_mode: DataMode
        filename, f, g, v, t, data_mode = data

        if data_mode not in TimeDomainWindow.supported_modes:
            return False

        if data_mode != self._data_mode:
            return False

        if not (t.size and v.size):
            return False

        self._ghost_data.set_data(
            frequency_data=f, gamma_data=g, voltage_data=v, time_data=t
        )
        self._ghost_line.setData(
            name=str(filename.parent / filename.stem),
        )

        self.toolbar.clear_ghost_action.setEnabled(True)

        self.display_gamma_or_voltage()

        return True

    @Slot(str)
    def on_voltage_box_data_mode_changed(self, mode: str) -> None:
        self._plot_data.y_data_type = mode
        self._ghost_data.y_data_type = mode
        self.display_gamma_or_voltage()

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

    def display_gamma_or_voltage(self) -> None:
        self._plot_data.jump = np.nan
        self._ghost_data.jump = np.nan

        if self._plot_data:  # something is loaded
            self._plot_line.setData(self._plot_data.x_data, self._plot_data.y_data)

            y_data: NDArray[np.float64] = self._plot_data.y_data
            min_y: np.float64 = np.min(y_data)
            max_y: np.float64 = np.max(y_data)
            with self._loading:
                self.box_voltage.switch_range(min_y, max_y)
            self.on_ylim_changed([min_y, max_y])

        if self._ghost_data:  # something is loaded
            self._ghost_line.setData(self._ghost_data.x_data, self._ghost_data.y_data)

        self.setup_left_axis()
        self.hide_cursors()

    @Slot()
    def on_save_data_triggered(self) -> None:
        if self._plot_line.yData is None:
            return

        def save_csv(fn: Path) -> None:
            data: NDArray[np.float64]
            sep: str = self.settings.csv_separator
            if self.box_voltage.show_gamma:
                data = np.column_stack((x, y))
                # noinspection PyTypeChecker
                np.savetxt(
                    fn,
                    data,
                    delimiter=sep,
                    header=(
                        sep.join(
                            (
                                _translate("plot axes labels", "Time"),
                                _translate("plot axes labels", "Absorption"),
                            )
                        )
                        + "\n"
                        + sep.join(
                            (
                                _translate("unit", "s"),
                                _translate("unit", "cm⁻¹"),
                            )
                        )
                    ),
                    fmt=("%.8e", "%.6e"),
                    encoding="utf-8",
                )
            else:
                data = np.column_stack((x, y * 1e3))
                # noinspection PyTypeChecker
                np.savetxt(
                    fn,
                    data,
                    delimiter=sep,
                    header=(
                        sep.join(
                            (
                                _translate("plot axes labels", "Time"),
                                _translate("plot axes labels", "Voltage"),
                            )
                        )
                        + "\n"
                        + sep.join(
                            (
                                _translate("unit", "s"),
                                _translate("unit", "mV"),
                            )
                        )
                    ),
                    fmt=("%.8e", "%.6f"),
                    encoding="utf-8",
                )

        def save_rtf(fn: Path) -> None:
            from ..utils import html_to_rtf, tag

            table: list[list[str]] = []
            if self.box_voltage.show_gamma:
                table.append(
                    [
                        _translate("plot axes labels", "Time (s)"),
                        _translate("plot axes labels", "Absorption (cm⁻¹)"),
                    ]
                )
                for _x, _y in zip(x, y, strict=True):
                    table.append([f"{_x:.8e}", f"{_y:.6e}"])
            else:
                table.append(
                    [
                        _translate("plot axes labels", "Time (s)"),
                        _translate("plot axes labels", "Voltage (mV)"),
                    ]
                )
                for _x, _y in zip(x, y * 1e3, strict=True):
                    table.append([f"{_x:.8e}", f"{_y:.6f}"])
            with open(fn, "w", encoding="utf-8") as f_out:
                f_out.write(
                    html_to_rtf(
                        tag(
                            "html",
                            tag(
                                "table",
                                "".join(
                                    tag(
                                        "tr",
                                        "".join(tag("td", cell) for cell in row),
                                    )
                                    for row in table
                                ),
                            ),
                        )
                    )
                )

        def save_xlsx(fn: Path) -> None:
            data: NDArray[np.float64]
            with pd.ExcelWriter(fn) as writer:
                df: pd.DataFrame
                if self.box_voltage.show_gamma:
                    data = np.column_stack((x, y))
                    df = pd.DataFrame(data)
                    df.to_excel(
                        writer,
                        index=False,
                        header=[
                            _translate("plot axes labels", "Time (s)"),
                            _translate("plot axes labels", "Absorption (cm⁻¹)"),
                        ],
                        sheet_name=self._plot_line.name()
                        or _translate("workbook", "Sheet1"),
                    )
                else:
                    data = np.column_stack((x, y * 1e3))
                    df = pd.DataFrame(data)
                    df.to_excel(
                        writer,
                        index=False,
                        header=[
                            _translate("plot axes labels", "Time (s)"),
                            _translate("plot axes labels", "Voltage (mV)"),
                        ],
                        sheet_name=self._plot_line.name()
                        or _translate("workbook", "Sheet1"),
                    )

        supported_formats_callbacks: dict[str, Callable[[Path], None]] = {
            ".csv": save_csv,
            ".rtf": save_rtf,
            ".xlsx": save_xlsx,
        }

        if not (filename := self._save_table_dialog.get_save_filename()):
            return
        x: NDArray[np.float64] = self._plot_line.xData
        y: NDArray[np.float64] = self._plot_line.yData
        max_mark: float
        min_mark: float
        min_mark, max_mark = self._canvas.axes["bottom"]["item"].range
        good: NDArray[np.bool_] = (min_mark <= x) & (x <= max_mark)
        x = x[good]
        y = y[good]
        del good

        filename_ext: str = filename.suffix.casefold()
        if filename_ext in supported_formats_callbacks:
            with self.show_loading():
                supported_formats_callbacks[filename_ext](filename)

    @Slot()
    def on_copy_figure_triggered(self) -> None:
        exporter: ImageExporter = ImageExporter(self._canvas)
        self.hide_cursors()
        exporter.export(copy=True)

    @Slot()
    def on_save_figure_triggered(self) -> None:
        exporter: ImageExporter = ImageExporter(self._canvas)
        if not (filename := self._save_image_dialog.get_save_filename()):
            return
        self.hide_cursors()
        exporter.export(str(filename))

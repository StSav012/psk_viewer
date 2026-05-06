from collections.abc import Callable

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QKeySequence, QPalette
from qtpy.QtWidgets import QAction, QApplication, QToolBar, QWidget

from .utils import load_icon, mix_colors

__all__ = ["TimeDomainToolbar", "FrequencyDomainToolbar"]


class ToolBar(QToolBar):
    def _add_action(
        self,
        icon_name: str,
        title: str,
        shortcut: QKeySequence.StandardKey | str | None = None,
        tooltip: str = "",
        enabled: bool = True,
        checkable: bool = False,
        role: QAction.MenuRole | None = None,
        receiver: Callable[[], None] | None = None,
    ) -> QAction:
        a: QAction
        if receiver is None:
            a = self.addAction(load_icon(self, icon_name), title)
        else:
            a = self.addAction(load_icon(self, icon_name), title, receiver)
        if shortcut is not None:
            a.setShortcut(shortcut)
        if tooltip:
            a.setToolTip(tooltip)
        if not a.shortcut().isEmpty() and a.toolTip():
            tooltip_text_color: QColor = self.palette().color(
                QPalette.ColorRole.ToolTipText
            )
            tooltip_base_color: QColor = self.palette().color(
                QPalette.ColorRole.ToolTipBase
            )
            shortcut_color: QColor = mix_colors(tooltip_text_color, tooltip_base_color)
            a.setToolTip(
                f'<p style="white-space:pre">{a.toolTip()}&nbsp;&nbsp;'
                f'<code style="color:{shortcut_color.name()};font-size:small">'
                f"{a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)}</code></p>"
            )
        a.setEnabled(enabled)
        a.setCheckable(checkable)
        if role is not None:
            a.setMenuRole(role)

        return a


class TimeDomainToolbar(ToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Time-Domain Toolbar", parent)
        self.setObjectName("TimeDomainToolbar")

        self.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)

        self.open_action: QAction = self._add_action(
            "open",
            self.tr("Open"),
            shortcut=QKeySequence.StandardKey.Open,
            tooltip=self.tr("Load spectrometer data"),
        )
        self.clear_action: QAction = self._add_action(
            "delete",
            self.tr("Clear"),
            shortcut=QKeySequence.StandardKey.Close,
            tooltip=self.tr("Clear lines"),
            enabled=False,
        )
        self.addSeparator()
        self.open_ghost_action: QAction = self._add_action(
            "openGhost",
            self.tr("Open Ghost"),
            tooltip=self.tr("Load spectrometer data as a background curve"),
            enabled=False,
        )
        self.clear_ghost_action: QAction = self._add_action(
            "deleteGhost",
            self.tr("Clear Ghost"),
            tooltip=self.tr("Clear the background curve"),
            enabled=False,
        )
        self.addSeparator()
        self.save_data_action: QAction = self._add_action(
            "saveTable",
            self.tr("Save Data"),
            tooltip=self.tr("Export the visible data"),
            enabled=False,
        )
        self.copy_figure_action: QAction = self._add_action(
            "copyImage",
            self.tr("Copy Figure"),
            tooltip=self.tr("Copy the plot as an image"),
            enabled=False,
        )
        self.save_figure_action: QAction = self._add_action(
            "saveImage",
            self.tr("Save Figure"),
            tooltip=self.tr("Save the plot as an image"),
            enabled=False,
        )
        self.addSeparator()
        self.configure_action: QAction = self._add_action(
            "configure",
            self.tr("Configure"),
            shortcut=QKeySequence.StandardKey.Preferences,
            tooltip=self.tr("Edit parameters"),
        )
        self.addSeparator()
        self._add_action(
            "qt_logo",
            self.tr("About Qt"),
            receiver=QApplication.aboutQt,
            role=QAction.MenuRole.AboutQtRole,
        )


class FrequencyDomainToolbar(ToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Frequency-Domain Toolbar", parent)
        self.setObjectName("FrequencyDomainToolbar")

        self.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)

        self.open_action: QAction = self._add_action(
            "open",
            self.tr("Open"),
            shortcut=QKeySequence.StandardKey.Open,
            tooltip=self.tr("Load spectrometer data"),
        )
        self.clear_action: QAction = self._add_action(
            "delete",
            self.tr("Clear"),
            shortcut=QKeySequence.StandardKey.Close,
            tooltip=self.tr("Clear lines and markers"),
            enabled=False,
        )
        self.addSeparator()
        self.open_ghost_action: QAction = self._add_action(
            "openGhost",
            self.tr("Open Ghost"),
            tooltip=self.tr("Load spectrometer data as a background curve"),
            enabled=False,
        )
        self.clear_ghost_action: QAction = self._add_action(
            "deleteGhost",
            self.tr("Clear Ghost"),
            tooltip=self.tr("Clear the background curve"),
            enabled=False,
        )
        self.addSeparator()
        self.differentiate_action: QAction = self._add_action(
            "secondDerivative",
            self.tr("Calculate second derivative"),
            shortcut="Ctrl+/",
            tooltip=self.tr("Calculate finite-step second derivative"),
            checkable=True,
            enabled=False,
        )
        self.addSeparator()
        self.save_data_action: QAction = self._add_action(
            "saveTable",
            self.tr("Save Data"),
            tooltip=self.tr("Export the visible data"),
            enabled=False,
        )
        self.copy_figure_action: QAction = self._add_action(
            "copyImage",
            self.tr("Copy Figure"),
            tooltip=self.tr("Copy the plot as an image"),
            enabled=False,
        )
        self.save_figure_action: QAction = self._add_action(
            "saveImage",
            self.tr("Save Figure"),
            tooltip=self.tr("Save the plot as an image"),
            enabled=False,
        )
        self.addSeparator()
        self.trace_action: QAction = self._add_action(
            "selectObject",
            self.tr("Mark"),
            shortcut="Ctrl+*",
            tooltip=self.tr("Mark data points (hold Shift to delete)"),
            checkable=True,
            enabled=False,
        )
        self.load_trace_action: QAction = self._add_action(
            "openSelected",
            self.tr("Load Marks"),
            shortcut="Ctrl+Shift+O",
            tooltip=self.tr("Load marked points values from a file"),
            enabled=False,
        )
        self.copy_trace_action: QAction = self._add_action(
            "copySelected",
            self.tr("Copy Marked"),
            shortcut="Ctrl+Shift+C",
            tooltip=self.tr("Copy marked points values into clipboard"),
            enabled=False,
        )
        self.save_trace_action: QAction = self._add_action(
            "saveSelected",
            self.tr("Save Marked"),
            shortcut="Ctrl+Shift+S",
            tooltip=self.tr("Save marked points values"),
            enabled=False,
        )
        self.clear_trace_action: QAction = self._add_action(
            "clearSelected",
            self.tr("Clear Marked"),
            shortcut="Ctrl+Shift+W",
            tooltip=self.tr("Clear marked points"),
            enabled=False,
        )
        self.addSeparator()
        self.configure_action: QAction = self._add_action(
            "configure",
            self.tr("Configure"),
            shortcut=QKeySequence.StandardKey.Preferences,
            tooltip=self.tr("Edit parameters"),
        )
        self.addSeparator()
        self._add_action(
            "qt_logo",
            self.tr("About Qt"),
            receiver=QApplication.aboutQt,
            role=QAction.MenuRole.AboutQtRole,
        )

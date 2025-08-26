from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QKeySequence, QPalette
from qtpy.QtWidgets import QAction, QApplication, QToolBar, QWidget

from .utils import load_icon, mix_colors

__all__ = ["NavigationToolbar"]


class NavigationToolbar(QToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Navigation Toolbar", parent)
        self.setObjectName("NavigationToolbar")

        self.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)

        self.open_action: QAction = self.addAction(
            load_icon(self, "open"), self.tr("Open"), QKeySequence.StandardKey.Open
        )
        self.open_action.setToolTip(self.tr("Load spectrometer data"))
        self.clear_action: QAction = self.addAction(
            load_icon(self, "delete"), self.tr("Clear"), QKeySequence.StandardKey.Close
        )
        self.clear_action.setToolTip(self.tr("Clear lines and markers"))
        self.addSeparator()
        self.open_ghost_action: QAction = self.addAction(
            load_icon(self, "openGhost"),
            self.tr("Open Ghost"),
        )
        self.open_ghost_action.setToolTip(
            self.tr("Load spectrometer data as a background curve")
        )
        self.clear_ghost_action: QAction = self.addAction(
            load_icon(self, "deleteGhost"),
            self.tr("Clear Ghost"),
        )
        self.clear_ghost_action.setToolTip(self.tr("Clear the background curve"))
        self.addSeparator()
        self.differentiate_action: QAction = self.addAction(
            load_icon(self, "secondDerivative"),
            self.tr("Calculate second derivative"),
            "Ctrl+/",
        )
        self.differentiate_action.setToolTip(
            self.tr("Calculate finite-step second derivative")
        )
        self.addSeparator()
        self.save_data_action: QAction = self.addAction(
            load_icon(self, "saveTable"),
            self.tr("Save Data"),
        )
        self.save_data_action.setToolTip(self.tr("Export the visible data"))
        self.copy_figure_action: QAction = self.addAction(
            load_icon(self, "copyImage"),
            self.tr("Copy Figure"),
        )
        self.copy_figure_action.setToolTip(self.tr("Copy the plot as an image"))
        self.save_figure_action: QAction = self.addAction(
            load_icon(self, "saveImage"),
            self.tr("Save Figure"),
        )
        self.save_figure_action.setToolTip(self.tr("Save the plot as an image"))
        self.addSeparator()
        self.trace_action: QAction = self.addAction(
            load_icon(self, "selectObject"), self.tr("Mark"), "Ctrl+*"
        )
        self.trace_action.setToolTip(self.tr("Mark data points (hold Shift to delete)"))
        self.load_trace_action: QAction = self.addAction(
            load_icon(self, "openSelected"), self.tr("Load Marks"), "Ctrl+Shift+O"
        )
        self.load_trace_action.setToolTip(
            self.tr("Load marked points values from a file")
        )
        self.copy_trace_action: QAction = self.addAction(
            load_icon(self, "copySelected"), self.tr("Copy Marked"), "Ctrl+Shift+C"
        )
        self.copy_trace_action.setToolTip(
            self.tr("Copy marked points values into clipboard")
        )
        self.save_trace_action: QAction = self.addAction(
            load_icon(self, "saveSelected"), self.tr("Save Marked"), "Ctrl+Shift+S"
        )
        self.save_trace_action.setToolTip(self.tr("Save marked points values"))
        self.clear_trace_action: QAction = self.addAction(
            load_icon(self, "clearSelected"), self.tr("Clear Marked"), "Ctrl+Shift+W"
        )
        self.clear_trace_action.setToolTip(self.tr("Clear marked points"))
        self.addSeparator()
        self.configure_action: QAction = self.addAction(
            load_icon(self, "configure"),
            self.tr("Configure"),
            QKeySequence.StandardKey.Preferences,
        )
        self.configure_action.setToolTip(self.tr("Edit parameters"))
        self.addSeparator()
        about_qt_action: QAction = self.addAction(
            load_icon(self, "qt_logo"), self.tr("About Qt"), QApplication.aboutQt
        )
        about_qt_action.setMenuRole(QAction.MenuRole.AboutQtRole)

        self._add_shortcuts_to_tooltips()

        self.clear_action.setEnabled(False)
        self.open_ghost_action.setEnabled(False)
        self.clear_ghost_action.setEnabled(False)
        self.differentiate_action.setEnabled(False)
        self.save_data_action.setEnabled(False)
        self.copy_figure_action.setEnabled(False)
        self.save_figure_action.setEnabled(False)
        self.trace_action.setEnabled(False)
        self.load_trace_action.setEnabled(False)
        self.copy_trace_action.setEnabled(False)
        self.save_trace_action.setEnabled(False)
        self.clear_trace_action.setEnabled(False)

        self.differentiate_action.setCheckable(True)
        self.trace_action.setCheckable(True)

    def _add_shortcuts_to_tooltips(self) -> None:
        tooltip_text_color: QColor = self.palette().color(
            QPalette.ColorRole.ToolTipText
        )
        tooltip_base_color: QColor = self.palette().color(
            QPalette.ColorRole.ToolTipBase
        )
        shortcut_color: QColor = mix_colors(tooltip_text_color, tooltip_base_color)
        a: QAction
        for a in self.actions():
            if not a.shortcut().isEmpty() and a.toolTip():
                a.setToolTip(
                    f'<p style="white-space:pre">{a.toolTip()}&nbsp;&nbsp;'
                    f'<code style="color:{shortcut_color.name()};font-size:small">'
                    f"{a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)}</code></p>"
                )

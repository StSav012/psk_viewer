from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtWidgets import QWidget

from ...utils import the
from ...widgets.toolbar import TimeDomainToolbar
from . import GUI
from .time_box import TimeBox
from .voltage_box import VoltageBox

__all__ = ["TimeDomainGUI"]

_translate = QCoreApplication.translate


class TimeDomainGUI(GUI):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        self.box_time: TimeBox = TimeBox(self.settings, self)
        self.box_voltage: VoltageBox = VoltageBox(self.settings, self)

        self.toolbar: TimeDomainToolbar = TimeDomainToolbar(self)

        self._setup_appearance()

    def _setup_appearance(self) -> None:
        super()._setup_appearance()

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.box_time.setup_appearance()
        self.box_voltage.setup_appearance()

        self.toolbar.toolboxes_menu.addAction(self.box_time.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_time)

        self.toolbar.toolboxes_menu.addAction(self.box_voltage.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_voltage)

        self.figure.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._install_translation()

        self.adjustSize()

    def _setup_translation(self) -> None:
        super()._setup_translation()

        self.box_time.setup_translation()
        self.box_voltage.setup_translation()

        with (
            the(_translate("unit", "s")) as unit_x,
            the(_translate("unit", "V")) as unit_y,
        ):
            self._cursor_x.suffix = unit_x
            self._cursor_y.suffix = unit_y

            self.figure.setLabel(
                "bottom",
                text=_translate("plot axes labels", "Time"),
                units=unit_x,
            )
            self.figure.setLabel(
                "left",
                text=_translate("plot axes labels", "Voltage"),
                units=unit_y,
            )

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

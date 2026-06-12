from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtWidgets import QWidget

from ...utils import the
from ...widgets.toolbar import FrequencyDomainToolbar
from . import GUI
from .find_lines_box import FindLinesBox
from .found_lines_box import FoundLinesBox
from .frequency_box import FrequencyBox
from .voltage_box import VoltageBox

__all__ = ["FrequencyDomainGUI"]

_translate = QCoreApplication.translate


class FrequencyDomainGUI(GUI):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        self.box_frequency: FrequencyBox = FrequencyBox(self.settings, self)
        self.box_voltage: VoltageBox = VoltageBox(self.settings, self)
        self.box_find_lines: FindLinesBox = FindLinesBox(self.settings, self)
        self.box_found_lines: FoundLinesBox = FoundLinesBox(self.settings, self)

        self.toolbar: FrequencyDomainToolbar = FrequencyDomainToolbar(self)

        self._setup_appearance()

    def _setup_appearance(self) -> None:
        super()._setup_appearance()

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.box_frequency.setup_appearance()
        self.box_voltage.setup_appearance()
        self.box_find_lines.setup_appearance()
        self.box_found_lines.setup_appearance()

        self.toolbar.toolboxes_menu.addAction(self.box_frequency.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_frequency)

        self.toolbar.toolboxes_menu.addAction(self.box_voltage.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_voltage)

        self.toolbar.toolboxes_menu.addAction(self.box_find_lines.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.box_find_lines)

        self.toolbar.toolboxes_menu.addAction(self.box_found_lines.toggleViewAction())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.box_found_lines)

        self.figure.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._install_translation()

        self.adjustSize()

    def _setup_translation(self) -> None:
        super()._setup_translation()

        self.box_frequency.setup_translation()
        self.box_voltage.setup_translation()
        self.box_find_lines.setup_translation()
        self.box_found_lines.setup_translation()

        with (
            the(_translate("unit", "Hz")) as unit_x,
            the(_translate("unit", "V")) as unit_y,
        ):
            self._cursor_x.suffix = unit_x
            self._cursor_y.suffix = unit_y

            self.figure.setLabel(
                "bottom",
                text=_translate("plot axes labels", "Frequency"),
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

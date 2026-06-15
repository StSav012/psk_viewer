from typing import cast

# noinspection PyPackageRequirements
import numpy as np
import pyqtgraph as pg  # type: ignore
from qtpy.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QItemSelectionModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
    Slot,
)
from qtpy.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...settings import Settings
from ...utils import HeaderWithUnit, the
from ...widgets.found_lines_model import FoundLinesModel
from ...widgets.table_view import TableView

__all__ = ["FoundLinesBox"]

_translate = QCoreApplication.translate


class FoundLinesBox(QDockWidget):
    show_frequency_requested: Signal = Signal(float, name="show_frequency_requested")

    def __init__(
        self,
        settings: Settings,
        parent: QWidget | None = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)
        self.setObjectName("box_found_lines")

        self.settings: Settings = settings

        self.group_found_lines: QWidget = QWidget(self)
        self.v_layout_found_lines: QVBoxLayout = QVBoxLayout(self.group_found_lines)
        self.form_layout_found_lines: QFormLayout = QFormLayout()
        self.spin_df: pg.SpinBox = pg.SpinBox(self.group_found_lines)
        self.table: TableView = TableView(settings, self.group_found_lines)
        self.model: FoundLinesModel = FoundLinesModel(self)

    def setup_appearance(self) -> None:
        self.setWidget(self.group_found_lines)

        self.form_layout_found_lines.addRow(
            self.tr("Frequency uncertainty:"), self.spin_df
        )

        with the(self.v_layout_found_lines) as layout:
            layout.addWidget(self.table, 1)
            layout.addLayout(self.form_layout_found_lines)

        self.model.set_format(
            [
                FoundLinesModel.Format(3, 1e-6),
                FoundLinesModel.Format(4, 1e3),
                FoundLinesModel.Format(
                    precision=4,
                    scale=np.nan,
                    fancy=self.settings.fancy_table_numbers,
                    log10=self.settings.log10_gamma,
                ),
            ]
        )

        sortable_model: QSortFilterProxyModel = QSortFilterProxyModel(
            self.model.parent()
        )
        sortable_model.setSourceModel(self.model)
        self.table.setModel(sortable_model)

        self.spin_df.setOpts(
            siPrefix=True,
            decimals=1,
            dec=True,
            compactHeight=False,
            format="{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}",
            scaleAtZero=1e6,
        )
        self.spin_df.setMinimum(0.01e6)
        self.spin_df.setMaximum(10.0e6)

        self.model.fancy_table_numbers = self.settings.fancy_table_numbers
        self.model.log10_gamma = self.settings.log10_gamma

        self.adjustSize()

    def setup_translation(self) -> None:
        self.setWindowTitle(self.tr("Found Lines"))

        with the(self.form_layout_found_lines.labelForField) as labelForField:
            cast(QLabel, labelForField(self.spin_df)).setText(
                self.tr("Frequency uncertainty:")
            )

        with the(_translate("unit", "Hz")) as unit_x:
            self.spin_df.setSuffix(unit_x)

        self.model.header = [
            HeaderWithUnit(
                name=_translate("plot axes labels", "Frequency"),
                unit=_translate("unit", "MHz"),
            ),
            HeaderWithUnit(
                name=_translate("plot axes labels", "Voltage"),
                unit=_translate("unit", "mV"),
            ),
            HeaderWithUnit(
                name=_translate("plot axes labels", "Absorption"),
                unit=(
                    _translate("unit", "cm⁻¹")
                    if not self.model.log10_gamma
                    else _translate("unit", "log₁₀(cm⁻¹)")
                ),
            ),
            self.tr("Substance"),
        ]

    def setup_ui_actions(self) -> None:
        self.table.doubleClicked.connect(self.on_table_cell_double_clicked)
        self.spin_df.valueChanged.connect(self.on_spin_df_changed)

    def load_config(self) -> None:
        with self.settings.section("catalog"):
            self.spin_df.setValue(self.settings.value("df", 0.6e6, float))

    def select(self, rows: list[int]) -> None:
        self.table.clearSelection()
        sm: QItemSelectionModel = self.table.selectionModel()
        model: QAbstractItemModel = self.table.model()
        row: int
        for row in rows:
            index: QModelIndex = (
                model.mapFromSource(model.sourceModel().index(row, 0))
                if isinstance(model, QSortFilterProxyModel)
                else model.index(row, 0)
            )
            sm.select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            self.table.scrollTo(index)

    @Slot(float)
    def on_spin_df_changed(self, df: float) -> None:
        self.model.df = df
        with self.settings.section("catalog"):
            self.settings.setValue("df", df)

    @Slot(QModelIndex)
    def on_table_cell_double_clicked(self, index: QModelIndex) -> None:
        self.show_frequency_requested.emit(self.model.item(index.row(), 0))

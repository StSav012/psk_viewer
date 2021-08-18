# -*- coding: utf-8 -*-

from typing import Iterable, Optional, Union

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPalette
from PySide6.QtWidgets import QToolBar, QWidget

from utils import load_icon, mix_colors


class NavigationToolbar(QToolBar):
    def __init__(self, parent: QWidget, *,
                 parameters_title: str = 'Figure options',
                 parameters_icon: Optional[Union[QIcon, str]] = None):
        super().__init__('Navigation Toolbar', parent)
        self.setObjectName('NavigationToolbar')

        self.setAllowedAreas(Qt.AllToolBarAreas)

        self.parameters_title: str = parameters_title
        self.parameters_icon: Optional[QIcon] = (load_icon(parameters_icon) if isinstance(parameters_icon, str)
                                                 else parameters_icon)

        self.open_action: QAction = QAction(self)
        self.clear_action: QAction = QAction(self)
        self.differentiate_action: QAction = QAction(self)
        self.switch_data_action: QAction = QAction(self)
        self.save_data_action: QAction = QAction(self)
        self.copy_figure_action: QAction = QAction(self)
        self.save_figure_action: QAction = QAction(self)
        self.trace_action: QAction = QAction(self)
        self.copy_trace_action: QAction = QAction(self)
        self.save_trace_action: QAction = QAction(self)
        self.clear_trace_action: QAction = QAction(self)
        self.configure_action: QAction = QAction(self)

        # TODO: add keyboard shortcuts
        a: QAction
        i: str
        for a, i in zip([
            self.open_action,
            self.clear_action,
            self.differentiate_action,
            self.switch_data_action,
            self.save_data_action,
            self.copy_figure_action,
            self.save_figure_action,
            self.trace_action,
            self.copy_trace_action,
            self.save_trace_action,
            self.clear_trace_action,
            self.configure_action
        ], [
            'open', 'delete',
            'secondDerivative',
            '',
            'saveTable',
            'copyImage',
            'saveImage',
            'selectObject',
            'copySelected', 'saveSelected', 'clearSelected',
            'configure'
        ]):
            a.setIcon(load_icon(i.lower()))
        for a, i in zip([
            self.open_action,
            self.clear_action,
            self.differentiate_action,
            self.switch_data_action,
            self.save_data_action,
            self.copy_figure_action,
            self.save_figure_action,
            self.trace_action,
            self.copy_trace_action,
            self.save_trace_action,
            self.clear_trace_action,
            self.configure_action
        ], [
            'Ctrl+O',
            'Ctrl+W',
            'Ctrl+/',
            'Ctrl+`',
            '',
            '', '',
            'Ctrl+*',
            'Ctrl+Shift+C', 'Ctrl+Shift+S', 'Ctrl+Shift+W',
            'Ctrl+,'
        ]):
            if isinstance(i, str) and i:
                a.setShortcut(i)
            elif not isinstance(i, str) and isinstance(i, Iterable):
                a.setShortcuts(i)

        self.addAction(self.open_action)
        self.addAction(self.clear_action)
        self.addSeparator()
        self.addAction(self.differentiate_action)
        self.addAction(self.switch_data_action)
        self.addSeparator()
        self.addAction(self.save_data_action)
        self.addAction(self.copy_figure_action)
        self.addAction(self.save_figure_action)
        self.addSeparator()
        self.addAction(self.trace_action)
        self.addAction(self.copy_trace_action)
        self.addAction(self.save_trace_action)
        self.addAction(self.clear_trace_action)
        self.addSeparator()
        self.addAction(self.configure_action)

        self.clear_action.setEnabled(False)
        self.differentiate_action.setEnabled(False)
        self.switch_data_action.setEnabled(False)
        self.save_data_action.setEnabled(False)
        self.copy_figure_action.setEnabled(False)
        self.save_figure_action.setEnabled(False)
        self.trace_action.setEnabled(False)
        self.copy_trace_action.setEnabled(False)
        self.save_trace_action.setEnabled(False)
        self.clear_trace_action.setEnabled(False)

        self.switch_data_action.setCheckable(True)
        self.trace_action.setCheckable(True)

        # Aesthetic adjustments - we need to set these explicitly in PyQt5
        # otherwise the layout looks different - but we don't want to set it if
        # not using HiDPI icons otherwise they look worse than before.
        self.setIconSize(QSize(24, 24))
        self.layout().setSpacing(12)

    def add_shortcuts_to_tooltips(self) -> None:
        a: QAction
        tooltip_text_color: QColor = self.palette().color(QPalette.ToolTipText)
        tooltip_base_color: QColor = self.palette().color(QPalette.ToolTipBase)
        shortcut_color: QColor = mix_colors(tooltip_text_color, tooltip_base_color)
        for a in self.actions():
            if a.shortcut():
                a.setToolTip(f'<p style="white-space:pre">{a.toolTip()}&nbsp;&nbsp;'
                             f'<code style="color:{shortcut_color.name()};font-size:small">'
                             f'{a.shortcut().toString(QKeySequence.NativeText)}</code></p>')

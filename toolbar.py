# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QIcon, QKeySequence, QPalette
from qtpy.QtWidgets import QAction, QApplication, QToolBar, QWidget

from utils import load_icon, mix_colors

__all__ = ['NavigationToolbar']


class NavigationToolbar(QToolBar):
    def __init__(self, parent: QWidget, *,
                 parameters_title: str = 'Figure options',
                 parameters_icon: QIcon | str | None = None):
        super().__init__('Navigation Toolbar', parent)
        self.setObjectName('NavigationToolbar')

        self.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)

        self.parameters_title: str = parameters_title
        self.parameters_icon: QIcon | None = (load_icon(parameters_icon)
                                              if isinstance(parameters_icon, str)
                                              else parameters_icon)

        self.open_action: QAction = QAction(self)
        self.open_ghost_action: QAction = QAction(self)
        self.clear_ghost_action: QAction = QAction(self)
        self.clear_action: QAction = QAction(self)
        self.differentiate_action: QAction = QAction(self)
        self.save_data_action: QAction = QAction(self)
        self.copy_figure_action: QAction = QAction(self)
        self.save_figure_action: QAction = QAction(self)
        self.trace_action: QAction = QAction(self)
        self.copy_trace_action: QAction = QAction(self)
        self.save_trace_action: QAction = QAction(self)
        self.clear_trace_action: QAction = QAction(self)
        self.configure_action: QAction = QAction(self)

        a: QAction
        i: str
        for a, i in zip([
            self.open_action,
            self.clear_action,
            self.open_ghost_action,
            self.clear_ghost_action,
            self.differentiate_action,
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
            'openGhost', 'deleteGhost',
            'secondDerivative',
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
            self.open_ghost_action,
            self.clear_ghost_action,
            self.differentiate_action,
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
            '',
            '',
            'Ctrl+/',
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
        self.addAction(self.open_ghost_action)
        self.addAction(self.clear_ghost_action)
        self.addSeparator()
        self.addAction(self.differentiate_action)
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
        self.open_ghost_action.setEnabled(False)
        self.clear_ghost_action.setEnabled(False)
        self.differentiate_action.setEnabled(False)
        self.save_data_action.setEnabled(False)
        self.copy_figure_action.setEnabled(False)
        self.save_figure_action.setEnabled(False)
        self.trace_action.setEnabled(False)
        self.copy_trace_action.setEnabled(False)
        self.save_trace_action.setEnabled(False)
        self.clear_trace_action.setEnabled(False)

        self.differentiate_action.setCheckable(True)
        self.trace_action.setCheckable(True)

        about_qt_action: QAction = QAction(self)
        about_qt_action.setIcon(load_icon('qt_logo'))
        about_qt_action.setMenuRole(QAction.MenuRole.AboutQtRole)
        about_qt_action.setText(self.tr('About Qt'))
        about_qt_action.triggered.connect(QApplication.aboutQt)
        self.addSeparator()
        self.addAction(about_qt_action)

    def add_shortcuts_to_tooltips(self) -> None:
        tooltip_text_color: QColor = self.palette().color(QPalette.ColorRole.ToolTipText)
        tooltip_base_color: QColor = self.palette().color(QPalette.ColorRole.ToolTipBase)
        shortcut_color: QColor = mix_colors(tooltip_text_color, tooltip_base_color)
        a: QAction
        for a in self.actions():
            if not a.shortcut().isEmpty() and a.toolTip():
                a.setToolTip(f'<p style="white-space:pre">{a.toolTip()}&nbsp;&nbsp;'
                             f'<code style="color:{shortcut_color.name()};font-size:small">'
                             f'{a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)}</code></p>')

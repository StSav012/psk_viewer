# -*- coding: utf-8 -*-
from typing import Iterable, Optional, Union

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QToolBar

import figureoptions
from utils import load_icon


class NavigationToolbar(QToolBar):
    def __init__(self, parent, *,
                 parameters_title: str = 'Figure options',
                 parameters_icon: Optional[Union[QIcon, str]] = None):
        super().__init__('Navigation Toolbar', parent)
        self.setObjectName('NavigationToolbar')

        self.parameters_title: str = parameters_title
        self.parameters_icon: Optional[QIcon] = (load_icon(parameters_icon) if isinstance(parameters_icon, str)
                                                 else parameters_icon)

        self.open_action: QAction = QAction(self)
        self.clear_action: QAction = QAction(self)
        self.save_data_action: QAction = QAction(self)
        self.save_figure_action: QAction = QAction(self)
        self.trace_action: QAction = QAction(self)
        self.copy_trace_action: QAction = QAction(self)
        self.save_trace_action: QAction = QAction(self)
        self.clear_trace_action: QAction = QAction(self)
        self.configure_action: QAction = QAction(self)

        # TODO: add keyboard shortcuts
        a: QAction
        i: str
        for a, i in zip([self.open_action,
                         self.clear_action,
                         self.save_data_action,
                         self.save_figure_action,
                         self.trace_action,
                         self.copy_trace_action,
                         self.save_trace_action,
                         self.clear_trace_action,
                         self.configure_action],
                        ['open', 'delete',
                         'saveTable',
                         'saveImage',
                         'selectObject',
                         'copySelected', 'saveSelected', 'clearSelected',
                         'configure']):
            a.setIcon(load_icon(i.lower()))
        a: QAction
        i: str
        for a, i in zip([self.open_action,
                         self.clear_action,
                         self.save_data_action,
                         self.save_figure_action,
                         self.trace_action,
                         self.copy_trace_action,
                         self.save_trace_action,
                         self.clear_trace_action,
                         self.configure_action],
                        ['Ctrl+O',
                         '',
                         '',
                         '',
                         '',
                         '', '', '',
                         '']):
            if isinstance(i, str) and i:
                a.setShortcut(i)
            elif not isinstance(i, str) and isinstance(i, Iterable):
                a.setShortcuts(i)

        self.addAction(self.open_action)
        self.addAction(self.clear_action)
        self.addSeparator()
        self.addAction(self.save_data_action)
        self.addAction(self.save_figure_action)
        self.addSeparator()
        self.addAction(self.trace_action)
        self.addAction(self.copy_trace_action)
        self.addAction(self.save_trace_action)
        self.addAction(self.clear_trace_action)
        self.addSeparator()
        self.addAction(self.configure_action)

        self.clear_action.setEnabled(False)
        self.save_data_action.setEnabled(False)
        self.save_figure_action.setEnabled(False)
        self.trace_action.setEnabled(False)
        self.copy_trace_action.setEnabled(False)
        self.save_trace_action.setEnabled(False)
        self.clear_trace_action.setEnabled(False)
        self.configure_action.setEnabled(False)

        self.trace_action.setCheckable(True)

        # Aesthetic adjustments - we need to set these explicitly in PyQt5
        # otherwise the layout looks different - but we don't want to set it if
        # not using HiDPI icons otherwise they look worse than before.
        self.setIconSize(QSize(24, 24))
        self.layout().setSpacing(12)

    def load_parameters(self):
        # figureoptions.load_settings(ax, self)
        pass

    def edit_parameters(self):
        ax, = self.canvas.figure.get_axes()
        figureoptions.figure_edit(ax, self, title=self.parameters_title, icon=self.parameters_icon)

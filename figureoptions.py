# -*- coding: utf-8 -*-
# based on matplotlib.backends.qt_editor.figureoptions

# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# see the mpl licenses directory for a copy of the license


"""Module that provides a GUI-based editor for matplotlib's figure options."""

import os.path

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QIcon


def get_icon(name):
    basedir = 'img'
    return QIcon(os.path.join(basedir, name))


def figure_edit(axes, parent=None, *,
                title="Figure options",
                icon=None):
    """Edit matplotlib figure options"""
    sep = (None, None)  # separator

    # Save the unit data
    xconverter = axes.xaxis.converter
    yconverter = axes.yaxis.converter
    xunits = axes.xaxis.get_units()
    yunits = axes.yaxis.get_units()

    # Get / Curves
    linedict = {}
    lines_count = len(axes.get_lines())
    for index, line in enumerate(axes.get_lines()[::-1]):
        label = line.get_label()
        if label.startswith('_'):
            continue
        linedict[label] = (line, lines_count - index - 1)

    curves = []

    def prepare_data(d, init):
        """Prepare entry for FormLayout.

        `d` is a mapping of shorthands to style names (a single style may
        have multiple shorthands, in particular the shorthands `None`,
        `"None"`, `"none"` and `""` are synonyms); `init` is one shorthand
        of the initial style.

        This function returns an list suitable for initializing a
        FormLayout combobox, namely `[initial_name, (shorthand,
        style_name), (shorthand, style_name), ...]`.
        """
        if init not in d:
            d[init] = str(init)
        # Drop duplicate shorthands from dict (by overwriting them during
        # the dict comprehension).
        name2short = {name: short for short, name in d.items()}
        # Convert back to {shorthand: name}.
        short2name = {short: name for name, short in name2short.items()}
        # Find the kept shorthand for the style specified by init.
        canonical_init = name2short[d[init]]
        # Sort by representation and prepend the initial value.
        return ([canonical_init] +
                sorted(short2name.items(),
                       key=lambda short_and_name: short_and_name[1]))

    _translate = QCoreApplication.translate

    linestyles = {'-': _translate("plot line options", 'Solid'),
                  '--': _translate("plot line options", 'Dashed'),
                  '-.': _translate("plot line options", 'DashDot'),
                  ':': _translate("plot line options", 'Dotted'),
                  'None': _translate("plot line options", 'None'),
                  }

    for label, (line, index) in linedict.items():
        color = mcolors.to_hex(
            mcolors.to_rgba(line.get_color(), line.get_alpha()),
            keep_alpha=True)
        ec = mcolors.to_hex(
            mcolors.to_rgba(line.get_markeredgecolor(), line.get_alpha()),
            keep_alpha=True)
        fc = mcolors.to_hex(
            mcolors.to_rgba(line.get_markerfacecolor(), line.get_alpha()),
            keep_alpha=True)
        curvedata = [
            (None, '<b>' + _translate("plot line options", 'Line') + '</b>'),
            (_translate("plot line options", 'Line style'), prepare_data(linestyles, line.get_linestyle())),
            (_translate("plot line options", 'Width'), line.get_linewidth()),
            (_translate("plot line options", 'Color (RGBA)'), color),
            sep,
            (None, '<b>' + _translate("plot line options", 'Marker') + '</b>'),
            (_translate("plot line options", 'Style'), prepare_data(markers.MarkerStyle.markers, line.get_marker())),
            (_translate("plot line options", 'Size'), line.get_markersize()),
            (_translate("plot line options", 'Face color (RGBA)'), fc),
            (_translate("plot line options", 'Edge color (RGBA)'), ec)
        ]
        curves.append([curvedata, label, ""])
    if not curves:
        return

    def save_settings(_index, _curve):
        if parent is None or not hasattr(parent, 'parent') \
                or parent.parent is None or not hasattr(parent.parent, 'set_config_value'):
            return
        for name, value in zip(('linestyle', 'linewidth', 'color', 'marker', 'markersize',
                                'markerfacecolor', 'markeredgecolor'), _curve):
            parent.parent.set_config_value('line {}'.format(_index), name, value)

    def apply_callback(_curves):
        """This function will be called to apply changes"""
        orig_xlim = axes.get_xlim()
        orig_ylim = axes.get_ylim()

        # Restore the unit data
        axes.xaxis.converter = xconverter
        axes.yaxis.converter = yconverter
        axes.xaxis.set_units(xunits)
        axes.yaxis.set_units(yunits)
        getattr(axes.xaxis, '_update_axisinfo')()
        getattr(axes.yaxis, '_update_axisinfo')()

        # Set / Curves
        for _label, curve in zip(linedict, _curves):
            _line, _index = linedict[_label]
            (linestyle, linewidth, _color, marker, markersize,
             markerfacecolor, markeredgecolor) = curve
            save_settings(_index, curve)
            _line.set_linestyle(linestyle)
            _line.set_linewidth(linewidth)
            rgba = mcolors.to_rgba(_color)
            _line.set_alpha(None)
            _line.set_color(rgba)
            if marker != 'none':
                _line.set_marker(marker)
                _line.set_markersize(markersize)
                _line.set_markerfacecolor(markerfacecolor)
                _line.set_markeredgecolor(markeredgecolor)

        # Redraw
        figure = axes.get_figure()
        figure.canvas.draw()
        if not (axes.get_xlim() == orig_xlim and axes.get_ylim() == orig_ylim):
            figure.canvas.toolbar.push_current()

    if hasattr(qt_editor, '_formlayout'):
        formlayout = getattr(qt_editor, '_formlayout')
    elif hasattr(qt_editor, 'formlayout'):
        formlayout = getattr(qt_editor, 'formlayout')
    else:
        return
    data = formlayout.fedit(
        curves,
        title=title,
        parent=parent,
        icon=icon if icon is not None else get_icon('qt4_editor_options.svg'),
        apply=apply_callback
    )
    if data is not None:
        apply_callback(data)


def load_settings(axes, parent=None):
    if parent is None \
            or not hasattr(parent, 'canvas') or not hasattr(parent.canvas, 'parent') \
            or parent.canvas.parent is None or not hasattr(parent.canvas.parent, 'get_config_value'):
        return

    def isnumber(string):
        if string.startswith('-'):
            string = string[1:]
        parts = string.split('.', maxsplit=1)
        ok = True
        for part in parts:
            ok = ok and part.isdigit()
        return ok

    for index, line in enumerate(axes.get_lines()):
        for name in ('linestyle', 'linewidth', 'color', 'marker', 'markersize',
                     'markerfacecolor', 'markeredgecolor'):
            value = parent.parent.get_config_value('line {}'.format(index), name, '???', str)
            if value != '???':
                if isnumber(value):
                    value = float(value)
                getattr(line, 'set_' + name)(value)

    # Redraw
    figure = axes.get_figure()
    figure.canvas.draw()

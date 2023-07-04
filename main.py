#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

if sys.version_info < (3, 8):
    message = ('The Python version ' + '.'.join(map(str, sys.version_info[:3])) + ' is not supported.\n' +
               'Use Python 3.8 or newer.')
    try:
        import tkinter
    except ImportError:
        input(message)  # wait for the user to see the text
    else:
        print(message, file=sys.stderr)

        import tkinter.messagebox

        _root = tkinter.Tk()
        _root.withdraw()
        tkinter.messagebox.showerror(title='Outdated Python', message=message)
        _root.destroy()

    exit(1)

if __name__ == '__main__':

    try:
        from psk_viewer import main
    except ImportError:
        __author__ = 'StSav012'
        __original_name__ = 'psk_viewer'

        try:
            from updater import update_with_pip

            update_with_pip(__original_name__)

            from psk_viewer import main
        except ImportError:
            from updater import update_with_pip, update_from_github, update_with_git

            update_with_git() or update_from_github(__author__, __original_name__)

            from src.psk_viewer import main
    main()

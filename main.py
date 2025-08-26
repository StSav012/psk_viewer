#!/usr/bin/env python3

if __name__ == "__main__":
    try:
        from psk_viewer import main
    except ImportError:
        __author__ = "StSav012"
        __original_name__ = "psk_viewer"

        try:
            from updater import update_with_pip

            update_with_pip(__original_name__)

            from psk_viewer import main
        except ImportError:
            from updater import update_from_github, update_with_git, update_with_pip

            update_with_git() or update_from_github(__author__, __original_name__)

            from src.psk_viewer import main
    main()

To add a translation, use
   pylupdate5 -noobsolete main.py backend.py figureoptions.py -ts xy_XY.ts
   lrelease *.ts

To compile, use
    python -m compileall -b -d . main.py backend.py figureoptions.py mplcursors/__init__.py mplcursors/_mplcursors.py mplcursors/_pick_info.py
    PyInstaller -y build_folder.spec
    PyInstaller -F build_exe.spec


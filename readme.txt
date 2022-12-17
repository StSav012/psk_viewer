IPM RAS PSK and FS spectrometer files viewer

Required packages:
  • pandas,
  • pyqtgraph,
  • QtPy,
  • scipy,
  • any of PyQt6, PySide6, PyQt5, PySide2, whichever compatible with the Python and the OS.

Optional packages:
  • openpyxl.

Required Python: >= 3.8

For developers. To add a translation, use
   pyside6-lupdate -noobsolete -tr-function-alias translate="_translate" *.py -ts translations/xy.ts
   pyside6-linguist translations/*.ts
   pyside6-lrelease translations/*.ts

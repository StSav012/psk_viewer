IPM RAS PSK and FS spectrometer files viewer

Required packages:
  • pandas,
  • pyqtgraph>=0.13.3,
  • QtPy>=2.3.1,
  • scipy,
  • any of PyQt6 (<6.5.0 if pyqtgraph<0.13.3), PySide6 (<6.5.0 if pyqtgraph<0.13.3), PyQt5, PySide2,
    whichever compatible with the Python and the OS.

Optional packages:
  • numexpr: for accelerating certain numerical operations;
  • bottleneck: for accelerating certain types of nan evaluations;
  • openpyxl: for saving MS Excel files.

Required Python: >= 3.9

For developers. To add a translation, use
   pyside6-lupdate -noobsolete -tr-function-alias translate="_translate" *.py -ts translations/xy.ts
   pyside6-linguist translations/*.ts
   pyside6-lrelease translations/*.ts

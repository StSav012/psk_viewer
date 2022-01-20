IPM RAS PSK and FS spectrometer files viewer

Required packages:
  • et-xmlfile
  • numpy
  • openpyxl
  • pandas
  • pyqtgraph
  • PySide6
  • python-dateutil
  • pytz
  • scipy
  • shiboken6
  • six


Required Python: >= 3.8

For developers. To add a translation, use
   pyside6-lupdate -noobsolete -tr-function-alias translate="_translate" *.py -ts translations/xy.ts
   pyside6-linguist translations/*.ts
   pyside6-lrelease translations/*.ts

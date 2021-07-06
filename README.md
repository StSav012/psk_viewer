# IPM RAS PSK and FS spectrometer files viewer

**Required packages:**
  - `et-xmlfile`
  - `numpy`
  - `openpyxl`
  - `pandas`
  - `pyqtgraph`
  - `PySide6`
  - `python-dateutil`
  - `pytz`
  - `scipy`
  - `shiboken6`
  - `six`

They should install at the first application start automatically.

**Required Python:** >= 3.8

Note: only Python <= 3.8 is available for MS Windows 7, so, there is not much choice for those who use it.

### Getting Python
Python might already been installed on your system.
If your system supports repositories, check them first.
Otherwise, download an appropriate Python distribution (or the source code) from https://www.python.org/downloads/ and install it.

It will be convenient to add the Python directory to the `PATH` environment variable to get quick access to the binaries.

### Getting the application
The source code is available at https://github.com/StSav012/psk_viewer.

###### Use `git`
You can get the code with `git` (the preferred way): 

  - navigate to the directory you wish to store the code in,
  - issue 
    ```commandline
    git clone https://github.com/StSav012/psk_viewer.git
    ```
    in the command line,
  - find `psk_viewer` directory with the code; feel free to move or rename however you want. 

Then, do 
```commandline
git pull https://github.com/StSav012/psk_viewer.git
```
every time you wish to update the code.

###### Use the official GitHub software
This way is pretty much like the previous.

If you prefer CLI applications, issue
```commandline
gh repo clone StSav012/psk_viewer
```
in the preferred directory.

###### Get a packed archive
  - download the source code archive from https://github.com/StSav012/psk_viewer/archive/master.zip,
  - unpack its content into a directory to your taste.

The source code will get updated every time the application starts unless you manually delete `updater.py` file.

### Launching the application
File called `main.py` should be fed to Python executable.

If the file associations set so, the opening of the file should lead to executing the code. Ugly and unsafe.

If the Python directory is in `PATH` environment variable, issue something like
```commandline
python main.py
```
Otherwise, use the full path to `python` (or `python3`) executable.

Feel free to create an entry to the quick launch or to the desktop to avoid excessive typing.
The text does not cover this topic anyhow.

### Usage tips
Parts of the application interface can be moved, re-arranged, and resized.

The least evident part of the interface is the toolbar. Its buttons allow you to do the following:

  - open a data file, either from the FS or the PSK spectrometer, see the selector below the file name;
  - clear everything opened and marked;
  - replace the displayed data with their finite-step second derivative (if appropriate);
  - switch the displayed data between the detector voltage and the absorption values (if appropriate);
  - export the displayed data into a numerical table or as a picture;
  - mark interested data points, copy the values, save them, or delete them;
  - customize colors, lines thickness, and some text formatting.

Read the tooltips, they may appear useful.

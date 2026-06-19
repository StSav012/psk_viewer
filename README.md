# IPM RAS PSK and FS spectrometer files viewer

###### Required packages:

* `pandas` [![PyPI - `pandas` Version](https://img.shields.io/pypi/v/pandas)](https://pypi.org/project/pandas),
* `packaging` [![PyPI - `packaging` Version](https://img.shields.io/pypi/v/packaging)](https://pypi.org/project/packaging),
* `pyqtgraph>=0.13.3` [![PyPI - `pyqtgraph` Version](https://img.shields.io/pypi/v/pyqtgraph)](https://pypi.org/project/pyqtgraph),
* `qtpy>=2.3.1` [![PyPI - `qtpy` Version](https://img.shields.io/pypi/v/qtpy)](https://pypi.org/project/qtpy),
* any of `PyQt6` [![PyPI - `PyQt6` Version](https://img.shields.io/pypi/v/PyQt6)](https://pypi.org/project/PyQt6),
  `PySide6` [![PyPI - `PySide6` Version](https://img.shields.io/pypi/v/PySide6)](https://pypi.org/project/PySide6),
  `PyQt5` [![PyPI - `PyQt5` Version](https://img.shields.io/pypi/v/PyQt5)](https://pypi.org/project/PyQt5),
  `PySide2` [![PyPI - `PySide2` Version](https://img.shields.io/pypi/v/PySide2)](https://pypi.org/project/PySide2).

###### Optional packages:

* `pycatsearch` [![PyPI - `pycatsearch` Version](https://img.shields.io/pypi/v/pycatsearch)](https://pypi.org/project/pycatsearch): for in-place matching spectral lines;
* `numexpr` [![PyPI - `numexpr` Version](https://img.shields.io/pypi/v/numexpr)](https://pypi.org/project/numexpr): for accelerating certain numerical operations;
* `bottleneck` [![PyPI - `bottleneck` Version](https://img.shields.io/pypi/v/bottleneck)](https://pypi.org/project/bottleneck): for accelerating certain types of nan evaluations;
* `openpyxl` [![PyPI - `openpyxl` Version](https://img.shields.io/pypi/v/openpyxl)](https://pypi.org/project/openpyxl): for saving MS Excel files.

They should install at the first application start automatically.

###### Required Python: ![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fgithub.com%2FStSav012%2Fpsk_viewer%2Fraw%2Frefs%2Fheads%2Fmaster%2Fpyproject.toml)

The package is developed under the newest Python to date. Older versions of Python should be compatible as long as [
`ruff`](https://docs.astral.sh/ruff/) makes no mistakes.

In case of a difficulty in the development, the support might shrink, but not further than what
[![SPEC 0 — Minimum Supported Dependencies](https://img.shields.io/badge/SPEC-0-green?labelColor=%23004811&color=%235CA038)](https://scientific-python.org/specs/spec-0000/)
proclaims.

###### Notes:

* to run on MS Windows 7, you can install Python from [adang1345/PythonWin7](https://github.com/adang1345/PythonWin7/);
* `PySide2` requires Python < 3.11; there is [a port of `PySide2` by ![`conda-forge`: Conda Version of `PySide2`](https://img.shields.io/conda/vn/conda-forge/pyside2)
](https://anaconda.org/conda-forge/pyside2) on Python
  3.11, 3.12, and 3.13, but it's unclear whether it's stable;
* `PyQt6` and `PySide6` require pretty modern OS, e.g., 64-bit MS Windows 10 21H2 or later;
* `pyqtgraph<0.13.3` is incompatible with `Qt6>=6.5.0`;
* `PySide6==6.9.1` doesn't draw anything, it's a known bug.

### Getting Python
Python might have already been installed on your system.
If your system supports repositories, check them first.
Otherwise, download an appropriate Python distribution (or the source code) from https://www.python.org/downloads/ and install it.

It will be convenient to add the Python directory to the `PATH` environment variable to get quick access to the binaries.

### Getting the application
The source code is available at https://github.com/StSav012/psk_viewer.

###### Use `pip` or another Python package manager

[![PyPI - Version](https://img.shields.io/pypi/v/psk_viewer)](https://pypi.org/project/psk_viewer)

You can get the code with `pip` (the preferred way): 

* (optionally) create a virtual environment and activate it,
* issue
    ```commandline
    pip install psk_viewer
    ```
    in the command line.

Then, do 
```commandline
pip install -U psk_viewer
```
every time you wish to update the code.

###### Use `git`
You can get the code with `git`: 

* navigate to the directory you wish to store the code in,
* issue
    ```commandline
    git clone https://github.com/StSav012/psk_viewer.git
    ```
    in the command line,
* find `psk_viewer` directory with the code; feel free to move or rename however you want.

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

* download the source code archive from https://github.com/StSav012/psk_viewer/archive/master.zip,
* unpack its content into a directory to your taste.

The source code will get updated every time the application starts unless you manually delete `updater.py` file.

### Launching the application
After the installation via `pip` or another package manager,
an executable named `psk_viewer` should be available in the environment. That's all.

Otherwise, there's more to do.

A file called `main.py` should be fed to Python executable.

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

* open a data file, either from the FS or the PSK spectrometer, see the selector below the file name;
* clear everything opened and marked;
* replace the displayed data with their finite-step second derivative (if appropriate);
* switch the displayed data between the detector voltage and the absorption values (if appropriate);
* export the displayed data into a numerical table or as a picture;
* mark interesting data points, copy the values, save them, or remove the marks;
* customize colors, lines thickness, and some text formatting.

Read the tooltips, they may appear useful.

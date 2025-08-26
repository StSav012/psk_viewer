import sys
from collections.abc import Collection, Iterable, Iterator
from contextlib import suppress
from os import PathLike
from pathlib import Path
from typing import Any, BinaryIO, Final, NamedTuple

import numpy as np
from numpy.typing import NDArray
from qtawesome import icon
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QColor, QIcon, QPalette, QPixmap
from qtpy.QtWidgets import QInputDialog, QWidget

_translate = QCoreApplication.translate

__all__ = [
    "copy_to_clipboard",
    "load_data_csv",
    "load_data_fs",
    "load_data_scandat",
    "resource_path",
    "superscript_number",
    "superscript_tag",
    "find_qm_files",
    "load_icon",
    "mix_colors",
    "HeaderWithUnit",
]

VOLTAGE_GAIN: Final[float] = 5.0


# https://www.reddit.com/r/learnpython/comments/4kjie3/how_to_include_gui_images_with_pyinstaller/d3gjmom
def resource_path(relative_path: str | Path) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


IMAGE_EXT: str = ".svg"


def load_icon(widget: QWidget, icon_name: str) -> QIcon:
    class QTAData(NamedTuple):
        args: Iterable[str]
        options: list[dict[str, Any]] = []

    def icon_from_data(data: bytes) -> QIcon:
        palette: QPalette = widget.palette()
        pixmap: QPixmap = QPixmap()
        pixmap.loadFromData(
            data.strip()
            .replace(
                b'"background"', b'"' + palette.window().color().name().encode() + b'"'
            )
            .replace(
                b'"foreground"', b'"' + palette.text().color().name().encode() + b'"'
            )
        )
        return QIcon(pixmap)

    filename: Path = resource_path("img") / (icon_name + IMAGE_EXT)
    if not filename.exists():
        icons: dict[str, bytes | QTAData] = {
            "open": QTAData(("mdi6.folder-open",), []),
            "delete": QTAData(
                ("mdi6.delete-forever",),
                [
                    {"color": "red"},
                ],
            ),
            "openGhost": QTAData(
                ("mdi6.folder-open", "mdi6.ghost"),
                [
                    {"disabled": "mdi6.folder-open-outline"},
                    {"scale_factor": 0.4, "offset": (0.05, 0.1), "color": "gray"},
                ],
            ),
            "deleteGhost": QTAData(
                ("mdi6.delete", "mdi6.ghost"),
                [
                    {"disabled": "mdi6.delete-outline", "color": "red"},
                    {"scale_factor": 0.4, "offset": (0.0, 0.0625), "color": "gray"},
                ],
            ),
            "secondDerivative": b"""\
                <svg viewBox="0 0 32 32" width="32" height="32" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" fill="none" stroke="foreground" stroke-width="1px">
                    <g id="d">
                        <path d="m9.5 4.5v10.5"/>
                        <ellipse cx="7.25" cy="12" rx="2.25" ry="2.5"/>
                    </g>
                    <path id="2" d="m11.75 6c-0-2 3.75-1.25 0.5 2.25h1.8"/>
                    <path d="m23.5 4.5-18.75 23"/>
                    <path id="x" d="m20 22 3 5.75"/>
                    <use transform="translate(8.25 13)" xlink:href="#d"/>
                    <use transform="translate(13 13)" xlink:href="#2"/>
                    <use transform="matrix(-1 0 0 1 43 0)" xlink:href="#x"/>
                </svg>""",
            "saveTable": QTAData(
                ("mdi6.content-save", "mdi6.table"),
                [
                    {"disabled": "mdi6.content-save-outline"},
                    {"scale_factor": 0.5, "offset": (0.2, 0.2), "color": "green"},
                ],
            ),
            "copyImage": QTAData(
                ("mdi6.content-copy", "mdi6.image"),
                [{}, {"scale_factor": 0.5, "offset": (0.2, 0.2), "color": "orange"}],
            ),
            "saveImage": QTAData(
                ("mdi6.content-save", "mdi6.image"),
                [
                    {"disabled": "mdi6.content-save-outline"},
                    {"scale_factor": 0.5, "offset": (0.2, 0.2), "color": "orange"},
                ],
            ),
            "selectObject": QTAData(
                ("mdi6.marker",),
                [
                    {"color": "blue"},
                ],
            ),
            "openSelected": QTAData(
                ("mdi6.folder-open", "mdi6.marker"),
                [
                    {"disabled": "mdi6.folder-open-outline"},
                    {"scale_factor": 0.4, "offset": (0.05, 0.1), "color": "blue"},
                ],
            ),
            "copySelected": QTAData(
                ("mdi6.content-copy", "mdi6.marker"),
                [{}, {"scale_factor": 0.5, "offset": (0.2, 0.2), "color": "blue"}],
            ),
            "saveSelected": QTAData(
                ("mdi6.content-save", "mdi6.marker"),
                [
                    {"disabled": "mdi6.content-save-outline"},
                    {"scale_factor": 0.5, "offset": (0.2, 0.2), "color": "blue"},
                ],
            ),
            "clearSelected": QTAData(
                ("mdi6.delete", "mdi6.marker"),
                [
                    {"disabled": "mdi6.delete-outline", "color": "red"},
                    {"scale_factor": 0.4, "offset": (0.0, 0.0625), "color": "blue"},
                ],
            ),
            "configure": QTAData(("mdi6.cogs",)),
            "qt_logo": b"""\
                <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 158 120" fill="foreground">
                    <path d="M142.6,0h-5.5H21.9v0L0,21.9V95v6v15.2h15.2h5.5h115.2v0l21.9-21.9V21.1v-6V0H142.6z M84,100.2L73.7,105 l-8.9-14.6c-1.3,0.4-3.3,0.6-6.1,0.6c-10.4,0-17.6-2.8-21.7-8.4c-4.1-5.6-6.1-14.4-6.1-26.5c0-12.1,2.1-21.1,6.2-26.9 c4.2-5.9,11.4-8.8,21.6-8.8c10.3,0,17.4,2.9,21.6,8.7c4.1,5.8,6.2,14.8,6.2,26.9c0,8-0.8,14.5-2.5,19.4c-1.7,4.9-4.5,8.7-8.3,11.3 L84,100.2z M115.2,89.7c-5.7,0-9.5-1.3-11.6-3.9c-2.1-2.6-3.1-7.5-3.1-14.7V48h-7.6v-9.3h7.6V24.2h10.8v14.5H125V48h-13.8v22 c0,4.1,0.3,6.8,0.9,8.1c0.6,1.3,2.1,2,4.6,2l8.2-0.3l0.5,8.7C120.9,89.3,117.5,89.7,115.2,89.7z"/>
                    <path d="M58.7,30c-6.3,0-10.6,2.1-12.9,6.2C43.5,40.4,42.4,47,42.4,56c0,9.1,1.1,15.5,3.4,19.4c2.3,3.9,6.6,5.8,13,5.8 s10.7-1.9,12.9-5.7c2.2-3.8,3.3-10.3,3.3-19.4c0-9.1-1.1-15.7-3.4-19.9C69.3,32.1,65,30,58.7,30z"/>
                </svg>""",
        }
        with suppress(KeyError):
            icon_description: bytes | QTAData = icons[icon_name]
            if isinstance(icon_description, bytes):
                return icon_from_data(icon_description)
            if isinstance(icon_description, QTAData):
                if icon_description.options:
                    return icon(
                        *icon_description.args, options=icon_description.options
                    )
                return icon(*icon_description.args)
            raise TypeError("Invalid icon description")
    else:
        with open(filename, "rb") as f_in:
            return icon_from_data(f_in.read())
    return QIcon()


def mix_colors(color_1: QColor, color_2: QColor, ratio_1: float = 0.5) -> QColor:
    return QColor(
        int(round(color_2.red() * (1.0 - ratio_1) + color_1.red() * ratio_1)),
        int(round(color_2.green() * (1.0 - ratio_1) + color_1.green() * ratio_1)),
        int(round(color_2.blue() * (1.0 - ratio_1) + color_1.blue() * ratio_1)),
        int(round(color_2.alpha() * (1.0 - ratio_1) + color_1.alpha() * ratio_1)),
    )


def superscript_number(number: str) -> str:
    ss_dict = {
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
        "-": "⁻",
        "−": "⁻",
    }
    for d in ss_dict:
        number = number.replace(d, ss_dict[d])
    return number


def superscript_tag(html: str) -> str:
    """Replace numbers within <sup></sup> with their Unicode superscript analogs."""
    text: str = html
    j: int = 0
    while j >= 0:
        i: int = text.casefold().find("<sup>", j)
        if i == -1:
            return text
        j = text.casefold().find("</sup>", i)
        if j == -1:
            return text
        text = text[:i] + superscript_number(text[i + 5 : j]) + text[j + 6 :]
        j -= 5
    return text


def copy_to_clipboard(
    plain_text: str,
    rich_text: str = "",
    text_type: Qt.TextFormat | str = Qt.TextFormat.PlainText,
) -> None:
    from qtpy.QtCore import QMimeData
    from qtpy.QtGui import QClipboard
    from qtpy.QtWidgets import QApplication

    clipboard: QClipboard = QApplication.clipboard()
    mime_data: QMimeData = QMimeData()
    if isinstance(text_type, str):
        mime_data.setData(text_type, plain_text.encode())
    elif text_type == Qt.TextFormat.RichText:
        mime_data.setHtml(rich_text)
        mime_data.setText(plain_text)
    else:
        mime_data.setText(plain_text)
    clipboard.setMimeData(mime_data, QClipboard.Mode.Clipboard)


def load_data_fs(filename: Path) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    min_frequency: float = np.nan
    max_frequency: float = np.nan
    if (filename_fmd := filename.with_suffix(".fmd")).exists():
        with open(filename_fmd) as f_in:
            line: str
            for line in f_in:
                if line and not line.startswith("*"):
                    t = list(map(lambda w: w.strip(), line.split(":", maxsplit=1)))
                    if len(t) > 1:
                        if t[0].lower() == "FStart [GHz]".lower():
                            min_frequency = float(t[1]) * 1e6
                        elif t[0].lower() == "FStop [GHz]".lower():
                            max_frequency = float(t[1]) * 1e6
    else:
        return np.empty(0), np.empty(0)
    if (
        not np.isnan(min_frequency)
        and not np.isnan(max_frequency)
        and (filename_frd := filename.with_suffix(".frd")).exists()
    ):
        y: NDArray[np.float64] = np.loadtxt(filename_frd, usecols=(0,))
        x: NDArray[np.float64] = np.linspace(
            min_frequency, max_frequency, num=y.size, endpoint=False
        )
        return x, y
    return np.empty(0), np.empty(0)


def load_data_scandat(
    filename: Path, parent: QWidget
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], float]:
    with open(filename) as f_in:
        lines: list[str] = f_in.readlines()

    min_frequency: float
    frequency_step: float
    frequency_jump: float
    x: NDArray[np.float64]
    y: NDArray[np.float64]
    bias_offset: float
    bias: NDArray[np.float64]
    cell_length: float

    if lines[0].startswith("*****"):
        min_frequency = (
            float(
                lines[
                    lines.index(
                        next(
                            filter(
                                lambda line: line.startswith("F(start) [MHz]:"), lines
                            )
                        )
                    )
                    + 1
                ]
            )
            * 1e3
        )
        frequency_step = (
            float(
                lines[
                    lines.index(
                        next(
                            filter(
                                lambda line: line.startswith("F(stept) [MHz]:"), lines
                            )
                        )
                    )
                    + 1
                ]
            )
            * 1e3
        )
        frequency_jump = (
            float(
                lines[
                    lines.index(
                        next(
                            filter(
                                lambda line: line.startswith("F(jump) [MHz]:"), lines
                            )
                        )
                    )
                    + 1
                ]
            )
            * 1e3
        )
        bias_offset = float(
            lines[
                lines.index(
                    next(filter(lambda line: line.startswith("U - shift:"), lines))
                )
                + 1
            ]
        )
        cell_length = float(
            lines[
                lines.index(
                    next(filter(lambda line: line.startswith("Length of Cell:"), lines))
                )
                + 1
            ]
        )
        lines = lines[
            lines.index(next(filter(lambda line: line.startswith("Finish"), lines)))
            + 1 : -2
        ]
        y = np.array([float(line.split()[0]) for line in lines]) * 1e-3
        bias = np.array([bias_offset - float(line.split()[1]) for line in lines])
    elif lines[0].startswith("   Spectrometer(PhSw)-2014   "):
        min_frequency = float(lines[14]) * 1e3
        frequency_step = float(lines[16]) * 1e3
        frequency_jump = float(lines[2]) * 1e3
        cell_length = float(lines[25])
        bias_offset = float(lines[26])
        lines = lines[32:]
        if lines[-1] == "0":
            lines = lines[:-2]
        y = np.array([float(line) for line in lines[::2]]) * 1e-3
        bias = np.array([bias_offset - float(line) for line in lines[1::2]])
    elif lines[0].startswith("   Spectrometer(PhSw)   "):
        min_frequency = float(lines[12]) * 1e3
        frequency_step = float(lines[14]) * 1e3
        frequency_jump = float(lines[2]) * 1e3
        cell_length = float(lines[23])
        bias_offset = float(lines[24])
        lines = lines[30:]
        if lines[-1].split()[-1] == "0":
            lines = lines[:-1]
        y = np.array([float(line.split()[0]) for line in lines]) * 1e-3
        bias = np.array([bias_offset - float(line.split()[1]) for line in lines])
    else:
        min_frequency = float(lines[13]) * 1e3
        frequency_step = float(lines[15]) * 1e3
        frequency_jump = float(lines[2]) * 1e3
        cell_length = float(lines[24])
        bias_offset = float(lines[25])
        lines = lines[31:]
        y = np.array([float(line) for line in lines[::2]]) * 1e-3
        bias = np.array([bias_offset - float(line) for line in lines[1::2]])
    x = np.arange(y.size, dtype=float) * frequency_step + min_frequency
    ok: bool = True
    while cell_length <= 0.0 or not ok:
        cell_length, ok = QInputDialog.getDouble(
            parent,
            parent.windowTitle() if parent is not None else "",
            _translate(
                "dialog prompt",
                "Encountered invalid value of the cell length: {} cm\n"
                "Enter a correct value [cm]:",
            ).format(cell_length),
            100.0,
            0.1,
            1000.0,
            1,
            Qt.WindowType.Dialog,
            0.1,
        )
    return x, y, y / bias / cell_length / VOLTAGE_GAIN, frequency_jump


def load_data_csv(
    filename: Path,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], float]:
    if (filename_csv := filename.with_suffix(".csv")).exists() and (
        filename_conf := filename.with_suffix(".conf")
    ).exists():
        with open(filename_csv) as f_in:
            lines: list[str] = list(
                filter(lambda line: line[0].isdigit(), f_in.readlines())
            )
        x: NDArray[np.float64] = (
            np.array([float(line.split()[1]) for line in lines]) * 1e6
        )
        y: NDArray[np.float64] = (
            np.array([float(line.split()[2]) for line in lines]) * 1e-3
        )
        g: NDArray[np.float64] = np.array([float(line.split()[4]) for line in lines])
        with open(filename_conf) as f_in:
            frequency_jump: float = (
                float(
                    next(
                        filter(
                            lambda line: line.startswith("F(jump) [MHz]:"),
                            f_in.readlines(),
                        )
                    ).split()[-1]
                )
                * 1e3
            )
        return x, y, g, frequency_jump
    return np.empty(0), np.empty(0), np.empty(0), np.nan


class HeaderWithUnit:
    def __init__(self, name: str, unit: str, fmt: str = "") -> None:
        self._name: str = name
        self._unit: str = unit
        self._fmt: str = fmt or _translate("header with unit", "{name} [{unit}]")
        self._str: str = self._fmt.format(name=self._name, unit=self._unit)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_value: str) -> None:
        with suppress(Exception):
            self._str = self._fmt.format(name=new_value, unit=self._unit)
            self._name = new_value

    @property
    def unit(self) -> str:
        return self._unit

    @unit.setter
    def unit(self, new_value: str) -> None:
        with suppress(Exception):
            self._str = self._fmt.format(name=self._name, unit=new_value)
            self._unit = new_value

    @property
    def format(self) -> str:
        return self._fmt

    @format.setter
    def format(self, new_value: str) -> None:
        with suppress(Exception):
            self._str = new_value.format(name=self._name, unit=self._unit)
            self._fmt = new_value

    def __str__(self) -> str:
        return self._str


def find_qm_files(
    root: str | PathLike[str] | None = None,
    *,
    exclude: Collection[str | PathLike[str]] = frozenset(),
) -> Iterator[Path]:
    if root in None:
        root = Path.cwd()
    magic: Final[bytes] = bytes(
        [
            0x3C,
            0xB8,
            0x64,
            0x18,
            0xCA,
            0xEF,
            0x9C,
            0x95,
            0xCD,
            0x21,
            0x1C,
            0xBF,
            0x60,
            0xA1,
            0xBD,
            0xDD,
        ]
    )
    exclude = frozenset(map(Path, exclude))

    def list_files(path: Path) -> set[Path]:
        files: set[Path] = set()
        if path not in exclude:
            if path.is_dir():
                with suppress(PermissionError):
                    for child in path.iterdir():
                        if (child := child.resolve()) not in files:
                            files.update(list_files(child))
            elif path.is_file():
                files.add(path.resolve())
        return files

    file: Path
    f_in: BinaryIO
    for file in list_files(Path(root)):
        with suppress(Exception), open(file, "rb") as f_in:
            if f_in.read(len(magic)) == magic:
                yield file

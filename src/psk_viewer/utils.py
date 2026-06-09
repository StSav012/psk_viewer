import enum
import html
import html.entities
import re
import sys
import unicodedata
from collections.abc import Collection, Iterable, Iterator
from contextlib import contextmanager, suppress
from os import PathLike, linesep
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Final, NamedTuple, TypeVar

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
    "load_data",
    "resource_path",
    "superscript_number",
    "superscript_tag",
    "find_qm_files",
    "load_icon",
    "mix_colors",
    "HeaderWithUnit",
    "FSData",
    "PSKData",
    "SpectrometerData",
    "XValues",
    "DataMode",
    "the",
    "tag",
    "p_tag",
    "wrap_in_html",
    "remove_html",
    "html_to_rtf",
    "best_name",
]

VOLTAGE_GAIN: Final[float] = 5.0


# https://www.reddit.com/r/learnpython/comments/4kjie3/how_to_include_gui_images_with_pyinstaller/d3gjmom
def resource_path(relative_path: str | Path) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / relative_path


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
                <svg
                    viewBox="0 0 32 32"
                    width="32"
                    height="32"
                    xmlns="http://www.w3.org/2000/svg"
                    xmlns:xlink="http://www.w3.org/1999/xlink"
                    fill="none"
                    stroke="foreground"
                    stroke-width="2px"
                    stroke-linejoin="bevel"
                >
                    <g id="d">
                        <path d="m9.5 4.5v10.5"/>
                        <ellipse cx="7.25" cy="11.5" rx="2.25" ry="2.5"/>
                    </g>
                    <path id="2" d="m 12.25,5.4c 0,-1.5 2.5,-1.5 1.75,0.25 -0.25,0.5 -1.24,2.5 -2.75,2.5h 4"/>
                    <path d="m23.5 4.5-18.75 23"/>
                    <path id="x" d="m20 22 3 5.75"/>
                    <use transform="translate(7.5 13)" xlink:href="#d"/>
                    <use transform="translate(12.5 13)" xlink:href="#2"/>
                    <use transform="matrix(-1 0 0 1 43 0)" xlink:href="#x"/>
                </svg>
            """,
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
            "toolbox": QTAData(("mdi6.toolbox",)),
            "configure": QTAData(("mdi6.cogs",)),
            "target": QTAData(("mdi6.target",)),
            "qt_logo": b"""\
                <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 158 120" fill="foreground">
                    <path d="M142.6,0h-5.5H21.9v0L0,21.9V95v6v15.2h15.2h5.5h115.2v0l21.9-21.9V21.1v-6V0H142.6z
                             M84,100.2L73.7,105 l-8.9-14.6c-1.3,0.4-3.3,0.6-6.1,0.6c-10.4,0-17.6-2.8-21.7-8.4
                             c-4.1-5.6-6.1-14.4-6.1-26.5c0-12.1,2.1-21.1,6.2-26.9 c4.2-5.9,11.4-8.8,21.6-8.8
                             c10.3,0,17.4,2.9,21.6,8.7c4.1,5.8,6.2,14.8,6.2,26.9c0,8-0.8,14.5-2.5,19.4
                             c-1.7,4.9-4.5,8.7-8.3,11.3 L84,100.2z
                             M115.2,89.7c-5.7,0-9.5-1.3-11.6-3.9c-2.1-2.6-3.1-7.5-3.1-14.7V48h-7.6v-9.3h7.6V24.2h10.8
                             v14.5H125V48h-13.8v22 c0,4.1,0.3,6.8,0.9,8.1c0.6,1.3,2.1,2,4.6,2l8.2-0.3l0.5,8.7
                             C120.9,89.3,117.5,89.7,115.2,89.7z"/>
                    <path d="M58.7,30c-6.3,0-10.6,2.1-12.9,6.2C43.5,40.4,42.4,47,42.4,56c0,9.1,1.1,15.5,3.4,19.4
                             c2.3,3.9,6.6,5.8,13,5.8 s10.7-1.9,12.9-5.7c2.2-3.8,3.3-10.3,3.3-19.4
                             c0-9.1-1.1-15.7-3.4-19.9C69.3,32.1,65,30,58.7,30z"/>
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


def superscript_tag(html_code: str) -> str:
    """Replace numbers within <sup></sup> with their Unicode superscript analogs."""
    text: str = html_code
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


tag_pattern: re.Pattern[str] = re.compile(
    r"<\s*(?P<tag_name>\w+)(?:\s+[^>]*)?>(?P<content>.*?)(?:</\s*(?P=tag_name)\s*>|$)"
)

tag_repl: dict[str, str] = {
    "html": r"rtf1\ansi{\fonttbl\f0\fnil}",
    "sup": "super",
    "u": "ul",
    "s": "strike",
}
char_repl: dict[str, str] = {"–": "-"}


def rtf_escape(s: str) -> str:
    return "".join(
        (
            c
            if ord(c) < 128
            else "\\u"
            + str(int.from_bytes(c.encode("utf-16be")))
            + char_repl.get(
                c,
                html.entities.codepoint2name.get(
                    ord(c),
                    unicodedata.name(c).split()[-1],
                )[0],
            )
        )
        for c in s
    )


def rtf_table(t: str) -> str:
    r: list[str] = [r"\trowd"]
    cols: int = 0
    for tr, row in tag_pattern.findall(t):
        if tr.lower() != "tr":
            continue
        # noinspection PyTypeChecker
        cells: list[tuple[str, str]] = tag_pattern.findall(row)
        cols = max(cols, len(cells))
        for td, cell in cells:
            if td.lower() != "td":
                continue
            r.append(cell + r"\cell")
        r.append(r"\row")

    r.insert(1, r"\cellx" * cols)
    return "\n".join(r)


def html_tag_to_rtf_tag(m: re.Match[str]) -> str:
    tag_name: str = m.group("tag_name").casefold()
    content: str = m.group("content")
    if tag_name == "table":
        return rtf_table(content)
    if tag_name == "font":  # do nothing
        return content
    tag_name = tag_repl.get(tag_name, tag_name)
    return "{\\" + tag_name + "\n" + content + "}"


def html_to_rtf(htm: str) -> str:
    htm = htm.replace(r"\&", "&").replace("\n", r"\par")
    htm, n = tag_pattern.subn(html_tag_to_rtf_tag, htm)
    while n:
        htm, n = tag_pattern.subn(html_tag_to_rtf_tag, htm)
    return rtf_escape(html.unescape(htm))


def tag(tag_name: str, content: str) -> str:
    return f"<{tag_name}>{content}</{tag_name}>"


def p_tag(content: str) -> str:
    return tag("p", content)


def copy_to_clipboard(
    plain_text: str,
    rich_text: str = "",
    text_type: Qt.TextFormat | str = Qt.TextFormat.PlainText,
) -> None:
    from qtpy.QtCore import QMimeData
    from qtpy.QtGui import QClipboard, QGuiApplication

    clipboard: QClipboard | None = QGuiApplication.clipboard()
    if clipboard is None:
        return
    mime_data: QMimeData = QMimeData()
    if isinstance(text_type, str):
        mime_data.setData(text_type, plain_text.encode())
    elif text_type == Qt.TextFormat.RichText:
        mime_data.setData(
            "text/rtf", html_to_rtf(tag("html", rich_text)).encode("utf-8")
        )
        mime_data.setData("text/markdown", rich_text.encode("utf-8"))
        mime_data.setHtml(wrap_in_html(rich_text))
        mime_data.setText(plain_text)
    else:
        mime_data.setText(plain_text)
    clipboard.setMimeData(mime_data, QClipboard.Mode.Clipboard)


class DataMode(enum.Enum):
    unknown = enum.auto()
    FS = enum.auto()
    PSK = enum.auto()
    PSK_WITH_JUMP = enum.auto()
    TIME_DOMAIN = enum.auto()


class FSData(NamedTuple):
    frequency: NDArray[np.double] = np.empty(0, dtype=np.double)
    voltage: NDArray[np.double] = np.empty(0, dtype=np.double)


class XValues(enum.Enum):
    unknown = enum.auto()
    time = enum.auto()
    frequency = enum.auto()


class PSKData(NamedTuple):
    frequency: NDArray[np.double] = np.empty(0, dtype=np.double)
    voltage: NDArray[np.double] = np.empty(0, dtype=np.double)
    absorption: NDArray[np.double] = np.empty(0, dtype=np.double)
    time: NDArray[np.double] = np.empty(0, dtype=np.double)
    jump: float = np.nan
    mode: XValues = XValues.unknown


class SpectrometerData(NamedTuple):
    filename: Path
    frequency: NDArray[np.double] = np.empty(0, dtype=np.double)
    voltage: NDArray[np.double] = np.empty(0, dtype=np.double)
    absorption: NDArray[np.double] = np.empty(0, dtype=np.double)
    time: NDArray[np.double] = np.empty(0, dtype=np.double)
    mode: DataMode = DataMode.unknown


def load_data_fs(filename: Path) -> FSData:
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
        return FSData()
    if (
        not np.isnan(min_frequency)
        and not np.isnan(max_frequency)
        and (filename_frd := filename.with_suffix(".frd")).exists()
    ):
        y: NDArray[np.float64] = np.loadtxt(filename_frd, usecols=(0,)) * 1e-3
        x: NDArray[np.float64] = np.linspace(
            min_frequency, max_frequency, num=y.size, endpoint=False, dtype=np.float64
        )
        return FSData(x, y)
    return FSData()


def load_data_scandat(filename: Path, parent: QWidget | None) -> PSKData:
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
    return PSKData(
        frequency=x,
        voltage=y,
        absorption=y / bias / cell_length / VOLTAGE_GAIN,
        jump=frequency_jump,
        mode=XValues.frequency,
    )


def time_to_seconds(s: str) -> float:
    r: float = 0.0
    for p in s.split(":"):
        r = r * 60.0 + float(p)
    return r


def load_data_csv(filename: Path) -> PSKData:
    if (filename_csv := filename.with_suffix(".csv")).exists() and (
        filename_conf := filename.with_suffix(".conf")
    ).exists():
        lines: list[str]
        with open(filename_conf) as f_in:
            lines = f_in.readlines()
            mode: XValues = (
                XValues.frequency
                if "frequency trend" in lines[0].casefold()
                else XValues.time
            )
            frequency_jump: float = (
                float(
                    next(
                        filter(
                            lambda line: line.startswith("F(jump) [MHz]:"),
                            lines,
                        )
                    ).split()[-1]
                )
                * 1e3
            )
        with open(filename_csv) as f_in:
            lines = f_in.readlines()
        header: list[str] = lines[0].split() if not lines[0][0].isdigit() else []
        if header:
            time_column = header.index(
                next(filter(lambda title: title.casefold().startswith("time"), header))
            )
            frequency_column = header.index(
                next(
                    filter(
                        lambda title: title.casefold().startswith("frequency"), header
                    )
                )
            )
            voltage_column = header.index(
                next(
                    filter(
                        lambda title: title.casefold().startswith("amplitude"), header
                    )
                )
            )
            absorption_column = header.index(
                next(filter(lambda title: title.casefold().startswith("gamma"), header))
            )
        else:
            # as the last resort
            frequency_column = 1
            voltage_column = 2
            absorption_column = 4
            time_column = -1
        words: list[list[str]] = [
            line.split()
            for line in filter(lambda line: line[0].isdigit(), lines[bool(header) :])
        ]
        frequency: NDArray[np.double] = (
            np.array([float(line[frequency_column]) for line in words]) * 1e6
        )
        time: NDArray[np.double] = np.array(
            [time_to_seconds(line[time_column]) for line in words]
        )
        voltage: NDArray[np.double] = (
            np.array([float(line[voltage_column]) for line in words]) * 1e-3
        )
        absorption: NDArray[np.double] = np.array(
            [float(line[absorption_column]) for line in words]
        )
        return PSKData(
            frequency=frequency,
            voltage=voltage,
            absorption=absorption,
            time=time,
            jump=frequency_jump,
            mode=mode,
        )
    return PSKData()


def load_data(
    parent: QWidget | None, filename: str | PathLike[str]
) -> SpectrometerData | None:
    v: NDArray[np.float64]
    f: NDArray[np.float64]
    g: NDArray[np.float64] = np.empty(0)
    t: NDArray[np.float64] = np.empty(0)
    jump: float
    m: XValues
    data_mode: DataMode = DataMode.unknown
    if not isinstance(filename, Path):
        filename = Path(filename)
    if filename.suffix.casefold() == ".scandat":
        f, v, g, t, jump, m = load_data_scandat(filename, parent)
        if f.size and v.size:
            data_mode = DataMode.PSK_WITH_JUMP if jump > 0.0 else DataMode.PSK
        elif m == XValues.time and t.size and v.size:
            data_mode = DataMode.TIME_DOMAIN
    elif filename.suffix.casefold() in (".csv", ".conf"):
        f, v, g, t, jump, m = load_data_csv(filename)
        if m == XValues.frequency and f.size and v.size:
            data_mode = DataMode.PSK_WITH_JUMP if jump > 0.0 else DataMode.PSK
        elif m == XValues.time and t.size and v.size:
            data_mode = DataMode.TIME_DOMAIN
    elif filename.suffix.casefold() in (".fmd", ".frd"):
        f, v = load_data_fs(filename)
        if f.size and v.size:
            data_mode = DataMode.FS
    else:
        return None

    return SpectrometerData(filename, f, g, v, t, data_mode)


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
    if root is None:
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


_T = TypeVar("_T")


@contextmanager
def the(obj: _T) -> Iterator[_T]:
    yield obj


def is_good_html(text: str) -> bool:
    _1, _2, _3 = text.count("<"), text.count(">"), 2 * text.count("</")
    return _1 == _2 and _1 == _3


def wrap_in_html(text: str, line_end: str = linesep) -> str:
    """Make a full HTML document out of a piece of the markup."""
    new_text: list[str] = [
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">',
        '<html lang="en" xml:lang="en">',
        "<head>",
        '<meta http-equiv="content-type" content="text/html; charset=utf-8">',
        "</head>",
        "<body>",
        text,
        "</body>",
        "</html>",
    ]

    return line_end.join(new_text)


def remove_html(line: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    from html import unescape

    if not is_good_html(line):
        return unescape(line)

    new_line: str = line
    tag_start: int = new_line.find("<")
    tag_end: int = new_line.find(">", tag_start)
    while tag_start != -1 and tag_end != -1:
        new_line = new_line[:tag_start] + new_line[tag_end + 1 :]
        tag_start = new_line.find("<")
        tag_end = new_line.find(">", tag_start)
    return unescape(new_line).lstrip()


def best_name(entry: object, allow_html: bool = True) -> str:
    import html.entities
    from html import escape, unescape

    try:
        from pycatsearch.utils import (
            NAME,
            STOICHIOMETRIC_FORMULA,
            STRUCTURAL_FORMULA,
            CatalogEntryType,
        )
    except ImportError:
        return repr(entry)

    if not isinstance(entry, CatalogEntryType):
        raise TypeError("Unsupported entry type")

    species_tag: int = entry.speciestag
    last: str = (
        best_name.__dict__.get("last", dict())
        .get(species_tag, dict())
        .get(allow_html, "")
    )
    if last:
        return last

    def chem_html(formula: str) -> str:
        """Convert plain text chemical formula into HTML markup."""
        if "<" in formula or ">" in formula:
            # we can not tell whether it's a tag or a mathematical sign
            return formula

        def sub_tag(s: str) -> str:
            return "<sub>" + s + "</sub>"

        def sup_tag(s: str) -> str:
            return "<sup>" + s + "</sup>"

        def i_tag(s: str) -> str:
            return "<i>" + s + "</i>"

        def subscript(s: str) -> str:
            number_start: int = -1
            number_started: bool = False
            cap_alpha_started: bool = False
            low_alpha_started: bool = False
            _i: int = 0
            while _i < len(s):
                _c: str = s[_i]
                if number_started and not _c.isdigit():
                    number_started = False
                    s = s[:number_start] + sub_tag(s[number_start:_i]) + s[_i:]
                    _i += 1
                if (
                    (cap_alpha_started or low_alpha_started)
                    and _c.isdigit()
                    and not number_started
                ):
                    number_start = _i
                    number_started = True
                if low_alpha_started:
                    cap_alpha_started = False
                    low_alpha_started = False
                if cap_alpha_started and _c.islower() or _c == ")":
                    low_alpha_started = True
                cap_alpha_started = _c.isupper()
                _i += 1
            if number_started:
                s = s[:number_start] + sub_tag(s[number_start:])
            return s

        def prefix(s: str) -> str:
            no_digits: bool = False
            _i: int = len(s)
            while not no_digits:
                _i = s.rfind("-", 0, _i)
                if _i == -1:
                    break
                if s[:_i].isalpha() and s[:_i].isupper():
                    break
                no_digits = True
                _c: str
                unescaped_prefix: str = unescape(s[:_i])
                for _c in unescaped_prefix:
                    if _c.isdigit() or _c == "<":
                        no_digits = False
                        break
                if no_digits and (
                    unescaped_prefix[0].islower() or unescaped_prefix[0] == "("
                ):
                    return i_tag(s[:_i]) + s[_i:]
            return s

        def charge(s: str) -> str:
            if s[-1] in "+-":
                return s[:-1] + sup_tag(s[-1])
            return s

        def v(s: str) -> str:
            if "=" not in s:
                return s[0] + " = " + s[1:]
            ss: list[str] = list(map(str.strip, s.split("=")))
            for _i in range(len(ss)):
                if ss[_i].startswith("v"):
                    ss[_i] = ss[_i][0] + sub_tag(ss[_i][1:])
            return " = ".join(ss)

        html_formula: str = escape(formula)
        html_formula_pieces: list[str] = list(map(str.strip, html_formula.split(",")))
        for i in range(len(html_formula_pieces)):
            if html_formula_pieces[i].startswith("v"):
                html_formula_pieces = html_formula_pieces[:i] + [
                    ", ".join(html_formula_pieces[i:])
                ]
                break
        for i in range(len(html_formula_pieces)):
            if html_formula_pieces[i].startswith("v"):
                html_formula_pieces[i] = v(html_formula_pieces[i])
                break
            for function in (subscript, prefix, charge):
                html_formula_pieces[i] = function(html_formula_pieces[i])
        return ", ".join(html_formula_pieces)

    def tex_to_html_entity(s: str) -> str:
        r"""Change LaTeX entities syntax to HTML one.

        Get ‘\alpha’ to be ‘&alpha;’ and so on.
        Unknown LaTeX entities do not get replaced.

        :param s: A line to convert
        :return: a line with all LaTeX entities renamed
        """
        word_start: int = -1
        word_started: bool = False
        backslash_found: bool = False
        _i: int = 0
        fixes: dict[str, str] = {
            "neq": "#8800",
        }
        while _i < len(s):
            _c: str = s[_i]
            if word_started and not _c.isalpha():
                word_started = False
                if s[word_start:_i] + ";" in html.entities.entitydefs:
                    s = s[: word_start - 1] + "&" + s[word_start:_i] + ";" + s[_i:]
                    _i += 2
                elif s[word_start:_i] in fixes:
                    s = (
                        s[: word_start - 1]
                        + "&"
                        + fixes[s[word_start:_i]]
                        + ";"
                        + s[_i:]
                    )
                    _i += 2
            if backslash_found and _c.isalpha() and not word_started:
                word_start = _i
                word_started = True
            backslash_found = _c == "\\"
            _i += 1
        if word_started:
            if s[word_start:_i] + ";" in html.entities.entitydefs:
                s = s[: word_start - 1] + "&" + s[word_start:_i] + ";" + s[_i:]
                _i += 2
            elif s[word_start:_i] in fixes:
                s = s[: word_start - 1] + "&" + fixes[s[word_start:_i]] + ";" + s[_i:]
                _i += 2
        return s

    def _best_name() -> str:
        if TYPE_CHECKING and not isinstance(entry, CatalogEntryType):
            raise TypeError("Unsupported entry type")

        if isotopolog := entry.isotopolog:
            if allow_html:
                if is_good_html(str(molecule_symbol := entry.moleculesymbol)) and (
                    entry.structuralformula == isotopolog
                    or entry.stoichiometricformula == isotopolog
                ):
                    if state_html := entry.state_html:
                        # span tags are needed when the molecule symbol is malformed
                        return f"<span>{molecule_symbol}</span>, {chem_html(tex_to_html_entity(str(state_html)))}"
                    return str(molecule_symbol)
                if state_html := entry.state_html:
                    return f"{chem_html(str(isotopolog))}, {chem_html(tex_to_html_entity(str(state_html)))}"
                return chem_html(str(isotopolog))
            if state_html := entry.state_html:
                return f"{isotopolog}, {remove_html(tex_to_html_entity(state_html))}"
            if state := entry.state:
                return (
                    f"{isotopolog}, {remove_html(tex_to_html_entity(state.strip('$')))}"
                )
            return isotopolog

        for key in (NAME, STRUCTURAL_FORMULA, STOICHIOMETRIC_FORMULA):
            if candidate := getattr(entry, key, ""):
                return chem_html(str(candidate)) if allow_html else str(candidate)
        if trivial_name := entry.trivialname:
            return str(trivial_name)
        if species_tag:
            return str(species_tag)
        return "no name"

    res: str = _best_name()
    if not species_tag:
        return res
    if "last" not in best_name.__dict__:
        best_name.__dict__["last"] = dict()
    if species_tag not in best_name.__dict__["last"]:
        best_name.__dict__["last"][species_tag] = dict()
    best_name.__dict__["last"][species_tag][allow_html] = res
    return res

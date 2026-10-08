import html
import html.entities
import itertools
import os
import re

__all__ = [
    "chem_html",
    "is_good_html",
    "p_tag",
    "remove_html",
    "tag",
    "tex_to_html_entity",
    "wrap_in_html",
]


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

    def replace_word() -> None:
        nonlocal s, _i
        if s[word_start:_i] + ";" in html.entities.entitydefs:
            s = s[: word_start - 1] + "&" + s[word_start:_i] + ";" + s[_i:]
            _i += 2
        elif s[word_start:_i] in fixes:
            s = s[: word_start - 1] + "&" + fixes[s[word_start:_i]] + ";" + s[_i:]
            _i += 2

    while _i < len(s):
        _c: str = s[_i]
        if word_started and not _c.isalpha():
            word_started = False
            replace_word()
        if backslash_found and _c.isalpha() and not word_started:
            word_start = _i
            word_started = True
        backslash_found = _c == "\\"
        _i += 1
    if word_started:
        replace_word()
    return s


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


isotope_pattern: re.Pattern[str] = re.compile(
    r"(?P<par>\()?(?P<element>[A-Z][a-z]?)-(?P<mass>\d+)(?(par)\)|-?)"
)


def _isotope_repl(m: re.Match[str]) -> str:
    return sup_tag(m["mass"]) + m["element"]


def isotope(s: str) -> str:
    return isotope_pattern.sub(_isotope_repl, s)


def prefix(s: str) -> str:
    parts: list[str] = s.split("-")
    for i in range(len(parts) - 1, -1, -1):
        part: str = html.unescape(parts[i])
        if not part or part.isdecimal():
            continue
        if (
            (
                ("'" in part)
                or part[0].islower()
                or part.endswith(
                    ("A", "D", "E", "G", "J", "L", "M", "Q", "R", "T", "X", "Z")
                )
            )
            and part.count("(") == part.count(")")
            and not any(c.isdigit() for c in part)
        ):
            return "-".join([i_tag(p) for p in parts[: i + 1]] + parts[i + 1 :])
    return s


def charge(s: str) -> str:
    if s[-1] in "+-":
        return s[:-1] + sup_tag(s[-1])
    return s


v_or_nu_pattern: re.Pattern[str] = re.compile(
    r"(?P<plus>\s*\+?\s*)(?<!\w)(?P<factor>\d*\s*)(?P<v_or_nu>[vν])(?P<subscript>[\dt]*)"
)


def v_or_nu(s: str) -> str:
    ss: list[str] = list(map(str.strip, s.split("=")))
    for i in range(len(ss)):
        pos: int = 0
        while m := v_or_nu_pattern.search(ss[i], pos=pos):
            new_v_or_nu: str = m["v_or_nu"]
            if m["factor"]:
                new_v_or_nu = m["factor"].strip() + " " + new_v_or_nu
            if m["plus"]:
                new_v_or_nu = m["plus"].strip() + " " + new_v_or_nu
                if m.start() > 0:
                    new_v_or_nu = " " + new_v_or_nu
            if m["subscript"]:
                new_v_or_nu += sub_tag(m["subscript"])
            ss[i] = ss[i][: m.start()] + new_v_or_nu + ss[i][m.end() :]
            pos = m.end()
    return " = ".join(ss)


def chem_html(formula: str) -> str:
    """Convert plain text chemical formula into HTML markup."""
    html_formula_pieces: list[str] = [
        html.escape(p.strip()) for p in formula.split(",")
    ]
    for i in range(len(html_formula_pieces)):
        if v_or_nu_pattern.search(html_formula_pieces[i]):
            html_formula_pieces = html_formula_pieces[:i] + [
                ", ".join(html_formula_pieces[i:])
            ]
            break
    for i in range(len(html_formula_pieces)):
        for function in (subscript, isotope, prefix, charge, v_or_nu):
            html_formula_pieces[i] = function(html_formula_pieces[i])
    return ", ".join(html_formula_pieces)


def is_good_html(text: str) -> bool:
    """Check that all tags are sound."""
    _1, _2, _3 = text.count("<"), text.count(">"), 2 * text.count("</")
    return _1 == _2 and _1 == _3


def remove_html(line: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    if not is_good_html(line):
        return html.unescape(line)

    new_line: str = line
    tag_start: int = new_line.find("<")
    tag_end: int = new_line.find(">", tag_start)
    while tag_start != -1 and tag_end != -1:
        new_line = new_line[:tag_start] + new_line[tag_end + 1 :]
        tag_start = new_line.find("<")
        tag_end = new_line.find(">", tag_start)
    return html.unescape(new_line).lstrip()


def wrap_in_html(text: str, line_end: str = os.linesep) -> str:
    """Make a full HTML document out of a piece of the markup."""
    new_text: list[str] = [
        "<!DOCTYPE HTML>",
        "<html>",
        "<head>",
        '<meta http-equiv="content-type" content="text/html; charset=utf-8"/>',
        "</head>",
        "<body>",
        text,
        "</body>",
        "</html>",
    ]

    return line_end.join(new_text)


def tag(name: str, text: str = "", **attrs: str) -> str:
    return "".join(
        [
            "<",
            " ".join(
                (
                    name,
                    *itertools.starmap(lambda a, v: f"{a}={str(v)!r}", attrs.items()),
                )
            ),
            ">",
            text,
            "</",
            name,
            ">",
        ]
    )


def p_tag(text: str) -> str:
    return tag("p", text)


def i_tag(text: str) -> str:
    return tag("i", text)


def sub_tag(text: str) -> str:
    return tag("sub", text)


def sup_tag(text: str) -> str:
    return tag("sup", text)

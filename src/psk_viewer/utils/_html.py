import html
import html.entities
import itertools
import os

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
        unescaped_prefix: str = html.unescape(s[:_i])
        for _c in unescaped_prefix:
            if _c.isdigit() or _c == "<":
                no_digits = False
                break
        if no_digits and (
            unescaped_prefix[0].islower()
            or unescaped_prefix[0] == "("
            and unescaped_prefix.count("(") == unescaped_prefix.count(")")
        ):
            return i_tag(s[:_i]) + s[_i:]
    return s


def charge(s: str) -> str:
    if s[-1] in "+-":
        return s[:-1] + sup_tag(s[-1])
    return s


def v_or_nu(s: str) -> str:
    if "=" not in s:
        return s[0] + " = " + s[1:]
    ss: list[str] = list(map(str.strip, s.split("=")))
    for _i in range(len(ss)):
        if ss[_i].startswith(("v", "ν")) and ss[_i][1:]:
            ss[_i] = ss[_i][0] + sub_tag(ss[_i][1:])
    return " = ".join(ss)


def chem_html(formula: str) -> str:
    """Convert plain text chemical formula into HTML markup."""
    if "<" in formula or ">" in formula:
        # we cannot tell whether it's a tag or a mathematical sign
        return formula

    html_formula: str = html.escape(formula)
    html_formula_pieces: list[str] = list(map(str.strip, html_formula.split(",")))
    for i in range(len(html_formula_pieces)):
        if html_formula_pieces[i].startswith("v"):
            html_formula_pieces = html_formula_pieces[:i] + [
                ", ".join(html_formula_pieces[i:])
            ]
            break
    for i in range(len(html_formula_pieces)):
        if html_formula_pieces[i].startswith("v"):
            html_formula_pieces[i] = v_or_nu(html_formula_pieces[i])
            break
        for function in (subscript, prefix, charge):
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
    parts: list[str] = [
        "<",
        " ".join(
            (name, *itertools.starmap(lambda a, v: f"{a}={str(v)!r}", attrs.items()))
        ),
    ]
    if text:
        parts.extend([">", text, "</", name, ">"])
    else:
        parts.append("/>")
    return "".join(parts)


def p_tag(text: str) -> str:
    return tag("p", text)


def i_tag(text: str) -> str:
    return tag("i", text)


def sub_tag(text: str) -> str:
    return tag("sub", text)


def sup_tag(text: str) -> str:
    return tag("sup", text)

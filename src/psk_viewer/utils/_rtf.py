import html
import html.entities
import re
import unicodedata

__all__ = ["html_to_rtf"]


tag_pattern: re.Pattern[str] = re.compile(
    r"<\s*(?P<tag_name>\w+)\s*(?P<attrs>[^>]*)?>(?P<content>.*?)(?:</\s*(?P=tag_name)\s*>|\n|$)"
)
empty_tag_pattern: re.Pattern[str] = re.compile(
    r"<\s*(?P<tag_name>\w+)\s*(?P<attrs>[^>]*)?\s*/>"
)
size_pattern: re.Pattern[str] = re.compile(
    r"size\s*=\s*(?P<q>|'|\")\s*(?P<size>\d+)\s*(?:pt)?\s*(?P=q)"
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
            + str(int.from_bytes(c.encode("utf-16be"), byteorder="big"))
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
    for tr, _, row in tag_pattern.findall(t):
        if tr.lower() != "tr":
            continue
        cells: list[tuple[str, str]] = tag_pattern.findall(row)
        cols = max(cols, len(cells))
        for td, _, cell in cells:
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
    if tag_name == "font":
        attrs: str | None = m.group("attrs")
        if attrs is not None:
            size_match: re.Match[str] | None = size_pattern.search(attrs)
            if size_match is not None:
                return (
                    "{\\fs"
                    + str(int(size_match.group("size")) * 2)
                    + "\n"
                    + content
                    + "}"
                )
        # otherwise, do nothing
        return content
    tag_name = tag_repl.get(tag_name, tag_name)
    return "{\\" + tag_name + "\n" + content + "}"


def html_to_rtf(htm: str) -> str:
    htm = htm.replace(r"\&", "&").replace("\n", r"\par")
    htm, n = tag_pattern.subn(html_tag_to_rtf_tag, htm)
    while n:
        htm, n = tag_pattern.subn(html_tag_to_rtf_tag, htm)
    htm, n = empty_tag_pattern.subn("", htm)
    while n:
        htm, n = empty_tag_pattern.subn("", htm)
    return rtf_escape(html.unescape(htm))

import re
import zipfile
from io import BytesIO

from . import tag

__all__ = ["html_to_ods", "ods_object_descriptor"]


tag_pattern: re.Pattern[str] = re.compile(
    r"<\s*(?P<tag_name>\w+)\s*(?P<attrs>[^>]*)?>(?P<content>.*?)</\s*(?P=tag_name)\s*>",
    re.IGNORECASE | re.DOTALL,
)
empty_tag_pattern: re.Pattern[str] = re.compile(
    r"<\s*(?P<tag_name>\w+)\s*(?P<attrs>[^>]*)?\s*/>\n*",
    re.IGNORECASE,
)
doctype_tag_pattern: re.Pattern[str] = re.compile(
    r"<\s*!\s*DOCTYPE.*?>\n*",
    re.IGNORECASE | re.DOTALL,
)

tag_repl: dict[str, tuple[str, dict[str, str]]] = {
    "html": (
        "office:document-content",
        {
            "xmlns:office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
            "xmlns:ooo": "http://openoffice.org/2004/office",
            "xmlns:fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "xmlns:oooc": "http://openoffice.org/2004/calc",
            "xmlns:style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
            "xmlns:text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
            "xmlns:table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
            "office:version": "1.4",
        },
    ),
    "table": ("table:table", {}),
    "tr": ("table:table-row", {}),
    "sub": ("text:span", {"text:style-name": "sub"}),
    "sup": ("text:span", {"text:style-name": "sup"}),
    "i": ("text:span", {"text:style-name": "i"}),
    "b": ("text:span", {"text:style-name": "b"}),
    "u": ("text:span", {"text:style-name": "u"}),
    "s": ("text:span", {"text:style-name": "s"}),
}


def html_tag_to_ods_tag(m: re.Match[str]) -> str:
    tag_name: str = m.group("tag_name").casefold()
    content: str = m.group("content")
    if tag_name == "span":
        return content
    if tag_name == "head":
        return tag(
            "office:automatic-styles",
            """
    <style:style style:name="b" style:family="text">
        <style:text-properties fo:font-weight="bold"/>
    </style:style>
    <style:style style:name="i" style:family="text">
        <style:text-properties fo:font-style="italic"/>
    </style:style>
    <style:style style:name="u" style:family="text">
        <style:text-properties style:text-underline-style="solid" style:text-underline-width="auto" style:text-underline-color="font-color"/>
    </style:style>
    <style:style style:name="s" style:family="text">
        <style:text-properties style:text-line-through-type="single"/>
    </style:style>
    <style:style style:name="sub" style:family="text">
        <style:text-properties style:text-position="sub"/>
    </style:style>
    <style:style style:name="sup" style:family="text">
        <style:text-properties style:text-position="super"/>
    </style:style>
    """,
        )
    if tag_name == "body":
        return tag(
            "office:body", tag("office:spreadsheet", html_to_office_xml(content))
        )
    if tag_name == "td":
        try:
            float(content)
        except ValueError:
            return tag(
                "table:table-cell",
                tag("text:p", html_to_office_xml(content)),
                **{"office:value-type": "string"},
            )
        else:
            return tag(
                "table:table-cell",
                tag("text:p", content),
                **{"office:value-type": "float", "office:value": content},
            )
    tag_name, tag_attrs = tag_repl.get(tag_name, (tag_name, {}))
    return tag(tag_name, content, **tag_attrs)


def html_to_office_xml(htm: str) -> str:
    htm = htm.replace(r"\&", "&")
    htm = doctype_tag_pattern.sub("", htm)

    new_htm = empty_tag_pattern.sub("", htm)
    while new_htm != htm:
        htm = new_htm
        new_htm = empty_tag_pattern.sub("", htm)

    new_htm = tag_pattern.sub(html_tag_to_ods_tag, htm)
    while new_htm != htm:
        htm = new_htm
        new_htm = tag_pattern.sub(html_tag_to_ods_tag, htm)
    return new_htm


def html_to_ods(htm: str) -> bytes:
    # Create an in-memory ZIP file
    zip_buffer: BytesIO = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zipf:
        # Add mimetype
        mimetype_content: bytes = b"application/vnd.oasis.opendocument.spreadsheet"
        zipf.writestr("mimetype", mimetype_content, zipfile.ZIP_STORED)

        # Add META-INF/manifest.xml
        manifest_xml_content: bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.4">
    <manifest:file-entry manifest:full-path="/" manifest:version="1.4" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>
    <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
    <manifest:file-entry manifest:full-path="manifest.rdf" manifest:media-type="application/rdf+xml"/>
    <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
    <manifest:file-entry manifest:full-path="settings.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""
        zipf.writestr("META-INF/manifest.xml", manifest_xml_content)

        # Add content.xml
        content_xml_content: str = (
            """<?xml version="1.0" encoding="UTF-8"?>""" + html_to_office_xml(htm)
        )
        zipf.writestr("content.xml", content_xml_content)

        # Add manifest.rdf
        manifest_rdf_content: bytes = b"""<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="styles.xml">
    <rdf:type rdf:resource="http://docs.oasis-open.org/ns/office/1.2/meta/odf#StylesFile"/>
  </rdf:Description>
  <rdf:Description rdf:about="">
    <ns0:hasPart xmlns:ns0="http://docs.oasis-open.org/ns/office/1.2/meta/pkg#" rdf:resource="styles.xml"/>
  </rdf:Description>
  <rdf:Description rdf:about="content.xml">
    <rdf:type rdf:resource="http://docs.oasis-open.org/ns/office/1.2/meta/odf#ContentFile"/>
  </rdf:Description>
  <rdf:Description rdf:about="">
    <ns0:hasPart xmlns:ns0="http://docs.oasis-open.org/ns/office/1.2/meta/pkg#" rdf:resource="content.xml"/>
  </rdf:Description>
  <rdf:Description rdf:about="">
    <rdf:type rdf:resource="http://docs.oasis-open.org/ns/office/1.2/meta/pkg#Document"/>
  </rdf:Description>
</rdf:RDF>
"""
        zipf.writestr("manifest.rdf", manifest_rdf_content)

        # Add settings.xml
        settings_xml_content: bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-settings xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.4"/>
"""
        zipf.writestr("settings.xml", settings_xml_content)

        # Add styles.xml
        styles_xml_content: bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.4"/>
"""
        zipf.writestr("styles.xml", styles_xml_content)

    # Return the in-memory ZIP file
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def ods_object_descriptor(
    *,
    displayname: str = "",
    typename: str = "LibreOffice 26.8 Spreadsheet",
    classname: str = "47BBB4CB-CE4C-4E80-a591-42d9ae74950f",
    width: int = 2048,
    height: int = 512,
    viewaspect: int = 1,
    posx: int = 0,
    posy: int = 0,
) -> tuple[str, bytes]:
    from uuid import UUID

    def sized_string(s: str) -> bytes:
        b: bytes = s.encode("ascii")
        return len(b).to_bytes(2, "little") + b

    data: bytes = (
        UUID(classname).bytes_le
        + viewaspect.to_bytes(4, "little")
        + width.to_bytes(4, "little")
        + height.to_bytes(4, "little")
        + posx.to_bytes(4, "little")
        + posy.to_bytes(4, "little")
        + sized_string(typename)
        + sized_string(classname)
        + (0x01234567).to_bytes(4, "little")
        + (0x89ABCDEF).to_bytes(4, "little")
    )

    return (
        ";".join(
            (
                "application/x-openoffice-objectdescriptor-xml",
                'windows_formatname="Star Object Descriptor (XML)"',
                f'classname="{classname}"',
                f'typename="{typename}"',
                f'displayname="{displayname}"',
                f'viewaspect="{viewaspect}"',
                f'width="{width}"',
                f'height="{height}"',
                f'posx="{posx}"',
                f'posy="{posy}"',
            )
        ),
        (len(data) + 4).to_bytes(4, "little") + data,
    )

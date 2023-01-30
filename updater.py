# -*- coding: utf-8 -*-
from __future__ import annotations

import http.client
import io
import json
import urllib.request
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import Final

__all__ = ['update']


def update(user: str, repo_name: str, branch: str = 'master') -> None:
    extraction_root: Path = Path.cwd()

    commits_url: Final[str] = f'https://api.github.com/repos/{user}/{repo_name}/commits?page=1&per_page=1'
    r: http.client.HTTPResponse = urllib.request.urlopen(commits_url, timeout=1)
    if r.getcode() != 200:
        return
    content: bytes = r.read()
    if not content:
        return
    d: list[dict[str, dict[str, dict[str, str]]]] = json.loads(content)
    if not isinstance(d, list) or not d:
        return
    date: Final[str] = d[0].get('commit', dict()).get('author', dict()).get('date', '')
    if (extraction_root / Path('version.py')).exists():
        with suppress(BaseException):  # suppress everything
            import version

            if version.UPDATED == f'{date}':
                return
    (extraction_root / Path('version.py')).write_text(f'UPDATED: str = "{date}"\n')

    repo_url: Final[str] = f'https://github.com/{user}/{repo_name}/archive/{branch}.zip'
    r = urllib.request.urlopen(repo_url, timeout=1)
    if r.getcode() != 200:
        return
    inner_zip: zipfile.ZipFile
    with zipfile.ZipFile(io.BytesIO(r.read())) as inner_zip:
        root: Path = Path(f'{repo_name}-{branch}/')
        member: zipfile.ZipInfo
        for member in inner_zip.infolist():
            if member.is_dir():
                continue
            content = inner_zip.read(member)
            (extraction_root / Path(member.filename).relative_to(root)).parent.mkdir(parents=True, exist_ok=True)
            (extraction_root / Path(member.filename).relative_to(root)).write_bytes(content)

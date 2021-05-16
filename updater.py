# -*- coding: utf-8 -*-

import http.client
import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import BinaryIO, Dict, Final, List, TextIO


def update(user: str, repo_name: str, branch: str = 'master') -> None:
    extraction_root: Path = Path.cwd()

    commits_url: Final[str] = f'https://api.github.com/repos/{user}/{repo_name}/commits?page=1&per_page=1'
    r: http.client.HTTPResponse = urllib.request.urlopen(commits_url, timeout=1)
    if r.getcode() != 200:
        return
    content: bytes = r.read()
    if not content:
        return
    d: List[Dict[str, Dict[str, Dict[str, str]]]] = json.loads(content)
    if not isinstance(d, list) or not len(d):
        return
    date: Final[str] = d[0].get('commit', dict()).get('author', dict()).get('date', '')
    if (extraction_root / Path('version.py')).exists():
        try:
            import version

            if version.UPDATED == f'{date}':
                return
        except (OSError, ImportError, ModuleNotFoundError):
            pass
    text_f_out: TextIO
    with (extraction_root / Path('version.py')).open('wt') as text_f_out:
        text_f_out.write(f'UPDATED: str = "{date}"\n')

    repo_url: Final[str] = f'https://github.com/{user}/{repo_name}/archive/{branch}.zip'
    r = urllib.request.urlopen(repo_url, timeout=1)
    if r.getcode() != 200:
        return
    with zipfile.ZipFile(io.BytesIO(r.read())) as inner_zip:
        root: Path = Path(f'{repo_name}-{branch}/')
        for member in inner_zip.infolist():
            if member.is_dir():
                continue
            content = inner_zip.read(member)
            (extraction_root / Path(member.filename).relative_to(root)).parent.mkdir(parents=True, exist_ok=True)
            binary_f_out: BinaryIO
            with (extraction_root / Path(member.filename).relative_to(root)).open('wb') as binary_f_out:
                binary_f_out.write(content)

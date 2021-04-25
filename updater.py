import http.client
import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Type, Union

try:
    from typing import Final
except ImportError:
    class _Final:
        @staticmethod
        def __getitem__(item: Type):
            return item


    Final = _Final()


def update(user: str, repo_name: str, branch: str = 'master'):
    extraction_root: Path = Path.cwd()
    url: str = f'https://github.com/{user}/{repo_name}/archive/{branch}.zip'
    r: http.client.HTTPResponse = urllib.request.urlopen(url, timeout=1)
    if r.getcode() != 200:
        return
    with zipfile.ZipFile(io.BytesIO(r.read())) as inner_zip:
        root: Path = Path(f'{repo_name}-{branch}/')
        for member in inner_zip.infolist():
            if member.is_dir():
                continue
            content: bytes = inner_zip.read(member)
            (extraction_root / Path(member.filename).relative_to(root)).parent.mkdir(parents=True, exist_ok=True)
            with (extraction_root / Path(member.filename).relative_to(root)).open('wb') as f_out:
                f_out.write(content)
    url: str = f'https://api.github.com/repos/{user}/{repo_name}/commits?page=1&per_page=1'
    r: http.client.HTTPResponse = urllib.request.urlopen(url, timeout=1)
    if r.getcode() != 200:
        return
    content: bytes = r.read()
    if not content:
        return
    d: List[Dict[str,
                 Union[str,
                       Dict[str,
                            Union[str,
                                  int,
                                  bool,
                                  Dict[str,
                                       Union[None,
                                             str,
                                             bool]]]],
                       List[Dict[str, str]]]]] \
        = json.loads(content)
    if not isinstance(d, list) or not len(d):
        return
    date: Final[str] = d[0].get('commit', dict()).get('author', dict()).get('date', '')
    with (extraction_root / Path('version.py')).open('w') as f_out:
        f_out.write(f'UPDATED: str = "{date}"\n')

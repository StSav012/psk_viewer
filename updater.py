# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import subprocess
import sys
import urllib.request
from contextlib import suppress
from datetime import datetime
from http.client import HTTPResponse
from pathlib import Path

__all__ = ['update_from_github', 'update_with_git', 'update_with_pip']

logger: logging.Logger = logging.getLogger('updater')


def from_iso_format(s: str) -> datetime:
    if sys.version_info < (3, 11):
        # NB: 'W' specifier is not fixed
        if s.endswith('Z'):  # '2011-11-04T00:05:23Z'
            s = s[:-1] + '+00:00'
        if s.isdigit() and len(s) == 8:  # '20111104'
            s = '-'.join((s[:4], s[4:6], s[6:]))
        elif s[:8].isdigit() and s[9:].isdigit() and len(s) >= 13:  # '20111104T000523'
            s = '-'.join((s[:4], s[4:6], s[6:8])) + s[8] + ':'.join((s[9:11], s[11:13], s[13:]))
    return datetime.fromisoformat(s)


def get_github_date(user: str, repo_name: str, branch: str = 'master') -> datetime | None:
    import json

    url: str = f'https://api.github.com/repos/{user}/{repo_name}/commits/{branch}'
    logger.debug(f'Requesting {url}')
    r: HTTPResponse = urllib.request.urlopen(url, timeout=1)
    logger.debug(f'Response code: {r.getcode()}')
    if r.getcode() != 200:
        logger.warning(f'Response code is not OK: {r.getcode()}')
        return None
    content: bytes = r.read()
    if not content:
        logger.warning(f'No data received from {url}')
        return None
    d: dict[str, str
                 | dict[str, bool | int | str]
                 | dict[str, int | str | dict[str, bool | str] | dict[str, str]]
                 | dict[str, int]
                 | list[dict[str, int | str]]
                 | list[dict[str, str]]] \
        = json.loads(content)
    if not isinstance(d, dict) or not d:
        logger.warning(f'Malformed JSON received: {d}')
        return None
    commit: dict[str, int | str | dict[str, bool | str] | dict[str, str]] = d.get('commit', dict())
    if not isinstance(commit, dict):
        logger.warning(f'Malformed commit info received: {commit}')
        return None
    committer: dict[str, str] = commit.get('committer', dict())
    if not isinstance(committer, dict) or 'date' not in committer:
        logger.warning(f'Malformed commit committer info received: {committer}')
        return None
    try:
        return from_iso_format(committer['date'])
    except ValueError:
        return None


def upgrade_files(code_directory: Path, user: str, repo_name: str, branch: str = 'master') -> bool:
    """ Replace the files in `code_directory` with the newer versions acquired from GitHub """

    import io
    import zipfile

    url: str = f'https://github.com/{user}/{repo_name}/archive/{branch}.zip'
    logger.debug(f'Requesting {url}')
    r: HTTPResponse = urllib.request.urlopen(url, timeout=1)
    logger.debug(f'Response code: {r.getcode()}')
    if r.getcode() != 200:
        logger.warning(f'Response code is not OK: {r.getcode()}')
        return False
    with zipfile.ZipFile(io.BytesIO(r.read())) as inner_zip:
        root: Path = Path(f'{repo_name}-{branch}/')
        member: zipfile.ZipInfo
        for member in inner_zip.infolist():
            logger.debug(f'Un-zipping {member.filename}')
            if member.is_dir():
                logger.debug('it is a directory')
                continue
            (code_directory / Path(member.filename).relative_to(root)).parent.mkdir(parents=True, exist_ok=True)
            (code_directory / Path(member.filename).relative_to(root)).write_bytes(inner_zip.read(member))
            logger.info(f'{(code_directory / Path(member.filename).relative_to(root))} written')

    return True


def update_with_git() -> bool:
    with suppress(Exception):
        code_directory: Path = Path(__file__).parent
        if (code_directory / '.git').exists():
            return subprocess.run(args=['git', 'pull'], capture_output=True).returncode == 0
    return False


def update_from_github(user: str, repo_name: str, branch: str = 'master') -> bool:
    with suppress(Exception):
        code_directory: Path = Path(__file__).parent
        version_path: Path = code_directory / 'src' / repo_name / '_version.py'

        github_date: datetime | None = get_github_date(user=user, repo_name=repo_name)
        if github_date is None:
            logger.warning('Failed to fetch the last commit date from GitHub')
            return False
        if version_path.exists() and datetime.fromtimestamp(version_path.stat().st_mtime) >= github_date:
            logger.info('Current files are up to date')
            return False

        if upgrade_files(code_directory=code_directory, user=user, repo_name=repo_name, branch=branch):
            # if everything went fine...
            version_path.parent.mkdir(exist_ok=True, parents=True)
            version_path.write_text(f'__version__ = version = "{github_date.isoformat()}"\n')
            logger.info(f'{github_date} written into {version_path}')
            return True
    return False


def parse_table(table_text: str) -> list[dict[str, str]]:
    text_lines: list[str] = table_text.splitlines()
    rules: list[str] = [line for line in text_lines if set(line) == set('- ')]
    if len(rules) != 1:
        raise RuntimeError('Failed to parse the table')
    if text_lines.index(rules[0]) != 1:
        raise RuntimeError('Failed to parse the table')
    cols: list[int] = [len(rule) for rule in rules[0].split()]
    titles: list[str] = []
    offset: int = 0
    for col in cols:
        titles.append(text_lines[0][offset:(offset + col)].strip())
        offset += col + 1
    data: list[dict[str, str]] = []
    for line_no in range(2, len(text_lines)):
        data.append(dict())
        offset = 0
        for col, title in zip(cols, titles):
            data[-1][title] = text_lines[line_no][offset:(offset + col)].strip()
            offset += col + 1
    return data


def update_package(package_name: str) -> tuple[str, str, int | None]:
    p: subprocess.CompletedProcess = subprocess.run(
        args=[sys.executable, '-m', 'pip', 'install', '-U', package_name],
        capture_output=True, text=True)
    return p.stdout, p.stderr, p.returncode


def update_packages() -> list[str]:
    priority_packages: list[str] = ['pip', 'setuptools', 'wheel']
    out: str
    err: str
    ret: int | None
    p: subprocess.CompletedProcess = subprocess.run(
        args=[sys.executable, '-m', 'pip', 'list', '--outdated'],
        capture_output=True, text=True)
    if p.returncode:
        return []
    outdated_packages: list[str] = [item['Package'] for item in parse_table(p.stdout)]
    updated_packages: list[str] = []
    try:
        for pp in priority_packages:
            if pp in outdated_packages:
                out, err, ret = update_package(pp)
                if ret:
                    return updated_packages
                outdated_packages.remove(pp)
                updated_packages.append(pp)
        for op in outdated_packages:
            update_package(op)
            updated_packages.append(op)
    finally:
        return updated_packages


def update_with_pip(package_name: str) -> bool:
    with suppress(Exception):
        if package_name not in update_packages():
            out, err, ret = update_package(package_name)
            return not ret
    return False


if __name__ == '__main__':
    import argparse

    ap: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Fetch the code of a package from a GitHub repository')
    ap.add_argument('user', type=str, help='the owner of the GitHub repository')
    ap.add_argument('repo', type=str, help='the GitHub repository name')
    ap.add_argument('branch', type=str, help='the GitHub repository branch', default='master')

    args: argparse.Namespace = ap.parse_args()
    update_from_github(user=args.user, repo_name=args.repo, branch=args.branch)

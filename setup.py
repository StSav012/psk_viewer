# coding=utf-8
from __future__ import annotations

import site

from setuptools import setup

site.main()


def required_packages() -> list[str]:
    import sys
    if sys.version_info < (3, 8):
        raise SystemError('Python versions prior to 3.8 are not supported')

    import platform
    from typing import NamedTuple, Sequence

    from pkg_resources import parse_version

    class PackageRequirement(NamedTuple):
        package_name: str
        min_version: str = ''

        def __str__(self) -> str:
            if self.min_version:
                return self.package_name + ' >= ' + self.min_version
            return self.package_name

    def is_package_importable(package_requirement: PackageRequirement) -> bool:
        from importlib.metadata import version, PackageNotFoundError

        try:
            version(package_requirement.package_name)
        except PackageNotFoundError:
            return False
        else:
            if (package_requirement.min_version
                    and (parse_version(version(package_requirement.package_name))
                         < parse_version(package_requirement.min_version))):
                return False
        return True

    def required_package(package_requirement: PackageRequirement | Sequence[PackageRequirement]) -> PackageRequirement:
        """
        Install packages if missing

        :param package_requirement: a package name or a sequence of the names of alternative packages;
                             if none of the packages installed beforehand, install the first one given
        :returns bool: True if a package is importable, False when an attempt to install the package made
        """

        if not package_requirement:
            raise ValueError('No package requirements given')

        if not isinstance(package_requirement, PackageRequirement) and isinstance(package_requirement, Sequence):
            for _package_requirement in package_requirement:
                if is_package_importable(_package_requirement):
                    return _package_requirement
            return package_requirement[0]

        if isinstance(package_requirement, PackageRequirement):
            return package_requirement
        raise ValueError('Invalid requirements')

    qt_list: list[PackageRequirement]
    uname: platform.uname_result = platform.uname()
    if ((uname.system == 'Windows'
         and parse_version(uname.version) < parse_version('10.0.19044'))  # Windows 10 21H2 or later required
            or uname.machine not in ('x86_64', 'AMD64')):
        # Qt6 does not support the OSes
        qt_list = [
            PackageRequirement(package_name='PyQt5', min_version='5.15.10'),
        ]
    else:
        qt_list = [
            PackageRequirement(package_name='PySide6-Essentials', min_version='6.6.2'),
            PackageRequirement(package_name='PyQt6', min_version='6.6.2'),
            PackageRequirement(package_name='PyQt5', min_version='5.15.10'),
        ]
    if sys.version_info < (3, 11):
        qt_list.append(PackageRequirement(package_name='PySide2', min_version='5.13.2'))

    requirements: list[PackageRequirement | Sequence[PackageRequirement]] = [
        PackageRequirement(package_name='qtpy', min_version='2.4.1'),
        PackageRequirement(package_name='qtawesome'),
        qt_list,
        PackageRequirement(package_name='pandas'),
        PackageRequirement(package_name='pyqtgraph', min_version='0.13.3'),
        PackageRequirement(package_name='scipy'),
    ]
    return [str(required_package(requirement)) for requirement in requirements]


setup(install_requires=required_packages())

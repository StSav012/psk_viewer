import mimetypes
from collections.abc import Collection
from importlib.util import find_spec
from os import PathLike
from pathlib import Path
from typing import NamedTuple

from qtpy.QtWidgets import QFileDialog, QWidget

from .settings import Settings

__all__ = ["OpenFileDialog", "SaveFileDialog"]


class FileDialog(QFileDialog):
    class SupportedMimetypeItem(NamedTuple):
        required_packages: Collection[str]
        file_extension: str

    class SupportedNameFilterItem(NamedTuple):
        required_packages: Collection[str]
        name: str
        file_extensions: Collection[str]

    def __init__(
        self,
        settings: Settings,
        supported_mimetype_filters: Collection[SupportedMimetypeItem] = (),
        supported_name_filters: Collection[SupportedNameFilterItem] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)

        self.settings: Settings = settings
        self.supported_mimetype_filters: Collection[
            FileDialog.SupportedMimetypeItem
        ] = tuple(supported_mimetype_filters)
        self.supported_name_filters: Collection[FileDialog.SupportedNameFilterItem] = (
            tuple(supported_name_filters)
        )

    def selectFile(self, filename: str | PathLike[str]) -> None:
        return super().selectFile(str(filename))

    def selectedFile(self) -> Path | None:
        try:
            return Path(self.selectedFiles()[0])
        except IndexError:
            return None


class OpenFileDialog(FileDialog):
    def __init__(
        self,
        settings: Settings,
        supported_mimetype_filters: Collection[FileDialog.SupportedMimetypeItem] = (),
        supported_name_filters: Collection[FileDialog.SupportedNameFilterItem] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            settings, supported_mimetype_filters, supported_name_filters, parent
        )

        self.setObjectName("openFileDialog")

    def _fill_filters(self) -> None:
        mimetypes.init()

        _space_before_extensions: str = " " * (
            not self.testOption(QFileDialog.Option.HideNameFilterDetails)
        )

        supported_name_filters_names: list[str] = []
        supported_name_filters: list[OpenFileDialog.SupportedNameFilterItem] = []
        for supported_name_filter in self.supported_name_filters:
            if not supported_name_filter.required_packages or any(
                find_spec(package)
                for package in supported_name_filter.required_packages
            ):
                supported_name_filters_names.append(
                    "".join(
                        (
                            supported_name_filter.name,
                            _space_before_extensions,
                            "(",
                            " ".join(
                                "*" + ext
                                for ext in supported_name_filter.file_extensions
                            ),
                            ")",
                        )
                    )
                )
                supported_name_filters.append(supported_name_filter)

        supported_mimetypes: list[str] = []
        mimetype: str | None
        for supported_mimetype_filter in self.supported_mimetype_filters:
            if (
                not supported_mimetype_filter.required_packages
                or any(
                    find_spec(package)
                    for package in supported_mimetype_filter.required_packages
                )
            ) and (
                mimetype := mimetypes.types_map.get(
                    supported_mimetype_filter.file_extension
                )
            ):
                supported_mimetypes.append(mimetype)
        # for the “All files (*)” filter
        supported_mimetypes.append("application/octet-stream")

        self.setMimeTypeFilters(supported_mimetypes)
        all_extensions: list[str] = [
            "*" + ext
            for t in supported_mimetypes[:-1]
            for ext in mimetypes.guess_all_extensions(t, strict=False)
        ] + ["*" + ext for t in supported_name_filters for ext in t.file_extensions]
        name_filters: list[str] = supported_name_filters_names + self.nameFilters()
        all_extensions_unique: frozenset[str] = frozenset(all_extensions)
        if len(all_extensions_unique) > 1:
            name_filters.insert(
                0,
                "".join(
                    (
                        self.tr("All supported"),
                        _space_before_extensions,
                        "(",
                        " ".join(all_extensions_unique),
                        ")",
                    )
                ),
            )
            self.setDefaultSuffix(all_extensions[0])
        self.setNameFilters(name_filters)

    def get_open_filename(self) -> Path | None:
        self._fill_filters()

        opened_filename: Path | None
        if opened_filename := self.settings.opened_file_name:
            self.selectFile(opened_filename)
            self.setDirectory(str(opened_filename.parent))

        self.settings.restore(self)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        if self.exec() and (file_path := self.selectedFile()):
            self.settings.save(self)
            self.settings.opened_file_name = file_path
            return file_path
        return None

    def get_open_filenames(self) -> list[str | PathLike[str]]:
        self._fill_filters()

        opened_filename: Path | None
        if opened_filename := self.settings.opened_file_name:
            self.selectFile(opened_filename)
            self.setDirectory(str(opened_filename.parent))

        self.settings.restore(self)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)
        if self.exec() and (file_paths := self.selectedFiles()):
            self.settings.save(self)
            self.settings.opened_file_name = file_paths[-1]
            return file_paths
        return []


class SaveFileDialog(FileDialog):
    def __init__(
        self,
        settings: Settings,
        supported_mimetype_filters: Collection[FileDialog.SupportedMimetypeItem] = (),
        supported_name_filters: Collection[FileDialog.SupportedNameFilterItem] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            settings, supported_mimetype_filters, supported_name_filters, parent
        )

        self.setObjectName("saveFileDialog")

    def get_save_filename(self) -> Path | None:
        mimetypes.init()

        _space_before_extensions: str = " " * (
            not self.testOption(QFileDialog.Option.HideNameFilterDetails)
        )

        filename: Path | None = self.settings.saved_file_name
        opened_filename: Path | None = self.settings.opened_file_name

        filename_mimetype: str | None = (
            mimetypes.guess_type(filename, strict=False)[0]
            if filename is not None
            else None
        )
        filename_suffixes: str = (
            "".join(filename.suffixes) if filename is not None else ""
        )

        selected_mimetype: str | None = None
        selected_filter: str | None = None
        selected_ext: str = filename.suffix if filename is not None else ""

        ext: str | None

        supported_name_filters: list[str] = []
        for supported_name_filter in self.supported_name_filters:
            if not supported_name_filter.required_packages or any(
                find_spec(package)
                for package in supported_name_filter.required_packages
            ):
                filter_: str = "".join(
                    (
                        supported_name_filter.name,
                        _space_before_extensions,
                        "(",
                        " ".join(
                            "*" + ext for ext in supported_name_filter.file_extensions
                        ),
                        ")",
                    )
                )
                supported_name_filters.append(filter_)
                if any(
                    filename_suffixes.endswith(ext)
                    for ext in supported_name_filter.file_extensions
                ):
                    selected_filter = filter_
                    if supported_name_filter.file_extensions:
                        selected_ext = list(supported_name_filter.file_extensions)[0]

        supported_mimetypes: list[str] = []
        mimetype: str | None
        for supported_mimetype_filter in self.supported_mimetype_filters:
            if (
                not supported_mimetype_filter.required_packages
                or any(
                    find_spec(package)
                    for package in supported_mimetype_filter.required_packages
                )
            ) and (
                mimetype := mimetypes.types_map.get(
                    supported_mimetype_filter.file_extension
                )
            ):
                supported_mimetypes.append(mimetype)
                if filename_mimetype is not None and filename_mimetype == mimetype:
                    selected_mimetype = mimetype
                    if ext := mimetypes.guess_extension(
                        selected_mimetype, strict=False
                    ):
                        selected_ext = ext

        if not supported_name_filters and not supported_mimetypes:
            return None

        self.setMimeTypeFilters(supported_mimetypes)
        if supported_name_filters:
            self.setNameFilters(supported_name_filters + self.nameFilters())
        self.setOption(QFileDialog.Option.DontConfirmOverwrite, False)
        if selected_filter is not None:
            self.selectNameFilter(selected_filter)
        elif selected_mimetype is not None:
            self.selectMimeTypeFilter(selected_mimetype)

        self.settings.restore(self)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        if selected_ext:
            self.setDefaultSuffix(selected_ext)

        expected_file: Path
        if expected_file := (filename or opened_filename):
            self.setDirectory(str(expected_file.parent))
            if opened_filename:
                expected_file = expected_file.with_name(opened_filename.name)
            if selected_ext:
                expected_file = expected_file.with_suffix(selected_ext)
            self.selectFile(str(expected_file))

        if self.exec() and self.selectedFiles():
            self.settings.save(self)
            if not (filename := self.selectedFile()):
                return None
            self.settings.saved_file_name = filename
            return filename
        return None

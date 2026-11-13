"""Read and write GEDZIP archives: a dataset and the local files it names."""

from __future__ import annotations

import os
import re
import shutil
import zipfile
from typing import IO, TYPE_CHECKING, BinaryIO, Union, cast
from urllib.parse import quote, unquote

from . import const, grammar
from .exceptions import GedcomParseError, GedcomSerializeError
from .parser import load
from .serializer import dumps

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping
    from types import TracebackType

    from .types import GedcomStructure

DATASET = "gedcom.ged"

FILE_PATH = "https://gedcom.io/terms/v7/type-FilePath"

# What a local file's content can be given as: its bytes, a path to read it
# from, or a function opening it.
FileSource = Union[bytes, str, "os.PathLike[str]", "Callable[[], IO[bytes]]"]

_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_BANNED = re.compile(grammar.banned)
# Characters a file path payload carries literally; anything else is escaped.
_SAFE = "/!$&'()*+,;=@-._~"
# A valid URL string: URL code points and percent escapes, no query or fragment.
_URL_PATH = re.compile(
    r"(?:[A-Za-z0-9!$&'()*+,\-./:;=@_~]|%[0-9A-Fa-f]{2}|[^\x00-\x7f])*"
)


def is_local_file(path: str) -> bool:
    """Say whether a file path payload names a local file, not a URL."""
    if not path or _SCHEME.match(path) or "?" in path or "#" in path:
        return False
    try:
        name = unquote(path, errors="strict")
    except UnicodeDecodeError:
        return False
    if name.startswith("/") or "\\" in name or _BANNED.search(name):
        return False
    return ".." not in name.split("/")


def entry_name(path: str) -> str:
    """Get the archive entry a local file path payload names."""
    if not is_local_file(path):
        raise ValueError(f"{path!r} is not a local file path")
    return unquote(path, errors="strict")


def file_path(name: str) -> str:
    """Get the file path payload naming an archive entry."""
    path = quote(name, safe=_SAFE)
    if not is_local_file(path):
        raise ValueError(f"{name!r} cannot be a local file in a GEDZIP")
    return path


def file_structures(
    records: Iterable[GedcomStructure],
) -> Iterator[GedcomStructure]:
    """Yield every structure whose payload is a file path."""
    stack = list(reversed(list(records)))
    while stack:
        structure = stack.pop()
        type_id = structure.type_id
        if type_id is not None and const.payloads.get(type_id) == FILE_PATH:
            yield structure
        stack.extend(reversed(structure.children))


def local_files(records: Iterable[GedcomStructure]) -> list[str]:
    """List the local file paths a dataset names, each once, in order."""
    paths = (s.text for s in file_structures(records))
    return list(dict.fromkeys(p for p in paths if is_local_file(p)))


class GedzipReader:
    """A GEDZIP archive opened for reading.

    ::

        with gedcom7.GedzipReader("family.gdz") as archive:
            records = archive.records
            with archive.open("media/photo.jpg") as f:
                data = f.read()
    """

    def __init__(self, file: str | os.PathLike[str] | IO[bytes]) -> None:
        """Open the archive and load its dataset."""
        try:
            self._zip = zipfile.ZipFile(file)
        except zipfile.BadZipFile as exc:
            raise GedcomParseError(f"not a GEDZIP archive: {exc}") from exc
        try:
            with self._zip.open(DATASET) as fp:
                self.records: list[GedcomStructure] = load(cast(BinaryIO, fp))
        except KeyError:
            self._zip.close()
            raise GedcomParseError(f"GEDZIP archive has no {DATASET}") from None
        except BaseException:
            self._zip.close()
            raise

    def has(self, path: str) -> bool:
        """Say whether the archive holds the local file a payload names."""
        try:
            self._zip.getinfo(entry_name(path))
        except (KeyError, ValueError):
            return False
        return True

    def open(self, path: str) -> IO[bytes]:
        """Open the local file a payload names.

        Raises :class:`KeyError` if the archive does not hold it.
        """
        return self._zip.open(entry_name(path))

    def missing(self) -> list[str]:
        """List the local file paths the dataset names but the archive lacks."""
        return [p for p in local_files(self.records) if not self.has(p)]

    def close(self) -> None:
        """Close the archive."""
        self._zip.close()

    def __enter__(self) -> GedzipReader:
        """Enter a ``with`` block."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the archive on leaving a ``with`` block."""
        self.close()


def _check_paths(
    records: list[GedcomStructure], files: Mapping[str, FileSource | None]
) -> None:
    for structure in file_structures(records):
        path = structure.text
        if is_local_file(path):
            if path not in files:
                raise GedcomSerializeError(f"no content given for local file {path}")
        elif path.lower().startswith("file:"):
            raise GedcomSerializeError(f"a GEDZIP cannot point at file URL {path}")
    names: dict[str, str] = {}
    for path, source in files.items():
        if not is_local_file(path) or not _URL_PATH.fullmatch(path):
            raise GedcomSerializeError(f"{path!r} is not a valid local file path")
        name = entry_name(path)
        if name == DATASET:
            raise GedcomSerializeError(f"a local file cannot be named {DATASET}")
        if source is not None:
            if name in names:
                raise GedcomSerializeError(
                    f"{names[name]} and {path} name the same file {name}"
                )
            names[name] = path


def _write_file(archive: zipfile.ZipFile, name: str, source: FileSource) -> None:
    if isinstance(source, bytes):
        archive.writestr(name, source)
    elif isinstance(source, (str, os.PathLike)):
        archive.write(source, name)
    else:
        with source() as src, archive.open(name, "w", force_zip64=True) as dst:
            shutil.copyfileobj(src, dst)


def dump_gedzip(
    records: Iterable[GedcomStructure],
    file: str | os.PathLike[str] | BinaryIO,
    files: Mapping[str, FileSource | None],
    *,
    compress_files: bool = False,
    line_terminator: str = "\n",
    byte_order_mark: bool = True,
    validate: bool = False,
) -> None:
    """Write a dataset and its local files as a GEDZIP archive.

    ``files`` maps each local file path payload in the dataset to its content,
    or to None to leave a file that is unavailable out.
    The dataset is compressed; the files only with ``compress_files=True``, as
    most media is compressed already.

    Raises :class:`~gedcom7.exceptions.GedcomSerializeError` if a local file has
    no content, is named ``gedcom.ged``, is not a valid URL string, or shares its
    name with another, or if a payload is a ``file:`` URL.
    """
    records = list(records)
    _check_paths(records, files)
    data = dumps(
        records,
        line_terminator=line_terminator,
        byte_order_mark=byte_order_mark,
        validate=validate,
    ).encode("utf-8")
    method = zipfile.ZIP_DEFLATED if compress_files else zipfile.ZIP_STORED
    with zipfile.ZipFile(file, "w", compression=method) as archive:
        archive.writestr(DATASET, data, compress_type=zipfile.ZIP_DEFLATED)
        for path, source in files.items():
            if source is not None:
                _write_file(archive, entry_name(path), source)

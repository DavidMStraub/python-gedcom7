"""Tests for reading and writing GEDZIP archives."""

import io
import pathlib
import zipfile

import pytest

import gedcom7
from gedcom7 import GedcomParseError, GedcomSerializeError, gedzip, types


def dataset(*paths: str) -> list[types.GedcomStructure]:
    head = types.GedcomStructure(tag="HEAD")
    gedc = types.GedcomStructure(tag="GEDC")
    head.append_child(gedc)
    gedc.append_child(types.GedcomStructure(tag="VERS", text="7.0"))
    records = [head]
    for number, path in enumerate(paths, start=1):
        obje = types.GedcomStructure(tag="OBJE", xref=f"@O{number}@")
        file = types.GedcomStructure(tag="FILE", text=path)
        file.append_child(types.GedcomStructure(tag="FORM", text="image/jpeg"))
        obje.append_child(file)
        records.append(obje)
    records.append(types.GedcomStructure(tag="TRLR"))
    return records


@pytest.mark.parametrize(
    "path",
    ["photo.jpg", "media/photo.jpg", "media/a%20b.jpg", "média/ü.jpg"],
)
def test_local_file(path: str) -> None:
    assert gedzip.is_local_file(path)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "https://example.com/a.jpg",
        "file:///home/a.jpg",
        "/abs/a.jpg",
        "../a.jpg",
        "media/%2E%2E/a.jpg",
        "media\\a.jpg",
        "media/a%5Cb.jpg",
        "a.jpg?x=1",
        "a.jpg#frag",
        "media//a.jpg",
        "a%01.jpg",
    ],
)
def test_not_local_file(path: str) -> None:
    assert not gedzip.is_local_file(path)


@pytest.mark.parametrize(
    "name", ["media/a b.jpg", "media/50%.jpg", "c:d.jpg", "a#b?.jpg", "ü.jpg"]
)
def test_file_path_round_trip(name: str) -> None:
    path = gedzip.file_path(name)
    assert gedzip.is_local_file(path)
    assert gedzip.entry_name(path) == name


@pytest.mark.parametrize("name", ["../a.jpg", "/a.jpg", "a\\b.jpg", ""])
def test_file_path_rejects(name: str) -> None:
    with pytest.raises(ValueError):
        gedzip.file_path(name)


def test_round_trip(tmp_path: pathlib.Path) -> None:
    on_disk = tmp_path / "c.jpg"
    on_disk.write_bytes(b"from disk")
    records = dataset("media/a%20b.jpg", "b.jpg", "c.jpg", "https://example.com/d.jpg")
    target = tmp_path / "family.gdz"
    gedcom7.dump_gedzip(
        records,
        target,
        {
            "media/a%20b.jpg": b"bytes",
            "b.jpg": lambda: io.BytesIO(b"opened"),
            "c.jpg": on_disk,
        },
    )
    with zipfile.ZipFile(target) as archive:
        assert sorted(archive.namelist()) == [
            "b.jpg",
            "c.jpg",
            "gedcom.ged",
            "media/a b.jpg",
        ]
        assert archive.getinfo("gedcom.ged").compress_type == zipfile.ZIP_DEFLATED
        assert archive.getinfo("b.jpg").compress_type == zipfile.ZIP_STORED
    with gedcom7.GedzipReader(target) as archive:
        assert archive.records == records
        assert archive.missing() == []
        with archive.open("media/a%20b.jpg") as f:
            assert f.read() == b"bytes"
        with archive.open("b.jpg") as f:
            assert f.read() == b"opened"
        with archive.open("c.jpg") as f:
            assert f.read() == b"from disk"
        assert not archive.has("https://example.com/d.jpg")


def test_local_files_include_translations() -> None:
    records = dataset("a.jpg", "a.jpg")
    tran = types.GedcomStructure(tag="TRAN", text="b.jpg")
    tran.append_child(types.GedcomStructure(tag="FORM", text="image/jpeg"))
    records[1].children[0].append_child(tran)
    assert gedzip.local_files(records) == ["a.jpg", "b.jpg"]


def test_reader_reports_missing() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("gedcom.ged", gedcom7.dumps(dataset("a.jpg", "b.jpg")))
        archive.writestr("a.jpg", b"")
    with gedcom7.GedzipReader(buffer) as reader:
        assert reader.missing() == ["b.jpg"]
        with pytest.raises(KeyError):
            reader.open("b.jpg")


def test_reader_needs_dataset() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("other.ged", b"")
    with pytest.raises(GedcomParseError, match="gedcom.ged"):
        gedcom7.GedzipReader(buffer)


def test_reader_needs_zip() -> None:
    with pytest.raises(GedcomParseError, match="not a GEDZIP"):
        gedcom7.GedzipReader(io.BytesIO(b"0 HEAD\n"))


def test_writer_needs_every_local_file() -> None:
    with pytest.raises(GedcomSerializeError, match="b.jpg"):
        gedcom7.dump_gedzip(dataset("a.jpg", "b.jpg"), io.BytesIO(), {"a.jpg": b""})


def test_writer_rejects_dataset_name() -> None:
    with pytest.raises(GedcomSerializeError, match="gedcom.ged"):
        gedcom7.dump_gedzip(dataset("gedcom.ged"), io.BytesIO(), {"gedcom.ged": b""})


def test_writer_rejects_file_url() -> None:
    with pytest.raises(GedcomSerializeError, match="file URL"):
        gedcom7.dump_gedzip(dataset("file:///home/a.jpg"), io.BytesIO(), {})


def test_writer_leaves_out_unavailable_file() -> None:
    buffer = io.BytesIO()
    gedcom7.dump_gedzip(
        dataset("a.jpg", "b.jpg"), buffer, {"a.jpg": b"", "b.jpg": None}
    )
    with gedcom7.GedzipReader(buffer) as reader:
        assert reader.missing() == ["b.jpg"]

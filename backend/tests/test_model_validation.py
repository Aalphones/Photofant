"""Validation pipeline tests — one case per §12.2a error class (Phase 3 core risk).

The §12.2a hash-mismatch class applies to *managed* downloads (covered by the
download job in Phase 2); in-place binding treats the hash as informative, so it
is not a gate here.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Base, ModelRegistry
from photofant.db.session import get_session
from photofant.main import create_app
from photofant.models import validation
from photofant.models.loader import ManifestEntry
from photofant.models.validation import (
    ModelErrorCode,
    ModelFileFormat,
    ModelValidationError,
    detect_format,
    validate_in_place,
)

# Bytes whose first tag (0x08) looks like an ONNX ModelProto ir_version field.
_FAKE_ONNX = bytes([0x08, 0x07]) + b"\x00" * 64


def _single_file_entry() -> ManifestEntry:
    """rembg: a single .onnx weight file."""
    return ManifestEntry({
        "id": "rembg-u2net",
        "role": "rembg",
        "name": "rembg u2net",
        "format": "onnx",
        "tier": "core",
        "files": [{"filename": "u2net.onnx"}],
    })


def _folder_entry() -> ManifestEntry:
    """WD14: a folder holding model.onnx + selected_tags.csv."""
    return ManifestEntry({
        "id": "wd-swinv2-v3",
        "role": "tagger",
        "name": "WD14 SwinV2 Tagger V3",
        "format": "onnx",
        "tier": "core",
        "files": [
            {"filename": "model.onnx"},
            {"filename": "selected_tags.csv"},
        ],
    })


def _write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class _FakeOnnxSession:
    """Stand-in for an onnxruntime InferenceSession with controllable inputs."""

    def __init__(self, input_ranks: list[int]) -> None:
        self._inputs = [type("Input", (), {"shape": [None] * rank})() for rank in input_ranks]

    def get_inputs(self) -> list[Any]:
        return self._inputs


# ── format detection ─────────────────────────────────────────────────────────


def test_detect_format_recognizes_gguf_and_safetensors(tmp_path: Path) -> None:
    gguf = _write(tmp_path / "m.gguf", b"GGUF\x03\x00\x00\x00rest")
    safet = _write(tmp_path / "m.safetensors", (16).to_bytes(8, "little") + b'{"a":1}\x00\x00')
    onnx = _write(tmp_path / "m.onnx", _FAKE_ONNX)

    assert detect_format(gguf) == ModelFileFormat.GGUF
    assert detect_format(safet) == ModelFileFormat.SAFETENSORS
    assert detect_format(onnx) == ModelFileFormat.ONNX


# ── one case per §12.2a error class ──────────────────────────────────────────


def test_not_found_when_path_missing(tmp_path: Path) -> None:
    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_single_file_entry(), str(tmp_path / "nope.onnx"))
    assert raised.value.code == ModelErrorCode.NOT_FOUND


def test_wrong_format_when_gguf_in_onnx_slot(tmp_path: Path) -> None:
    bad = _write(tmp_path / "u2net.onnx", b"GGUF\x03\x00\x00\x00rest")
    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_single_file_entry(), str(bad))
    assert raised.value.code == ModelErrorCode.WRONG_FORMAT


def test_wrong_format_when_folder_given_for_single_file(tmp_path: Path) -> None:
    folder = tmp_path / "a_dir"
    folder.mkdir()
    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_single_file_entry(), str(folder))
    assert raised.value.code == ModelErrorCode.WRONG_FORMAT


def test_wrong_role_when_input_not_image_shaped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    weights = _write(tmp_path / "u2net.onnx", _FAKE_ONNX)
    # rembg expects an image (4-D) input; a 2-D-input model contradicts the role.
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: _FakeOnnxSession([2]))

    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_single_file_entry(), str(weights))
    assert raised.value.code == ModelErrorCode.WRONG_ROLE


def test_incomplete_when_companion_csv_missing(tmp_path: Path) -> None:
    folder = tmp_path / "wd14"
    _write(folder / "model.onnx", _FAKE_ONNX)  # selected_tags.csv deliberately absent

    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_folder_entry(), str(folder))
    assert raised.value.code == ModelErrorCode.INCOMPLETE


def test_load_failed_when_not_valid_onnx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Extension says .onnx, but the bytes are neither gguf/safetensors nor a
    # protobuf header. Force the no-runtime path so the result is deterministic.
    garbage = _write(tmp_path / "u2net.onnx", b"XXXXnot-a-model")
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_single_file_entry(), str(garbage))
    assert raised.value.code == ModelErrorCode.LOAD_FAILED


# ── happy paths ──────────────────────────────────────────────────────────────


def test_valid_single_file_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    weights = _write(tmp_path / "u2net.onnx", _FAKE_ONNX)
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    result = validate_in_place(_single_file_entry(), str(weights))

    assert result.primary_path == weights
    assert len(result.sha256) == 64
    assert result.detected_format == ModelFileFormat.ONNX


def test_valid_folder_with_companions_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "wd14"
    _write(folder / "model.onnx", _FAKE_ONNX)
    _write(folder / "selected_tags.csv", b"tag_id,name\n0,cat\n")
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    result = validate_in_place(_folder_entry(), str(folder))

    assert result.primary_path == folder / "model.onnx"


# ── endpoint guarantees (transactional + in-place delete leaves file) ─────────


@pytest.fixture
def app_with_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[Any, Session], None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    app = create_app()

    def _override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = _override
    try:
        yield app, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_register_local_failed_validation_writes_nothing(
    app_with_db: tuple[Any, Session], tmp_path: Path,
) -> None:
    app, session = app_with_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/models/register-local",
            json={"manifest_id": "rembg-u2net", "path": str(tmp_path / "does-not-exist.onnx")},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == ModelErrorCode.NOT_FOUND
    assert session.query(ModelRegistry).count() == 0


@pytest.mark.asyncio
async def test_delete_in_place_leaves_file_untouched(
    app_with_db: tuple[Any, Session], tmp_path: Path,
) -> None:
    app, session = app_with_db
    weights = _write(tmp_path / "u2net.onnx", _FAKE_ONNX)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register = await client.post(
            "/api/models/register-local",
            json={"manifest_id": "rembg-u2net", "path": str(weights)},
        )
        assert register.status_code == 200
        assert register.json()["status"] == "inplace"

        delete = await client.delete("/api/models/rembg-u2net")

    assert delete.status_code == 200
    assert delete.json() == {"deleted": True, "file_removed": False}
    assert weights.exists()  # in-place file must survive removal
    assert session.query(ModelRegistry).count() == 0

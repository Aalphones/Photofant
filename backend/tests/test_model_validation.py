"""Validation pipeline tests — one case per §12.2a error class (Phase 3 core risk).

The §12.2a hash-mismatch class applies to *managed* downloads (covered by the
download job in Phase 2); in-place binding treats the hash as informative, so it
is not a gate here.

Phase 9.2: Component-model validation (completeness gate, family mismatch warning).
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
    validate_component_model,
    validate_in_place,
)

_FAKE_ONNX = bytes([0x08, 0x07]) + b"\x00" * 64
_FAKE_SAFETENSORS = (16).to_bytes(8, "little") + b'{"a":1}\x00\x00\x00\x00\x00\x00\x00\x00'


def _onnx_folder_entry() -> ManifestEntry:
    """rembg: an ONNX folder model (plain 'onnx' format always resolves to FOLDER layout)."""
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


def _component_entry() -> ManifestEntry:
    """Flux: a component model with transformer, text_encoder, vae."""
    return ManifestEntry({
        "id": "flux2-klein-9b",
        "role": "editor",
        "name": "FLUX.2 klein 9B",
        "format": "safetensors",
        "tier": "generativ",
        "files": [],
        "capabilities": {
            "component_model": True,
            "components": {
                "transformer": {"label": "Diffusion-Modell", "required": True, "formats": ["safetensors", "gguf"]},
                "text_encoder": {"label": "Text-Encoder", "required": True, "formats": ["safetensors", "gguf"]},
                "vae": {"label": "VAE", "required": True, "formats": ["safetensors"]},
            },
            "expected_families": {
                "text_encoder": "t5",
                "vae": "flux-ae",
            },
            "variants": [
                {"name": "bf16", "size_gb": 18.2, "vram_gb": 29},
                {"name": "fp8", "size_gb": 9, "vram_gb": 24},
            ],
        },
    })


def _write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class _FakeOnnxSession:
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
        validate_in_place(_onnx_folder_entry(), str(tmp_path / "nope"))
    assert raised.value.code == ModelErrorCode.NOT_FOUND


def test_wrong_format_when_gguf_in_onnx_slot(tmp_path: Path) -> None:
    folder = tmp_path / "rembg"
    _write(folder / "u2net.onnx", b"GGUF\x03\x00\x00\x00rest")
    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_onnx_folder_entry(), str(folder))
    assert raised.value.code == ModelErrorCode.WRONG_FORMAT


def test_wrong_format_when_file_given_for_folder_model(tmp_path: Path) -> None:
    bare_file = _write(tmp_path / "u2net.onnx", _FAKE_ONNX)
    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_onnx_folder_entry(), str(bare_file))
    assert raised.value.code == ModelErrorCode.WRONG_FORMAT


def test_wrong_role_when_input_not_image_shaped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "rembg"
    _write(folder / "u2net.onnx", _FAKE_ONNX)
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: _FakeOnnxSession([2]))

    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_onnx_folder_entry(), str(folder))
    assert raised.value.code == ModelErrorCode.WRONG_ROLE


def test_incomplete_when_companion_csv_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "wd14"
    _write(folder / "model.onnx", _FAKE_ONNX)
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_folder_entry(), str(folder))
    assert raised.value.code == ModelErrorCode.INCOMPLETE


def test_load_failed_when_not_valid_onnx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "rembg"
    _write(folder / "u2net.onnx", b"XXXXnot-a-model")
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    with pytest.raises(ModelValidationError) as raised:
        validate_in_place(_onnx_folder_entry(), str(folder))
    assert raised.value.code == ModelErrorCode.LOAD_FAILED


# ── happy paths ──────────────────────────────────────────────────────────────


def test_valid_onnx_folder_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "rembg"
    _write(folder / "u2net.onnx", _FAKE_ONNX)
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    result = validate_in_place(_onnx_folder_entry(), str(folder))

    assert result.primary_path == folder / "u2net.onnx"
    assert len(result.sha256) == 64
    assert result.detected_format == ModelFileFormat.ONNX


def test_valid_folder_with_companions_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "wd14"
    _write(folder / "model.onnx", _FAKE_ONNX)
    _write(folder / "selected_tags.csv", b"tag_id,name\n0,cat\n")
    monkeypatch.setattr(validation, "_open_onnx_session", lambda path: None)

    result = validate_in_place(_folder_entry(), str(folder))

    assert result.primary_path == folder / "model.onnx"


# ── component model validation (P9 Phase 2) ─────────────────────────────────


def test_component_completeness_gate_rejects_missing_parts(tmp_path: Path) -> None:
    transformer_dir = tmp_path / "transformer"
    _write(transformer_dir / "model.safetensors", _FAKE_SAFETENSORS)

    with pytest.raises(ModelValidationError) as raised:
        validate_component_model(_component_entry(), {
            "transformer": str(transformer_dir),
        })
    assert raised.value.code == ModelErrorCode.INCOMPLETE
    assert "Text-Encoder" in raised.value.expected
    assert "VAE" in raised.value.expected


def test_component_completeness_gate_rejects_empty_paths(tmp_path: Path) -> None:
    transformer_dir = tmp_path / "transformer"
    _write(transformer_dir / "model.safetensors", _FAKE_SAFETENSORS)

    with pytest.raises(ModelValidationError) as raised:
        validate_component_model(_component_entry(), {
            "transformer": str(transformer_dir),
            "text_encoder": "",
            "vae": "  ",
        })
    assert raised.value.code == ModelErrorCode.INCOMPLETE


def test_component_validation_detects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ModelValidationError) as raised:
        validate_component_model(_component_entry(), {
            "transformer": str(tmp_path / "nonexistent"),
            "text_encoder": str(tmp_path / "nonexistent2"),
            "vae": str(tmp_path / "nonexistent3"),
        })
    assert raised.value.code == ModelErrorCode.NOT_FOUND


def test_component_validation_passes_with_all_parts(tmp_path: Path) -> None:
    for name in ("transformer", "text_encoder", "vae"):
        _write(tmp_path / name / "model.safetensors", _FAKE_SAFETENSORS)

    result = validate_component_model(_component_entry(), {
        "transformer": str(tmp_path / "transformer"),
        "text_encoder": str(tmp_path / "text_encoder"),
        "vae": str(tmp_path / "vae"),
    })
    assert len(result.component_hashes) == 3
    assert all(len(sha) == 64 for sha in result.component_hashes.values())


def test_component_family_mismatch_produces_warning(tmp_path: Path) -> None:
    for name in ("transformer", "vae"):
        _write(tmp_path / name / "model.safetensors", _FAKE_SAFETENSORS)

    # text_encoder in a folder named "clip" — Flux expects "t5"
    clip_dir = tmp_path / "clip-encoder"
    _write(clip_dir / "model.safetensors", _FAKE_SAFETENSORS)

    result = validate_component_model(_component_entry(), {
        "transformer": str(tmp_path / "transformer"),
        "text_encoder": str(clip_dir),
        "vae": str(tmp_path / "vae"),
    })
    assert len(result.warnings) >= 1
    assert "clip" in result.warnings[0].lower()


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
            json={"manifest_id": "rembg-u2net", "path": str(tmp_path / "does-not-exist")},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == ModelErrorCode.NOT_FOUND
    assert session.query(ModelRegistry).count() == 0


@pytest.mark.asyncio
async def test_delete_in_place_leaves_file_untouched(
    app_with_db: tuple[Any, Session], tmp_path: Path,
) -> None:
    app, session = app_with_db
    folder = tmp_path / "rembg"
    _write(folder / "u2net.onnx", _FAKE_ONNX)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register = await client.post(
            "/api/models/register-local",
            json={"manifest_id": "rembg-u2net", "path": str(folder)},
        )
        assert register.status_code == 200
        body = register.json()
        assert body["model"]["status"] == "inplace"

        delete = await client.delete("/api/models/rembg-u2net")

    assert delete.status_code == 200
    assert delete.json() == {"deleted": True, "file_removed": False}
    assert folder.exists()
    assert session.query(ModelRegistry).count() == 0

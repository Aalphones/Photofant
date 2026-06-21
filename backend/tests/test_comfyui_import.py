"""Tests for Phase 5 — ComfyUI results listing and import.

Covers:
- GET /api/comfyui/results: history path, output_dir path, dedup
- POST /api/comfyui/results/import: creates version with type=comfyui + correct params
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from photofant.db.models import Asset, AssetInstance, Base, Person, Version

# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture()
def db(tmp_path: Path) -> Session:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(Person(id=1, name="Max", is_unknown=False))
    session.flush()
    asset = Asset(
        id=1,
        content_hash="abc123",
        source="test",
        width=100,
        height=100,
        file_size=1000,
    )
    session.add(asset)
    session.flush()
    session.add(AssetInstance(id=1, asset_id=1, person_id=1, path="/data/img.jpg"))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_app(db_session: Session):  # type: ignore[no-untyped-def]
    """Build a minimal FastAPI app with the comfyui_router mounted."""
    from fastapi import FastAPI

    from photofant.api.comfyui import comfyui_router
    from photofant.db.session import get_session

    app = FastAPI()
    # comfyui_router already has prefix="/comfyui"; mount at "/api" like main.py
    app.include_router(comfyui_router, prefix="/api")
    app.dependency_overrides[get_session] = lambda: db_session
    return app


# ── _extract_history_items ─────────────────────────────────────────────────────

class TestExtractHistoryItems:
    def test_extracts_images_from_history(self) -> None:
        from photofant.api.comfyui import _extract_history_items

        history = {
            "abc-prompt": {
                "outputs": {
                    "4": {
                        "images": [
                            {"filename": "output_001.png", "subfolder": "photofant", "type": "output"},
                            {"filename": "output_002.png", "subfolder": "", "type": "output"},
                        ]
                    }
                }
            }
        }
        items = _extract_history_items(history)
        assert len(items) == 2
        assert items[0].filename == "output_001.png"
        assert items[0].subfolder == "photofant"
        assert items[0].source == "history"
        assert "output_001.png" in items[0].preview_url

    def test_empty_history_gives_empty_list(self) -> None:
        from photofant.api.comfyui import _extract_history_items

        assert _extract_history_items({}) == []

    def test_skips_entries_without_filename(self) -> None:
        from photofant.api.comfyui import _extract_history_items

        history = {
            "pid": {
                "outputs": {
                    "4": {"images": [{"filename": "", "subfolder": ""}]}
                }
            }
        }
        assert _extract_history_items(history) == []


# ── _scan_output_dir ──────────────────────────────────────────────────────────

class TestScanOutputDir:
    def test_lists_images_in_dir(self, tmp_path: Path) -> None:
        from photofant.api.comfyui import _scan_output_dir

        (tmp_path / "a.png").write_bytes(b"\x89PNG")
        (tmp_path / "b.jpg").write_bytes(b"\xff\xd8")
        (tmp_path / "notes.txt").write_bytes(b"text")

        items = _scan_output_dir(str(tmp_path))
        filenames = {item.filename for item in items}
        assert "a.png" in filenames
        assert "b.jpg" in filenames
        assert "notes.txt" not in filenames

    def test_empty_string_returns_empty(self) -> None:
        from photofant.api.comfyui import _scan_output_dir

        assert _scan_output_dir("") == []

    def test_nonexistent_dir_returns_empty(self) -> None:
        from photofant.api.comfyui import _scan_output_dir

        assert _scan_output_dir("/no/such/path") == []

    def test_items_have_source_output_dir(self, tmp_path: Path) -> None:
        from photofant.api.comfyui import _scan_output_dir

        (tmp_path / "img.png").write_bytes(b"x")
        items = _scan_output_dir(str(tmp_path))
        assert items[0].source == "output_dir"


# ── GET /api/comfyui/results ──────────────────────────────────────────────────

class TestListResults:
    def test_output_dir_results_returned(self, db: Session, tmp_path: Path) -> None:
        (tmp_path / "result.png").write_bytes(b"x")
        app = _make_app(db)
        client = TestClient(app)

        with patch("photofant.api.comfyui.load_settings", return_value={
            "comfyui": {"output_dir": str(tmp_path), "base_url": "http://127.0.0.1:8188", "timeout": 5}
        }):
            response = client.get("/api/comfyui/results")

        assert response.status_code == 200
        data = response.json()
        assert any(item["filename"] == "result.png" for item in data["items"])

    def test_history_and_dir_deduplication(self, db: Session, tmp_path: Path) -> None:
        (tmp_path / "output_001.png").write_bytes(b"x")
        app = _make_app(db)
        client = TestClient(app)

        mock_history = {
            "pid1": {
                "outputs": {"4": {"images": [{"filename": "output_001.png", "subfolder": ""}]}}
            }
        }

        with (
            patch("photofant.api.comfyui.load_settings", return_value={
                "comfyui": {"output_dir": str(tmp_path), "base_url": "http://x", "timeout": 5}
            }),
            patch("photofant.api.comfyui.ComfyUIClient") as mock_cls,
        ):
            mock_client = MagicMock()
            mock_client.get_history.return_value = mock_history
            mock_cls.return_value = mock_client
            response = client.get("/api/comfyui/results", params={"prompt_id": "pid1"})

        assert response.status_code == 200
        filenames = [item["filename"] for item in response.json()["items"]]
        # output_001.png must appear only once (history wins, dir entry deduped)
        assert filenames.count("output_001.png") == 1


# ── POST /api/comfyui/results/import ─────────────────────────────────────────

class TestComfyUIImport:
    @pytest.mark.asyncio
    async def test_import_creates_comfyui_version(self, db: Session, tmp_path: Path) -> None:
        """Import via ComfyUI /view → version with type=comfyui created."""
        from photofant.media.person_folders import ensure_person_folder

        person = db.get(Person, 1)
        assert person is not None
        person_dir = ensure_person_folder(tmp_path, person)
        (person_dir / "edits").mkdir(parents=True, exist_ok=True)

        app = _make_app(db)
        client = TestClient(app)

        fake_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with (
            patch("photofant.api.comfyui.load_settings", return_value={
                "comfyui": {
                    "base_url": "http://127.0.0.1:8188",
                    "timeout": 5,
                    "output_dir": str(tmp_path),
                }
            }),
            patch("photofant.api.comfyui.ComfyUIClient") as mock_cls,
            patch("photofant.api.comfyui.get_data_root", return_value=str(tmp_path)),
            patch("photofant.api.comfyui.get_cache_db_path", return_value=str(tmp_path / "cache.db")),
            patch("photofant.api.comfyui.init_cache_db"),
            patch("photofant.api.comfyui.store_thumbnail"),
            patch("photofant.api.comfyui.generate_thumbnail", return_value=b"\xff\xd8"),
        ):
            mock_client = MagicMock()
            mock_client.view_image.return_value = fake_png
            mock_cls.return_value = mock_client

            response = client.post("/api/comfyui/results/import", json={
                "asset_id": 1,
                "filename": "output_001.png",
                "subfolder": "photofant",
            })

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["type"] == "comfyui"
        assert data["is_current"] is True
        assert data["params"]["source"] == "comfyui"
        assert data["params"]["source_filename"] == "output_001.png"

        # Verify version in DB
        version = db.get(Version, data["version_id"])
        assert version is not None
        assert version.type == "comfyui"
        assert version.instance_id == 1

    def test_import_unknown_asset_returns_404(self, db: Session) -> None:
        app = _make_app(db)
        client = TestClient(app)

        with patch("photofant.api.comfyui.load_settings", return_value={
            "comfyui": {"base_url": "http://x", "timeout": 5, "output_dir": ""}
        }):
            response = client.post("/api/comfyui/results/import", json={
                "asset_id": 999,
                "filename": "x.png",
                "subfolder": "",
            })

        assert response.status_code == 404

    def test_import_fallback_to_output_dir(self, db: Session, tmp_path: Path) -> None:
        """When ComfyUI /view fails, fallback reads from output_dir."""
        from photofant.comfyui.client import ComfyUIError
        from photofant.media.person_folders import ensure_person_folder

        person = db.get(Person, 1)
        assert person is not None
        person_dir = ensure_person_folder(tmp_path, person)
        (person_dir / "edits").mkdir(parents=True, exist_ok=True)

        fake_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        (tmp_path / "fallback.png").write_bytes(fake_png)

        app = _make_app(db)
        client = TestClient(app)

        with (
            patch("photofant.api.comfyui.load_settings", return_value={
                "comfyui": {
                    "base_url": "http://x",
                    "timeout": 5,
                    "output_dir": str(tmp_path),
                }
            }),
            patch("photofant.api.comfyui.ComfyUIClient") as mock_cls,
            patch("photofant.api.comfyui.get_data_root", return_value=str(tmp_path)),
            patch("photofant.api.comfyui.get_cache_db_path", return_value=str(tmp_path / "cache.db")),
            patch("photofant.api.comfyui.init_cache_db"),
            patch("photofant.api.comfyui.store_thumbnail"),
            patch("photofant.api.comfyui.generate_thumbnail", return_value=b"\xff\xd8"),
        ):
            mock_client = MagicMock()
            mock_client.view_image.side_effect = ComfyUIError("x", "y", "z")
            mock_cls.return_value = mock_client

            response = client.post("/api/comfyui/results/import", json={
                "asset_id": 1,
                "filename": "fallback.png",
                "subfolder": "",
            })

        assert response.status_code == 201
        assert response.json()["type"] == "comfyui"

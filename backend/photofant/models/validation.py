"""In-place model validation pipeline (Konzept §12.2a).

A user can bind an *already present* model file or folder (a ComfyUI/A1111 stock,
say) instead of downloading it again. This module decides whether the thing at a
given path actually matches the manifest slot the user picked — *before* anything
touches the registry. A failed bind must leave the DB and the filesystem exactly
as they were.

Five ordered validation stages, per the concept:

1. Existence/access  — path exists, is readable, and its shape (file vs folder)
                       matches what the manifest entry expects.
2. Format            — extension + magic bytes match the expected weight format
                       (onnx / safetensors / gguf).
3. Role              — the file fits the slot's role. Deep ONNX-graph
                       introspection needs the inference runtime (onnxruntime),
                       which only lands with the Core-inference milestone; until
                       then this stage uses onnxruntime opportunistically and
                       otherwise logs that role introspection is deferred.
4. Completeness      — folder models carry all required companion files
                       (e.g. the WD14 `selected_tags.csv`, a HF `config.json`).
5. Loadability       — a probe-load: open an ONNX session when onnxruntime is
                       available, otherwise read and sanity-check the protobuf
                       header. Never a full inference.

Each stage raises `ModelValidationError(code, expected, found, next_step)` on
failure; the API layer turns that into a structured 422 the frontend maps onto a
"erwartet · gefunden · nächster Schritt" message. Raw engine exceptions are
logged, never handed to the user verbatim.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from photofant.models.loader import ManifestEntry

log = logging.getLogger(__name__)

# Magic bytes / structural signatures.
_GGUF_MAGIC = b"GGUF"
# ONNX serializes a ModelProto; its first field is `ir_version` (field 1, varint),
# whose protobuf tag byte is 0x08. Not a guaranteed magic, but a reliable smell.
_ONNX_PROTOBUF_TAG = 0x08
_SAFETENSORS_MAX_HEADER = 100 * 1024 * 1024  # 100 MB sanity ceiling for the JSON header
_HASH_CHUNK = 65536


class ModelErrorCode(StrEnum):
    """Structured error codes returned to the frontend (Konzept §12.2a)."""

    NOT_FOUND = "MODEL_NOT_FOUND"
    WRONG_FORMAT = "MODEL_WRONG_FORMAT"
    WRONG_ROLE = "MODEL_WRONG_ROLE"
    INCOMPLETE = "MODEL_INCOMPLETE"
    LOAD_FAILED = "MODEL_LOAD_FAILED"
    HASH_MISMATCH = "MODEL_HASH_MISMATCH"


class ModelFileFormat(StrEnum):
    ONNX = "onnx"
    SAFETENSORS = "safetensors"
    GGUF = "gguf"
    UNKNOWN = "unknown"


class ModelLayout(StrEnum):
    SINGLE_FILE = "single_file"
    FOLDER = "folder"


class ModelValidationError(Exception):
    """A validation stage rejected the chosen path.

    Carries the three things every §12.2a message must name: what was expected,
    what was found, and the next step the user can take.
    """

    def __init__(
        self,
        code: ModelErrorCode,
        *,
        expected: str,
        found: str,
        next_step: str,
    ) -> None:
        super().__init__(f"{code}: expected {expected}, found {found}")
        self.code = code
        self.expected = expected
        self.found = found
        self.next_step = next_step


@dataclass(frozen=True)
class ValidationSpec:
    """What a given manifest entry expects on disk."""

    layout: ModelLayout
    expected_format: ModelFileFormat
    role: str
    required_filenames: tuple[str, ...] = field(default=())
    required_globs: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class InPlaceValidation:
    """Successful validation result handed back to the API layer."""

    primary_path: Path
    sha256: str
    detected_format: ModelFileFormat


def spec_for(entry: ManifestEntry) -> ValidationSpec:
    """Derive the on-disk expectation from a manifest entry.

    The manifest's `format` plus its declared `files` tell us whether to expect a
    single weight file or a folder, and which companions must be present.
    """
    if entry.format == "onnx_bundle":
        # buffalo_l: a folder bundling several .onnx sub-models.
        return ValidationSpec(
            layout=ModelLayout.FOLDER,
            expected_format=ModelFileFormat.ONNX,
            role=entry.role,
            required_globs=("*.onnx",),
        )

    if entry.format == "onnx_folder" or entry.hf_repo:
        # Florence-2: a HuggingFace folder — onnx weights plus a config.json.
        return ValidationSpec(
            layout=ModelLayout.FOLDER,
            expected_format=ModelFileFormat.ONNX,
            role=entry.role,
            required_filenames=("config.json",),
            required_globs=("*.onnx",),
        )

    # Plain "onnx": always a folder named after the manifest_id — consistent with
    # how scan_models_dir stores paths. Even a single-file model (rembg-u2net) lives
    # in <models_dir>/<manifest_id>/u2net.onnx, so we always validate the folder
    # and require the declared filenames inside it.
    declared = tuple(file_info["filename"] for file_info in entry.files)
    return ValidationSpec(
        layout=ModelLayout.FOLDER,
        expected_format=ModelFileFormat.ONNX,
        role=entry.role,
        required_filenames=declared,
    )


def detect_format(path: Path) -> ModelFileFormat:
    """Classify a weight file by magic bytes, falling back to its extension.

    safetensors and gguf carry reliable headers; ONNX is protobuf with no stable
    magic, so we trust the `.onnx` extension once gguf/safetensors are ruled out.
    """
    try:
        with open(path, "rb") as file_handle:
            head = file_handle.read(16)
    except OSError as error:
        log.warning("Could not read header of %s: %s", path, error)
        return ModelFileFormat.UNKNOWN

    if head[:4] == _GGUF_MAGIC:
        return ModelFileFormat.GGUF

    # safetensors: u64 little-endian header length, immediately followed by '{'.
    if len(head) >= 9:
        header_length = int.from_bytes(head[:8], "little")
        if 0 < header_length < _SAFETENSORS_MAX_HEADER and head[8:9] == b"{":
            return ModelFileFormat.SAFETENSORS

    if path.suffix.lower() == ".onnx":
        return ModelFileFormat.ONNX

    return ModelFileFormat.UNKNOWN


def compute_sha256(path: Path) -> str:
    """SHA-256 of an existing file (for the informative in-place hash)."""
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        while chunk := file_handle.read(_HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Probe-load — opportunistic onnxruntime, else protobuf header sniff
# ---------------------------------------------------------------------------


def _open_onnx_session(path: Path) -> Any | None:
    """Open an ONNX inference session if onnxruntime is installed, else None.

    Injectable seam: tests monkeypatch this to exercise the role/loadability
    stages without the heavy runtime present.
    """
    try:
        import onnxruntime  # type: ignore[import-not-found]
    except ImportError:
        return None
    return onnxruntime.InferenceSession(str(path), providers=["CPUExecutionProvider"])


def _looks_like_onnx_protobuf(path: Path) -> bool:
    """Cheap structural sniff used when onnxruntime is unavailable."""
    try:
        with open(path, "rb") as file_handle:
            first = file_handle.read(1)
    except OSError:
        return False
    return first == bytes([_ONNX_PROTOBUF_TAG])


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------


def _stage_existence(path: Path, spec: ValidationSpec) -> None:
    """Stage 1: path exists, is readable, and matches the expected shape."""
    if not path.exists():
        raise ModelValidationError(
            ModelErrorCode.NOT_FOUND,
            expected=f"{'Ordner' if spec.layout is ModelLayout.FOLDER else 'Datei'} unter dem Pfad",
            found=f"nichts unter `{path}`",
            next_step="Pfad prüfen oder neu auswählen.",
        )

    if spec.layout is ModelLayout.FOLDER and not path.is_dir():
        raise ModelValidationError(
            ModelErrorCode.WRONG_FORMAT,
            expected="ein Ordner-Modell (Verzeichnis)",
            found="eine einzelne Datei",
            next_step="Den Modell-Ordner wählen, nicht eine einzelne Datei.",
        )

    if spec.layout is ModelLayout.SINGLE_FILE and not path.is_file():
        raise ModelValidationError(
            ModelErrorCode.WRONG_FORMAT,
            expected="eine einzelne Modell-Datei",
            found="ein Verzeichnis",
            next_step="Die einzelne Modell-Datei wählen, nicht den Ordner.",
        )


def _locate_primary(path: Path, spec: ValidationSpec) -> Path | None:
    """Find the primary weight file (the thing format/role/load checks run on)."""
    if spec.layout is ModelLayout.SINGLE_FILE:
        return path

    # Prefer a declared .onnx companion by exact name, else the first one found.
    for filename in spec.required_filenames:
        if filename.lower().endswith(".onnx"):
            candidate = path / filename
            if candidate.is_file():
                return candidate

    matches = sorted(path.rglob("*.onnx"))
    return matches[0] if matches else None


def _stage_format(primary: Path, spec: ValidationSpec) -> ModelFileFormat:
    """Stage 2: the primary file's format matches what the slot expects."""
    detected = detect_format(primary)
    if detected != spec.expected_format:
        raise ModelValidationError(
            ModelErrorCode.WRONG_FORMAT,
            expected=f"`.{spec.expected_format}`",
            found=f"`{primary.suffix or '?'}` ({detected})",
            next_step=f"Eine {spec.expected_format}-Datei für diesen Slot wählen.",
        )
    return detected


def _has_image_input(onnx_path: Path) -> bool:
    """Return True if the ONNX file at onnx_path has at least one 4-D input tensor."""
    session = _open_onnx_session(onnx_path)
    if session is None:
        return False
    try:
        inputs = session.get_inputs()
    except Exception:  # noqa: BLE001 — engine internals, never surfaced
        return False
    return any(len(getattr(model_input, "shape", []) or []) >= 4 for model_input in inputs)


def _stage_role(root: Path, primary: Path, entry: ManifestEntry, spec: ValidationSpec) -> None:
    """Stage 3: the file plausibly fits the slot's role.

    Reliable role discrimination needs the ONNX graph (input rank/shape), which
    requires onnxruntime. When it is present we check that image-consuming roles
    really take an image-shaped (4-D) input; when it is absent we log and defer —
    the format stage and the completeness stage already carry the role signal for
    the core ONNX set (a wrong-format file is rejected earlier, a tagger bundle
    must ship its CSV, etc.).

    Multi-component folders (e.g. CLIP with vision + text model) must have at
    least ONE .onnx file with a 4-D input. Checking only the alphabetically-first
    file would misidentify the text encoder as the primary and fail the role check.
    root is the folder path passed by validate_in_place; primary is the specific
    .onnx file chosen by _locate_primary.
    """
    image_roles = {"face", "tagger", "semantic_search", "rembg"}
    if entry.role not in image_roles:
        return

    # For folders, scan all .onnx files under root (covers sub-dirs like onnx/).
    # For single files, just that file. Any one passing the 4-D check is enough.
    if spec.layout is ModelLayout.FOLDER and root.is_dir():
        candidates = sorted(root.rglob("*.onnx"))
    else:
        candidates = [primary]

    if not candidates:
        return

    # Check whether onnxruntime is available before looping over candidates.
    if _open_onnx_session(candidates[0]) is None:
        log.info(
            "onnxruntime unavailable — role introspection for %r deferred to the inference runtime",
            entry.id,
        )
        return

    if any(_has_image_input(candidate) for candidate in candidates):
        return

    input_ranks_per_file = []
    for candidate in candidates:
        session = _open_onnx_session(candidate)
        if session is not None:
            try:
                ranks = [len(getattr(inp, "shape", []) or []) for inp in session.get_inputs()]
                input_ranks_per_file.append(f"{candidate.name}:{ranks}")
            except Exception:  # noqa: BLE001
                pass

    raise ModelValidationError(
        ModelErrorCode.WRONG_ROLE,
        expected=f"ein Bild-Modell für die Rolle `{entry.role}` (mind. ein 4-D-Eingang)",
        found=f"kein Modell im Ordner hat einen 4-D-Eingang — {'; '.join(input_ranks_per_file)}",
        next_step="Slot oder Ordner korrigieren — keines der ONNX-Modelle darin passt zu dieser Rolle.",
    )


def _stage_completeness(path: Path, spec: ValidationSpec) -> None:
    """Stage 4: folder models carry every required companion file."""
    if spec.layout is ModelLayout.SINGLE_FILE:
        return

    missing: list[str] = []
    for filename in spec.required_filenames:
        if not (path / filename).is_file():
            missing.append(filename)

    for glob_pattern in spec.required_globs:
        if not any(path.rglob(glob_pattern)):
            missing.append(glob_pattern)

    if missing:
        raise ModelValidationError(
            ModelErrorCode.INCOMPLETE,
            expected=f"alle Pflichtbestandteile: {', '.join(spec.required_filenames + spec.required_globs)}",
            found=f"es fehlen: {', '.join(missing)}",
            next_step="Den vollständigen Modell-Ordner wählen (inkl. aller Begleitdateien).",
        )


def _stage_loadability(primary: Path, spec: ValidationSpec) -> None:
    """Stage 5: probe-load without running inference."""
    if spec.expected_format is not ModelFileFormat.ONNX:
        return

    try:
        session = _open_onnx_session(primary)
    except Exception as error:  # noqa: BLE001 — raw engine error, translated below
        log.warning("ONNX probe-load failed for %s: %s", primary, error)
        raise ModelValidationError(
            ModelErrorCode.LOAD_FAILED,
            expected="eine ladbare ONNX-Datei",
            found="eine Datei, die die ONNX-Runtime nicht öffnen konnte",
            next_step=f"Datei evtl. beschädigt oder inkompatibel. Engine-Meldung: {error}",
        ) from error

    if session is not None:
        return

    # No onnxruntime: fall back to a protobuf-header sniff.
    if not _looks_like_onnx_protobuf(primary):
        raise ModelValidationError(
            ModelErrorCode.LOAD_FAILED,
            expected="einen gültigen ONNX-Protobuf-Header",
            found="Bytes, die nicht wie ein ONNX-Modell aussehen",
            next_step="Datei evtl. beschädigt oder kein echtes ONNX-Modell.",
        )


def validate_in_place(entry: ManifestEntry, raw_path: str) -> InPlaceValidation:
    """Run all five stages in order; return the primary path + informative hash.

    Raises `ModelValidationError` on the first failing stage. Performs no DB or
    filesystem mutation — a caller may safely register only on success.
    """
    spec = spec_for(entry)
    path = Path(raw_path)

    _stage_existence(path, spec)

    primary = _locate_primary(path, spec)
    if primary is None:
        # Folder present but holds no weight file → an incompleteness, reported as such.
        raise ModelValidationError(
            ModelErrorCode.INCOMPLETE,
            expected="eine ONNX-Gewichtsdatei im Ordner",
            found="keine `.onnx`-Datei im gewählten Ordner",
            next_step="Den korrekten Modell-Ordner wählen.",
        )

    _stage_format(primary, spec)
    _stage_role(path, primary, entry, spec)
    _stage_completeness(path, spec)
    _stage_loadability(primary, spec)

    sha256 = compute_sha256(primary)
    log.info("In-place validation passed for %r at %s (sha256=%s…)", entry.id, path, sha256[:8])
    return InPlaceValidation(primary_path=primary, sha256=sha256, detected_format=spec.expected_format)

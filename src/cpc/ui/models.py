from __future__ import annotations

import hashlib
import shutil
import ssl
import sys
import traceback
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from cpc.ui.settings import AppSettings


class ModelStatus(str, Enum):
    RECOMMENDED = "Recommended"
    READY = "Ready"
    NOT_INSTALLED = "Not Installed"
    MISSING = "Missing"
    CUSTOM = "Custom"
    INCOMPATIBLE = "Incompatible"
    INSTALLING = "Installing"
    ERROR = "Error"


@dataclass
class ModelEntry:
    """Authoritative metadata representation of a tracking model."""

    model_id: str
    name: str
    backend: str  # "mediapipe" | "null" | "custom"
    description: str
    capabilities: list[str] = field(default_factory=list)
    is_recommended: bool = False
    source_url: str | None = None
    filename: str = ""
    expected_size_bytes: int | None = None
    expected_sha256: str | None = None
    license_name: str = "Apache 2.0"
    default_delegate: str = "cpu"
    version: str = "1.0"
    custom_path: Path | None = None


# Official Google MediaPipe Face Landmarker model asset
RECOMMENDED_MEDIAPIPE_MODEL = ModelEntry(
    model_id="mediapipe-face-landmarker",
    name="MediaPipe Face Landmarker",
    backend="mediapipe",
    description="Face tracking, expressions and head motion (478 pts + 52 blendshapes)",
    capabilities=[
        "478 3D Facial Landmarks",
        "52 ARKit Blendshape Coefficients",
        "Tait-Bryan Head Rotation Matrix",
    ],
    is_recommended=True,
    source_url="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
    filename="face_landmarker.task",
    expected_size_bytes=3773411,
    license_name="Apache 2.0",
    default_delegate="cpu",
    version="float16-latest",
)

NULL_TRACKER_MODEL = ModelEntry(
    model_id="null-tracker",
    name="No Tracking (Passthrough / Baseline)",
    backend="null",
    description="Testing / passthrough preview only (no tracker inference)",
    capabilities=["Passthrough Frame Feed"],
    is_recommended=False,
    filename="",
    license_name="Proprietary",
    default_delegate="cpu",
    version="1.0",
)


def get_managed_models_dir() -> Path:
    """Resolve the platform-native application storage directory for CPC-managed models."""
    if sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support" / "CharacterPerformanceCapture"
    elif sys.platform == "win32":
        import os

        base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "CharacterPerformanceCapture"
    else:
        base_dir = Path.home() / ".local" / "share" / "character-performance-capture"

    models_dir = base_dir / "models"
    try:
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir
    except (OSError, PermissionError):
        pass

    try:
        fallback_dir = Path.home() / ".cpc" / "models"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir
    except (OSError, PermissionError):
        pass

    import tempfile

    tmp_fallback = Path(tempfile.gettempdir()) / "cpc_models"
    tmp_fallback.mkdir(parents=True, exist_ok=True)
    return tmp_fallback


class ModelDownloadWorker(QThread):
    """Executes a user-initiated model download in the background with progress reporting and cancellation."""

    progress_updated = Signal(int, str)  # (percent, status_message)
    download_finished = Signal(Path)  # destination_path
    error_occurred = Signal(str, str)  # (user_friendly_message, technical_details)

    def __init__(
        self,
        source_url: str,
        dest_path: Path,
        expected_size: int | None = None,
        expected_sha256: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.source_url = source_url
        self.dest_path = dest_path
        self.expected_size = expected_size
        self.expected_sha256 = expected_sha256
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        self.progress_updated.emit(0, "Connecting to official model storage...")
        tmp_path = self.dest_path.with_suffix(".tmp")
        self.dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create a secure SSL context for official HTTPS downloads
            context = ssl.create_default_context()
            req = urllib.request.Request(
                self.source_url,
                headers={"User-Agent": "CharacterPerformanceCapture/1.1.0"},
            )

            with urllib.request.urlopen(req, context=context, timeout=20.0) as response, open(tmp_path, "wb") as out_f:
                content_length = response.headers.get("Content-Length")
                total_bytes = int(content_length) if content_length and content_length.isdigit() else (self.expected_size or 0)
                downloaded_bytes = 0
                chunk_size = 32768  # 32 KB chunks

                hasher = hashlib.sha256() if self.expected_sha256 else None

                while True:
                    if self._is_cancelled:
                        if tmp_path.exists():
                            tmp_path.unlink()
                        self.error_occurred.emit("Model download cancelled by user.", "User clicked Cancel.")
                        return

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    out_f.write(chunk)
                    if hasher:
                        hasher.update(chunk)
                    downloaded_bytes += len(chunk)

                    if total_bytes > 0:
                        pct = min(100, int((downloaded_bytes / total_bytes) * 100))
                        mb_done = downloaded_bytes / (1024 * 1024)
                        mb_total = total_bytes / (1024 * 1024)
                        self.progress_updated.emit(pct, f"Downloading: {mb_done:.1f} / {mb_total:.1f} MB ({pct}%)")
                    else:
                        mb_done = downloaded_bytes / (1024 * 1024)
                        self.progress_updated.emit(50, f"Downloading: {mb_done:.1f} MB")

            # Check downloaded file integrity
            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                raise ValueError("Downloaded model file is empty.")

            if self.expected_sha256 and hasher:
                computed_sha = hasher.hexdigest()
                if computed_sha.lower() != self.expected_sha256.lower():
                    raise ValueError(f"Checksum mismatch. Expected {self.expected_sha256}, got {computed_sha}")

            # Atomic move into final path
            if self.dest_path.exists():
                self.dest_path.unlink()
            shutil.move(str(tmp_path), str(self.dest_path))

            self.progress_updated.emit(100, "Model verified and installed.")
            self.download_finished.emit(self.dest_path)

        except (RuntimeError, ValueError, OSError, TimeoutError, ssl.SSLError, urllib.error.URLError) as exc:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

            user_msg = (
                "Model could not be installed.\n\n"
                "CPC couldn't retrieve the recommended Face Landmarker model from Google's official storage. "
                "Please check your internet connection or import a local model file."
            )
            tech_details = (
                f"Download Failure Exception: {type(exc).__name__}: {exc}\n"
                f"URL: {self.source_url}\n"
                f"Destination: {self.dest_path}\n"
                f"Platform: {sys.platform}\n\n"
                f"{traceback.format_exc()}"
            )
            self.error_occurred.emit(user_msg, tech_details)


class ModelRegistry(QObject):
    """Authoritative UI-side Model Registry for managing curated and custom tracking models."""

    registry_changed = Signal()

    def __init__(self, base_dir: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self._settings = AppSettings()
        self._base_dir = Path(base_dir) if base_dir else None
        self._models: dict[str, ModelEntry] = {
            RECOMMENDED_MEDIAPIPE_MODEL.model_id: RECOMMENDED_MEDIAPIPE_MODEL,
            NULL_TRACKER_MODEL.model_id: NULL_TRACKER_MODEL,
        }
        self._load_custom_models()

    def _load_custom_models(self) -> None:
        """Load registered custom models from application settings."""
        custom_paths = self._settings.get_recent_items("custom_models")
        for p_str in custom_paths:
            p = Path(p_str)
            if p.is_file():
                mid = f"custom:{p.stem}"
                entry = ModelEntry(
                    model_id=mid,
                    name=f"Custom: {p.name}",
                    backend="mediapipe",
                    description=f"Local MediaPipe Face Landmarker asset ({p.name})",
                    capabilities=["Facial Landmarks", "Blendshapes", "Head Rotation"],
                    is_recommended=False,
                    filename=p.name,
                    custom_path=p,
                )
                self._models[mid] = entry

    def get_entries(self) -> list[ModelEntry]:
        """Return all catalog entries (including built-in modes)."""
        return list(self._models.values())

    def get_installable_entries(self) -> list[ModelEntry]:
        """Return only installable model files (excluding built-in modes like null tracker)."""
        return [e for e in self._models.values() if e.model_id != NULL_TRACKER_MODEL.model_id]

    def get_recommended_entry(self) -> ModelEntry:
        """Return the primary recommended model entry."""
        return RECOMMENDED_MEDIAPIPE_MODEL

    def get_entry(self, model_id: str) -> ModelEntry | None:
        """Retrieve a model entry by its stable ID."""
        return self._models.get(model_id)

    def resolve_model_path(self, model_id: str) -> Path | None:
        """Resolve the local filesystem path for a given model ID."""
        if model_id == NULL_TRACKER_MODEL.model_id:
            return None

        entry = self._models.get(model_id)
        if entry is None:
            return None

        if entry.custom_path is not None:
            return entry.custom_path if entry.custom_path.is_file() else None

        if model_id == RECOMMENDED_MEDIAPIPE_MODEL.model_id:
            if self._base_dir is not None:
                managed_path = self._base_dir / "mediapipe" / RECOMMENDED_MEDIAPIPE_MODEL.filename
                if managed_path.is_file() and managed_path.stat().st_size > 100000:
                    return managed_path
                return None

            # Check managed application storage location first
            managed_path = get_managed_models_dir() / "mediapipe" / RECOMMENDED_MEDIAPIPE_MODEL.filename
            if managed_path.is_file() and managed_path.stat().st_size > 100000:
                return managed_path

            # Check validation cache fallback
            cache_fallback = Path.home() / ".cache" / "cpc-validation" / RECOMMENDED_MEDIAPIPE_MODEL.filename
            if cache_fallback.is_file() and cache_fallback.stat().st_size > 100000:
                return cache_fallback

            # Check current working directory
            cwd_fallback = Path.cwd() / RECOMMENDED_MEDIAPIPE_MODEL.filename
            if cwd_fallback.is_file() and cwd_fallback.stat().st_size > 100000:
                return cwd_fallback

        return None

    def get_status(self, model_id: str) -> ModelStatus:
        """Evaluate the readiness status of a model."""
        if model_id == NULL_TRACKER_MODEL.model_id:
            return ModelStatus.READY

        entry = self._models.get(model_id)
        if entry is None:
            return ModelStatus.MISSING

        resolved = self.resolve_model_path(model_id)
        if resolved is not None and resolved.is_file():
            return ModelStatus.READY

        if entry.is_recommended:
            return ModelStatus.NOT_INSTALLED

        return ModelStatus.MISSING

    def get_managed_destination(self, model_id: str) -> Path:
        """Get the authoritative installation destination for a curated model."""
        entry = self._models.get(model_id, RECOMMENDED_MEDIAPIPE_MODEL)
        managed_dir = (self._base_dir if self._base_dir is not None else get_managed_models_dir()) / entry.backend
        managed_dir.mkdir(parents=True, exist_ok=True)
        return managed_dir / entry.filename

    def register_custom_model(self, file_path: Path | str, copy_to_managed: bool = False) -> ModelEntry:
        """Register a user-provided custom model file."""
        src_path = Path(file_path).resolve()
        if not src_path.is_file():
            raise FileNotFoundError(f"Custom model file does not exist: {src_path}")

        # Validate file
        valid, reason = self.validate_model_file(src_path)
        if not valid:
            raise ValueError(f"Incompatible MediaPipe model: {reason}")

        if copy_to_managed:
            managed_dir = get_managed_models_dir() / "custom"
            managed_dir.mkdir(parents=True, exist_ok=True)
            target_path = managed_dir / src_path.name
            if target_path != src_path:
                shutil.copy2(src_path, target_path)
            stored_path = target_path
        else:
            stored_path = src_path

        mid = f"custom:{stored_path.stem}"
        entry = ModelEntry(
            model_id=mid,
            name=f"Custom: {stored_path.name}",
            backend="mediapipe",
            description=f"User-imported MediaPipe Face Landmarker ({stored_path.name})",
            capabilities=["Facial Landmarks", "Blendshapes", "Head Rotation"],
            is_recommended=False,
            filename=stored_path.name,
            custom_path=stored_path,
        )

        self._models[mid] = entry
        self._settings.add_recent_item("custom_models", stored_path)
        self.registry_changed.emit()
        return entry

    def register_custom_path(self, file_path: Path | str) -> ModelEntry:
        """Register or associate an existing custom model file path without requiring active model validation."""
        path = Path(file_path)
        mid = f"custom:{path.stem}"
        if mid in self._models:
            return self._models[mid]

        entry = ModelEntry(
            model_id=mid,
            name=f"Custom: {path.name}",
            backend="mediapipe",
            description=f"Local MediaPipe Face Landmarker asset ({path.name})",
            capabilities=["Facial Landmarks", "Blendshapes", "Head Rotation"],
            is_recommended=False,
            filename=path.name,
            custom_path=path,
        )
        self._models[mid] = entry
        self._settings.add_recent_item("custom_models", path)
        self.registry_changed.emit()
        return entry

    def validate_model_file(self, file_path: Path | str) -> tuple[bool, str]:
        """Perform a bounded compatibility check on a candidate .task model file."""
        path = Path(file_path)
        if not path.is_file():
            return False, "File does not exist."

        if path.stat().st_size < 50000:
            return False, "File size is too small for a MediaPipe Face Landmarker model."

        try:
            from cpc.mediapipe_tracker import create_face_landmarker

            # Attempt a minimal initialization to confirm MediaPipe can parse options
            landmarker = create_face_landmarker(path, delegate="cpu", running_mode="IMAGE")
            if hasattr(landmarker, "close"):
                landmarker.close()
            return True, "Valid MediaPipe Face Landmarker model."
        except (RuntimeError, ValueError, OSError, FileNotFoundError, ImportError, AttributeError) as exc:
            return False, f"MediaPipe model initialization error: {exc}"


# Global singleton instance for UI usage
_GLOBAL_REGISTRY: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ModelRegistry()
    return _GLOBAL_REGISTRY


def reset_model_registry(registry: ModelRegistry | None = None) -> None:
    """Reset or override the global model registry instance (useful for test hermeticity)."""
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = registry

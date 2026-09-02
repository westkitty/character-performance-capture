from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cpc.ui.models import (
    RECOMMENDED_MEDIAPIPE_MODEL,
    ModelDownloadWorker,
    ModelEntry,
    ModelRegistry,
    ModelStatus,
    get_model_registry,
)


class ModelSelectorWidget(QWidget):
    """Curated, progressive-disclosure Tracking Model selection widget for Character Setup and Live Studio."""

    model_selection_changed = Signal(str, object, str)  # (model_id, resolved_path: Path | None, delegate: str)
    status_changed = Signal(str)  # status string

    def __init__(self, parent=None, compact: bool = False) -> None:
        super().__init__(parent)
        self._compact = compact
        self._active_model_id = RECOMMENDED_MEDIAPIPE_MODEL.model_id
        self._active_delegate = "cpu"
        self._download_worker: ModelDownloadWorker | None = None

        self._init_ui()
        self._registry.registry_changed.connect(self._refresh_models_list)
        self._refresh_models_list()

    @property
    def _registry(self) -> ModelRegistry:
        return get_model_registry()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. Primary Model Card
        # -------------------------------------------------------------
        self._card = QFrame()
        self._card.setStyleSheet(
            "QFrame { background-color: #13131a; border: 1px solid #232330; border-radius: 8px; padding: 10px; }"
        )
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)

        # Top Header Row: Model Selector Combo, Recommended Badge, Status Pill
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.setMinimumHeight(32)
        self._model_combo.currentIndexChanged.connect(self._on_combo_changed)
        header_row.addWidget(self._model_combo, 1)

        self._recommended_badge = QLabel("★ RECOMMENDED")
        self._recommended_badge.setStyleSheet(
            "background-color: #1e3a8a; color: #93c5fd; font-weight: 700; font-size: 11px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid #3b82f6;"
        )
        header_row.addWidget(self._recommended_badge)

        self._status_pill = QLabel("● Ready")
        self._status_pill.setStyleSheet(
            "font-weight: 700; font-size: 12px; color: #10b981; padding: 2px 6px;"
        )
        header_row.addWidget(self._status_pill)
        card_layout.addLayout(header_row)

        # Description
        self._desc_lbl = QLabel(RECOMMENDED_MEDIAPIPE_MODEL.description)
        self._desc_lbl.setStyleSheet("color: #a1a1aa; font-size: 12px; line-height: 1.3;")
        self._desc_lbl.setWordWrap(True)
        card_layout.addWidget(self._desc_lbl)

        # Capability Pills Row
        self._caps_widget = QWidget()
        self._caps_layout = QHBoxLayout(self._caps_widget)
        self._caps_layout.setContentsMargins(0, 0, 0, 0)
        self._caps_layout.setSpacing(6)
        card_layout.addWidget(self._caps_widget)

        # Action: Install Button (visible when Recommended is not installed)
        self._install_btn = QPushButton("⚡  Install Recommended Model (Download 3.6 MB)")
        self._install_btn.setProperty("primary", True)
        self._install_btn.setMinimumHeight(36)
        font_ib = QFont(self._install_btn.font())
        font_ib.setBold(True)
        self._install_btn.setFont(font_ib)
        self._install_btn.clicked.connect(self.install_recommended_model)
        card_layout.addWidget(self._install_btn)

        # Download Progress Row (hidden by default)
        self._progress_widget = QWidget()
        prog_layout = QVBoxLayout(self._progress_widget)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(4)

        self._prog_status_lbl = QLabel("Downloading official model asset...")
        self._prog_status_lbl.setStyleSheet("color: #60a5fa; font-size: 12px;")
        prog_layout.addWidget(self._prog_status_lbl)

        prog_bar_row = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        prog_bar_row.addWidget(self._progress_bar, 1)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setMaximumWidth(70)
        self._cancel_btn.clicked.connect(self.cancel_installation)
        prog_bar_row.addWidget(self._cancel_btn)
        prog_layout.addLayout(prog_bar_row)

        self._progress_widget.setVisible(False)
        card_layout.addWidget(self._progress_widget)

        main_layout.addWidget(self._card)

        # -------------------------------------------------------------
        # 2. Collapsible Advanced Technical Details
        # -------------------------------------------------------------
        self._adv_toggle_btn = QPushButton("▸ Advanced Model Details")
        self._adv_toggle_btn.setFlat(True)
        self._adv_toggle_btn.setStyleSheet("text-align: left; color: #71717a; font-size: 11px; padding: 2px 0;")
        self._adv_toggle_btn.clicked.connect(self._toggle_advanced)
        main_layout.addWidget(self._adv_toggle_btn)

        self._adv_widget = QWidget()
        adv_layout = QVBoxLayout(self._adv_widget)
        adv_layout.setContentsMargins(4, 4, 4, 4)
        adv_layout.setSpacing(6)

        # Resolved Path
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Model File:"))
        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText("No local model file resolved")
        path_row.addWidget(self._path_edit, 1)

        self._reveal_btn = QPushButton("📁")
        self._reveal_btn.setMaximumWidth(32)
        self._reveal_btn.setToolTip("Reveal model file in Finder")
        self._reveal_btn.clicked.connect(self._reveal_model_in_finder)
        path_row.addWidget(self._reveal_btn)

        self._copy_path_btn = QPushButton("📋")
        self._copy_path_btn.setMaximumWidth(32)
        self._copy_path_btn.setToolTip("Copy file path to clipboard")
        self._copy_path_btn.clicked.connect(self._copy_model_path)
        path_row.addWidget(self._copy_path_btn)
        adv_layout.addLayout(path_row)

        # Delegate & Custom Import Row
        bottom_adv_row = QHBoxLayout()
        bottom_adv_row.addWidget(QLabel("Compute Delegate:"))
        self._delegate_combo = QComboBox()
        self._delegate_combo.addItems([
            "CPU (Validated Default)",
            "GPU (Experimental)",
        ])
        self._delegate_combo.currentIndexChanged.connect(self._on_delegate_changed)
        bottom_adv_row.addWidget(self._delegate_combo, 1)

        self._import_custom_btn = QPushButton("📂 Import Custom Model...")
        self._import_custom_btn.clicked.connect(self._import_custom_model_dialog)
        bottom_adv_row.addWidget(self._import_custom_btn)
        adv_layout.addLayout(bottom_adv_row)

        self._adv_widget.setVisible(False)
        main_layout.addWidget(self._adv_widget)

        self._refresh_models_list()

    def _toggle_advanced(self) -> None:
        is_vis = not self._adv_widget.isVisible()
        self._adv_widget.setVisible(is_vis)
        self._adv_toggle_btn.setText("▾ Advanced Model Details" if is_vis else "▸ Advanced Model Details")

    def _refresh_models_list(self) -> None:
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        entries = self._registry.get_entries()
        for e in entries:
            self._model_combo.addItem(e.name, e.model_id)
        # Select active
        idx = self._model_combo.findData(self._active_model_id)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        self._model_combo.blockSignals(False)
        self.refresh_state()

    def _on_combo_changed(self, idx: int) -> None:
        mid = self._model_combo.itemData(idx)
        if mid:
            self._active_model_id = mid
            self.refresh_state()
            self._emit_change()

    def _on_delegate_changed(self, idx: int) -> None:
        self._active_delegate = "gpu" if idx == 1 else "cpu"
        self._emit_change()

    def refresh_state(self) -> None:
        entry = self._registry.get_entry(self._active_model_id) or RECOMMENDED_MEDIAPIPE_MODEL
        status = self._registry.get_status(self._active_model_id)
        resolved_path = self._registry.resolve_model_path(self._active_model_id)

        # Update description & capabilities
        self._desc_lbl.setText(entry.description)
        self._recommended_badge.setVisible(entry.is_recommended)

        # Update capability pills dynamically
        while self._caps_layout.count():
            item = self._caps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for cap in entry.capabilities:
            pill = QLabel(cap)
            pill.setStyleSheet(
                "background-color: #1a1a26; color: #d4d4d8; font-size: 11px; padding: 3px 8px; border-radius: 4px; border: 1px solid #28283a;"
            )
            self._caps_layout.addWidget(pill)
        self._caps_layout.addStretch(1)
        self._caps_widget.setVisible(len(entry.capabilities) > 0)

        # Update path display
        if resolved_path:
            self._path_edit.setText(str(resolved_path))
            self._reveal_btn.setEnabled(True)
            self._copy_path_btn.setEnabled(True)
        else:
            self._path_edit.setText("No local file found (Installation required)")
            self._reveal_btn.setEnabled(False)
            self._copy_path_btn.setEnabled(False)

        # Update Status Pill & Install Button
        if self._download_worker is not None and self._download_worker.isRunning():
            self._status_pill.setText("⟳ Installing...")
            self._status_pill.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 12px;")
            self._install_btn.setVisible(False)
            self._progress_widget.setVisible(True)
        elif status == ModelStatus.READY:
            self._status_pill.setText("● Ready")
            self._status_pill.setStyleSheet("color: #10b981; font-weight: 700; font-size: 12px;")
            self._install_btn.setVisible(False)
            self._progress_widget.setVisible(False)
        elif status == ModelStatus.NOT_INSTALLED:
            self._status_pill.setText("▲ Not Installed")
            self._status_pill.setStyleSheet("color: #f59e0b; font-weight: 700; font-size: 12px;")
            self._install_btn.setVisible(True)
            self._progress_widget.setVisible(False)
        else:
            self._status_pill.setText("✕ Missing")
            self._status_pill.setStyleSheet("color: #ef4444; font-weight: 700; font-size: 12px;")
            self._install_btn.setVisible(entry.is_recommended)
            self._progress_widget.setVisible(False)

        self.status_changed.emit(status.value)

    def _emit_change(self) -> None:
        path = self._registry.resolve_model_path(self._active_model_id)
        self.model_selection_changed.emit(self._active_model_id, path, self._active_delegate)

    def select_model(self, model_id: str) -> None:
        idx = self._model_combo.findData(model_id)
        if idx < 0:
            self._refresh_models_list()
            idx = self._model_combo.findData(model_id)

        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        else:
            self._active_model_id = model_id
            self.refresh_state()

    def set_delegate(self, delegate: str) -> None:
        self._active_delegate = delegate.lower().strip()
        idx = 1 if self._active_delegate == "gpu" else 0
        self._delegate_combo.setCurrentIndex(idx)

    def get_selected_model_id(self) -> str:
        return self._active_model_id

    def get_selected_entry(self) -> ModelEntry:
        return self._registry.get_entry(self._active_model_id) or RECOMMENDED_MEDIAPIPE_MODEL

    def get_resolved_path(self) -> Path | None:
        return self._registry.resolve_model_path(self._active_model_id)

    def get_selected_delegate(self) -> str:
        return self._active_delegate

    def is_ready(self) -> bool:
        return self._registry.get_status(self._active_model_id) == ModelStatus.READY

    # -----------------------------------------------------------------
    # User-Initiated Download Lifecycle
    # -----------------------------------------------------------------
    def install_recommended_model(self) -> None:
        """Trigger explicit, user-initiated download of the recommended model asset."""
        entry = RECOMMENDED_MEDIAPIPE_MODEL
        if not entry.source_url:
            return

        dest_path = self._registry.get_managed_destination(entry.model_id)

        self._download_worker = ModelDownloadWorker(
            source_url=entry.source_url,
            dest_path=dest_path,
            expected_size=entry.expected_size_bytes,
            expected_sha256=entry.expected_sha256,
            parent=self,
        )
        self._download_worker.progress_updated.connect(self._on_download_progress)
        self._download_worker.download_finished.connect(self._on_download_finished)
        self._download_worker.error_occurred.connect(self._on_download_error)

        self.refresh_state()
        self._download_worker.start()

    def cancel_installation(self) -> None:
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.cancel()

    def _on_download_progress(self, pct: int, msg: str) -> None:
        self._progress_bar.setValue(pct)
        self._prog_status_lbl.setText(msg)

    def _on_download_finished(self, dest: Path) -> None:
        self._download_worker = None
        self.refresh_state()
        self._emit_change()
        QMessageBox.information(
            self,
            "Installation Complete",
            f"MediaPipe Face Landmarker model successfully verified and installed to:\n{dest.name}",
        )

    def _on_download_error(self, user_msg: str, tech_details: str) -> None:
        self._download_worker = None
        self.refresh_state()
        QMessageBox.critical(self, "Download Error", f"{user_msg}\n\nTechnical details:\n{tech_details}")

    # -----------------------------------------------------------------
    # Custom Model Import Dialog
    # -----------------------------------------------------------------
    def _import_custom_model_dialog(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import Compatible MediaPipe Face Landmarker Model",
            str(Path.home()),
            "MediaPipe Models (*.task);;All Files (*)",
        )
        if not path_str:
            return

        p = Path(path_str)
        try:
            entry = self._registry.register_custom_model(p, copy_to_managed=True)
            self._refresh_models_list()
            self.select_model(entry.model_id)
            QMessageBox.information(
                self,
                "Model Imported",
                f"Custom model '{p.name}' successfully validated and registered.",
            )
        except (RuntimeError, ValueError, OSError, FileNotFoundError) as exc:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Could not import model:\n{exc}\n\nEnsure this is a valid MediaPipe Face Landmarker .task file.",
            )

    def _reveal_model_in_finder(self) -> None:
        path = self.get_resolved_path()
        if path and path.is_file():
            QDesktopServices.openUrl(f"file://{path.parent.resolve()}")

    def _copy_model_path(self) -> None:
        path = self.get_resolved_path()
        if path:
            QApplication.clipboard().setText(str(path.resolve()))
            QMessageBox.information(self, "Copied", "Model path copied to clipboard.")

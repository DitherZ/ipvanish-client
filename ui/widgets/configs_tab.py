"""
ui/widgets/configs_tab.py
Config file downloader — embedded into Settings.
Styled consistently with the dashboard (flat, no card frame).
IPVanish-Client v2
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFileDialog,
)

from core.downloader import DownloadManager
from core.profiles import ProfileStore

CONFIGS_DIR = Path(__file__).parents[2] / "config"


class ConfigsTab(QWidget):
    profile_imported = pyqtSignal()   # emitted after a file is successfully imported

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store   = ProfileStore()
        self._manager = DownloadManager()
        self._manager.progress.connect(self._on_progress)
        self._manager.status.connect(self._on_status)
        self._manager.finished.connect(self._on_finished)
        self._manager.error.connect(self._on_error)
        self._build_ui()
        self._refresh_state()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Status line — uses green accent when ready, muted otherwise
        self._status_label = QLabel("Checking configs…")
        self._status_label.setObjectName("dashISP")
        layout.addWidget(self._status_label)
        layout.addSpacing(12)

        # Progress bar (hidden until download starts)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("dashDisclaimer")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)
        layout.addSpacing(12)

        # Buttons
        btn_row = QHBoxLayout()
        self._download_btn = QPushButton("Download Config Files")
        self._download_btn.clicked.connect(lambda: self._start_download(purge=False))
        self._redownload_btn = QPushButton("Re-Download (Fresh)")
        self._redownload_btn.clicked.connect(lambda: self._start_download(purge=True))
        self._import_btn = QPushButton("Add Config File…")
        self._import_btn.clicked.connect(self._import_file)
        btn_row.addWidget(self._download_btn)
        btn_row.addWidget(self._redownload_btn)
        btn_row.addWidget(self._import_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _refresh_state(self):
        if self._manager.configs_exist():
            ipvanish_dir = CONFIGS_DIR / "ipvanish"
            count = len(list(ipvanish_dir.glob("*.ovpn"))) if ipvanish_dir.exists() else 0
            self._status_label.setText(f"✓  {count} config files ready")
            self._status_label.setObjectName("dashLocation")   # green
            self._status_label.style().unpolish(self._status_label)
            self._status_label.style().polish(self._status_label)
            self._download_btn.setVisible(False)
            self._redownload_btn.setVisible(True)
        else:
            self._status_label.setText("No config files found — download required.")
            self._status_label.setObjectName("dashISP")        # muted
            self._status_label.style().unpolish(self._status_label)
            self._status_label.style().polish(self._status_label)
            self._download_btn.setVisible(True)
            self._redownload_btn.setVisible(False)

    def _start_download(self, purge: bool):
        self._download_btn.setEnabled(False)
        self._redownload_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress.setValue(0)
        self._manager.start(purge_first=purge)

    @pyqtSlot(int, int)
    def _on_progress(self, done: int, total: int):
        self._progress.setMaximum(total)
        self._progress.setValue(done)
        self._progress_label.setText(f"{done} / {total} files downloaded")

    @pyqtSlot(str)
    def _on_status(self, msg: str):
        self._status_label.setText(msg)

    @pyqtSlot()
    def _on_finished(self):
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        self._download_btn.setEnabled(True)
        self._redownload_btn.setEnabled(True)
        self._refresh_state()

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import VPN Config",
            str(Path.home()),
            "VPN Configs (*.ovpn *.conf);;All Files (*)",
        )
        if not path:
            return
        try:
            self._store.import_file(Path(path))
            self.profile_imported.emit()
        except Exception as exc:
            self._status_label.setText(f"✗  Import failed: {exc}")

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        self._status_label.setText(f"✗  Error: {msg}")
        self._status_label.setObjectName("dashISP")
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        self._download_btn.setEnabled(True)
        self._redownload_btn.setEnabled(True)

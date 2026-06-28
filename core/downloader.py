"""
core/downloader.py
Downloads IPVanish OpenVPN config files using concurrent requests.
Uses QThread + signals so the GUI never freezes.
IPVanish-Client v2
"""

import os
import shutil
from pathlib import Path
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup as Soup
from PyQt6.QtCore import QObject, pyqtSignal, QThread


CONFIGS_DIR    = Path(__file__).parents[1] / "config"
IPVANISH_DIR   = CONFIGS_DIR / "ipvanish"   # purge-safe subtree for bulk downloads
DOWNLOAD_BASE  = "https://configs.ipvanish.com/configs/"
MAX_WORKERS    = 20


class DownloadWorker(QObject):
    """
    Emits progress and completion signals while downloading configs.
    Designed to be moved to a QThread.
    """
    progress = pyqtSignal(int, int)       # (completed, total)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, purge_first: bool = False):
        super().__init__()
        self._purge = purge_first
        self._lock = Lock()
        self._completed = 0

    def run(self):
        try:
            if self._purge and IPVANISH_DIR.exists():
                self.status.emit("Removing old IPVanish configs…")
                shutil.rmtree(IPVANISH_DIR)

            IPVANISH_DIR.mkdir(parents=True, exist_ok=True)

            self.status.emit("Fetching config list…")
            links = self._fetch_links()

            if not links:
                self.error.emit("No download links found. Check your internet connection.")
                return

            total = len(links)
            self.status.emit(f"Downloading {total} config files…")
            self._completed = 0

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = {pool.submit(self._download_one, url): url for url in links}
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass  # Skip individual failures silently
                    with self._lock:
                        self._completed += 1
                        self.progress.emit(self._completed, total)

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    # ──── PRIVATE ──── #

    @staticmethod
    def _fetch_links() -> list[str]:
        resp = requests.get(DOWNLOAD_BASE, timeout=15)
        resp.raise_for_status()
        soup = Soup(resp.content, "html.parser")
        spans = soup.find_all("span", {"class": "name"})
        return [DOWNLOAD_BASE + s.text.strip() for s in spans]

    @staticmethod
    def _download_one(url: str):
        filename = url.split("/")[-1]
        dest = IPVANISH_DIR / filename
        if dest.exists():
            return  # Skip already-downloaded files
        content = requests.get(url, timeout=15).content
        dest.write_bytes(content)


class DownloadManager(QObject):
    """Spawns the DownloadWorker on a QThread."""
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread: QThread | None = None
        self._worker: DownloadWorker | None = None

    def start(self, purge_first: bool = False):
        if self._thread and self._thread.isRunning():
            return
        self._thread = QThread()
        self._worker = DownloadWorker(purge_first)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress)
        self._worker.status.connect(self.status)
        self._worker.finished.connect(self.finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self.error)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def configs_exist(self) -> bool:
        if not IPVANISH_DIR.exists():
            return False
        ovpn_files = [f for f in os.listdir(IPVANISH_DIR) if f.endswith(".ovpn")]
        return len(ovpn_files) > 10

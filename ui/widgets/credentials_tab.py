"""
ui/widgets/credentials_tab.py
IPVanish account credentials — embedded into Settings.
Styled consistently with the dashboard (flat, no card frame).
IPVanish-Client v2
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
)

CREDS_FILE = Path(__file__).parents[2] / "config" / "credentials"


class CredentialsTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_existing()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Username
        layout.addWidget(self._field_label("Username"))
        layout.addSpacing(6)
        self._user_field = QLineEdit()
        self._user_field.setPlaceholderText("your@email.com")
        layout.addWidget(self._user_field)
        layout.addSpacing(14)

        # Password
        layout.addWidget(self._field_label("Password"))
        layout.addSpacing(6)
        self._pass_field = QLineEdit()
        self._pass_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_field.setPlaceholderText("••••••••••••")
        layout.addWidget(self._pass_field)
        layout.addSpacing(16)

        # Buttons
        btn_row = QHBoxLayout()
        self._save_btn = QPushButton("Save Credentials")
        self._save_btn.clicked.connect(self._save)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addSpacing(10)

        # Feedback
        self._feedback = QLabel("")
        self._feedback.setObjectName("dashLocation")
        layout.addWidget(self._feedback)
        layout.addSpacing(12)

        # WireGuard hint (hidden by default — shown when a WG profile is selected)
        self._wg_hint = QLabel(
            "WireGuard profiles are self-contained — no credentials needed here."
        )
        self._wg_hint.setObjectName("dashDisclaimer")
        self._wg_hint.setWordWrap(True)
        self._wg_hint.setVisible(False)
        layout.addWidget(self._wg_hint)

        # Note
        note = QLabel(
            "Sudo/admin access is handled automatically via polkit.\n"
            "Your system password is never stored by this application."
        )
        note.setObjectName("dashDisclaimer")
        note.setWordWrap(True)
        layout.addWidget(note)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("dashCreditKey")
        return lbl

    def _load_existing(self):
        if CREDS_FILE.exists():
            lines = CREDS_FILE.read_text().splitlines()
            if len(lines) >= 2:
                self._user_field.setText(lines[0])
                self._pass_field.setText(lines[1])
                self._feedback.setText("✓  Credentials loaded from disk")

    def _save(self):
        user = self._user_field.text().strip()
        pwd  = self._pass_field.text()
        if not user or not pwd:
            self._feedback.setText("✗  Please enter both username and password.")
            return
        CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CREDS_FILE.write_text(f"{user}\n{pwd}\n")
        self._feedback.setText("✓  Credentials saved.")

    def _clear(self):
        self._user_field.clear()
        self._pass_field.clear()
        if CREDS_FILE.exists():
            CREDS_FILE.unlink()
        self._feedback.setText("Credentials cleared.")

    def set_wireguard_mode(self, is_wg: bool) -> None:
        """Show/hide the WireGuard hint based on the selected profile's protocol."""
        self._wg_hint.setVisible(is_wg)

    def has_credentials(self) -> bool:
        return (CREDS_FILE.exists() and
                len(CREDS_FILE.read_text().splitlines()) >= 2)

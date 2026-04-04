"""
PyQt5 update notification dialog for SignFlow.
"""

import sys
import webbrowser
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QApplication
)
from PyQt5.QtGui import QFont, QIcon

from update_checker import UpdateCheckResult


class UpdateDialog(QDialog):
    """
    Modal dialog for update notification.
    """

    def __init__(self, result: UpdateCheckResult, parent=None):
        super().__init__(parent)
        self.result = result
        self.download_url = result.download_url
        
        self._setup_ui()
        self._center_on_screen()

    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowTitle("SignFlow Update Available")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Update Available")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Version info
        info_text = (
            f"<b>Current Version:</b> {self.result.current_version}<br>"
            f"<b>Latest Version:</b> {self.result.latest_version}"
        )
        info_label = QLabel(info_text)
        layout.addWidget(info_label)

        # Release notes
        if self.result.release_notes:
            notes_label = QLabel("Release Notes:")
            notes_font = QFont()
            notes_font.setBold(True)
            notes_label.setFont(notes_font)
            layout.addWidget(notes_label)

            notes_text = QTextEdit()
            notes_text.setPlainText(self.result.release_notes)
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(120)
            layout.addWidget(notes_text)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        later_btn = QPushButton("Later")
        later_btn.clicked.connect(self.reject)
        button_layout.addWidget(later_btn)

        download_btn = QPushButton("Download")
        download_btn.setDefault(True)
        download_btn.clicked.connect(self._on_download_clicked)
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)

    def _center_on_screen(self):
        """Center dialog on screen."""
        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def _on_download_clicked(self):
        """Handle download button click."""
        if self.download_url:
            print(f"[UpdateDialog] Opening: {self.download_url}")
            webbrowser.open(self.download_url)
        self.accept()


def show_update_dialog(result: UpdateCheckResult, parent=None) -> bool:
    """
    Show update dialog and return True if user clicked Download.
    """
    dialog = UpdateDialog(result, parent)
    return dialog.exec_() == QDialog.Accepted


def test_update_dialog():
    """Test script for update dialog."""
    from update_checker import UpdateCheckResult
    
    app = QApplication(sys.argv)
    
    # Create mock result
    result = UpdateCheckResult(
        has_update=True,
        current_version="1.0.0",
        latest_version="1.1.0",
        download_url="https://github.com/example/SignFlow/releases/download/v1.1.0/SignFlow-mac.dmg",
        release_notes="Bug fixes and performance improvements\n- Fixed screen capture issue\n- Improved model loading speed"
    )
    
    print("[TEST] Showing update dialog...")
    accepted = show_update_dialog(result)
    print(f"[TEST] Dialog accepted: {accepted}")


if __name__ == "__main__":
    test_update_dialog()

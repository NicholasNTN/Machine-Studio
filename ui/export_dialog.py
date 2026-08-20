from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


def sanitize_windows_name(value: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "").strip()).rstrip(". ")
    return clean or "Machine_Export"


class ExportDialog(QDialog):
    """Review-only export surface; rendering starts only after acceptance."""
    def __init__(self, preview: QPixmap, sources, output_dir, resolution, codec, encoder, strip_metadata=True, parent=None):
        super().__init__(parent); self.setWindowTitle("Export — Machine Studio"); self.resize(1120, 720); self.setModal(True)
        root = QHBoxLayout(self)
        left = QVBoxLayout(); title = QLabel("Final Preview"); title.setObjectName("panelTitle"); left.addWidget(title)
        self.preview = QLabel(); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumSize(480, 360); self.preview.setStyleSheet("background:#05080d;border:1px solid #34465f;border-radius:10px;")
        if not preview.isNull(): self.preview.setPixmap(preview.scaled(540, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        left.addWidget(self.preview, 1); root.addLayout(left, 1)
        right = QVBoxLayout(); form = QFormLayout(); self.name = QLineEdit("Machine_Export"); form.addRow("Name", self.name)
        out_row = QHBoxLayout(); self.output_dir = QLineEdit(str(output_dir)); browse = QPushButton("Browse"); browse.clicked.connect(self._browse); out_row.addWidget(self.output_dir, 1); out_row.addWidget(browse); form.addRow("Export To", out_row); right.addLayout(form)
        self.tabs = QTabWidget(); right.addWidget(self.tabs, 1)
        video = QWidget(); vf = QFormLayout(video); self.resolution = QComboBox(); self.resolution.addItems(["720x1280 (HD - Nhanh)", "1080x1920 (Full HD)", "1080x1920 (Full HD 60FPS)", "1440x2560 (2K)", "2160x3840 (4K)", "1080x1440 (3:4)", "1920x1080 (YouTube)", "Original"]); self.resolution.setCurrentText(resolution)
        self.codec = QComboBox(); self.codec.addItems(["Auto", "H.264", "H.265", "AV1"]); self.codec.setCurrentText(codec)
        self.encoder = QComboBox(); self.encoder.addItems(["Auto (GPU)", "GPU", "CPU"]); self.encoder.setCurrentText(encoder)
        vf.addRow("Resolution", self.resolution); vf.addRow("Bit Rate / Quality", QLabel("Managed by the existing quality-safe export preset")); vf.addRow("Codec", self.codec); vf.addRow("Format", QLabel("MP4")); vf.addRow("Frame Rate", QLabel("Project / selected resolution")); self.tabs.addTab(video, "Xuất video")
        batch = QWidget(); bl = QVBoxLayout(batch); self.batch = QTableWidget(len(sources), 2); self.batch.setHorizontalHeaderLabels(["Source", "Output Name"])
        for row, source in enumerate(sources): self.batch.setItem(row, 0, QTableWidgetItem(Path(source).name)); self.batch.setItem(row, 1, QTableWidgetItem(f"{Path(source).stem}_MS"))
        bl.addWidget(self.batch); self.tabs.addTab(batch, "Hàng loạt")
        optimize = QWidget(); ol = QVBoxLayout(optimize); self.strip_metadata = QCheckBox("Optimize metadata and remove private file information"); self.strip_metadata.setChecked(strip_metadata); ol.addWidget(self.strip_metadata); ol.addStretch(1); self.tabs.addTab(optimize, "Tối ưu")
        capcut = QWidget(); cl = QVBoxLayout(capcut); cl.addWidget(QLabel("Export an MP4 + subtitle + narration package for CapCut.")); package = QPushButton("Export CapCut Package"); open_capcut = QPushButton("Open CapCut")
        if parent is not None and hasattr(parent, "capcut_package"): package.clicked.connect(parent.capcut_package)
        if parent is not None and hasattr(parent, "open_capcut"): open_capcut.clicked.connect(parent.open_capcut)
        cl.addWidget(package); cl.addWidget(open_capcut); cl.addStretch(1); self.tabs.addTab(capcut, "CapCut")
        self.summary = QLabel("Duration and estimated size are calculated by the existing render pipeline."); self.summary.setObjectName("hint"); right.addWidget(self.summary)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel); export = buttons.addButton("Export", QDialogButtonBox.AcceptRole); export.setObjectName("success"); buttons.rejected.connect(self.reject); buttons.accepted.connect(self._accept_clean); right.addWidget(buttons); root.addLayout(right, 1)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Export To", self.output_dir.text())
        if path: self.output_dir.setText(path)

    def _accept_clean(self):
        self.name.setText(sanitize_windows_name(self.name.text())); self.accept()

    def batch_names(self):
        return {self.batch.item(row, 0).text(): sanitize_windows_name(self.batch.item(row, 1).text()) for row in range(self.batch.rowCount())}

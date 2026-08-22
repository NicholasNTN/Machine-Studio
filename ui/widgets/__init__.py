"""Shared, focused widgets used by Machine Studio panels."""
from __future__ import annotations

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton, QVBoxLayout

from ..icons import icon


class MachineButton(QPushButton):
    def __init__(self, text="", *, variant="secondary", icon_name=None, parent=None):
        super().__init__(text, parent); self.setProperty("variant", variant); self.setCursor(Qt.PointingHandCursor)
        if icon_name: self.setIcon(icon(icon_name))
        self._base_text = text

    def setLoading(self, loading=True, text="Working…"):
        self.setEnabled(not loading); self.setText(text if loading else self._base_text)


class MachineIconButton(QToolButton):
    def __init__(self, icon_name, tooltip, parent=None):
        super().__init__(parent); self.setIcon(icon(icon_name)); self.setToolTip(tooltip)
        self.setAccessibleName(tooltip); self.setCursor(Qt.PointingHandCursor); self.setAutoRaise(True)


class MachineToolButton(QPushButton):
    def __init__(self, text, icon_name, parent=None):
        super().__init__("", parent); self.setObjectName("toolButton"); self._icon_name = icon_name; self.setIcon(icon(icon_name, size=20)); self.setIconSize(QSize(20, 20))
        self.setToolTip(text); self.setAccessibleName(text); self.setCheckable(True); self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(self._sync_icon)

    def _sync_icon(self, checked): self.setIcon(icon(self._icon_name, "accent" if checked else "textSecondary", 20))


class MachineNavButton(QPushButton):
    def __init__(self, text, icon_name, parent=None):
        super().__init__(text, parent); self.setObjectName("navButton"); self._icon_name = icon_name; self.setIcon(icon(icon_name, size=18))
        self.setCheckable(True); self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(self._sync_icon)

    def _sync_icon(self, checked): self.setIcon(icon(self._icon_name, "accent" if checked else "textSecondary", 18))


class MachineCard(QFrame):
    def __init__(self, parent=None): super().__init__(parent); self.setObjectName("machineCard")


class MachineSection(QFrame):
    def __init__(self, title, description="", parent=None):
        super().__init__(parent); self.setObjectName("machineCard"); layout = QVBoxLayout(self)
        heading = QLabel(title); heading.setObjectName("sectionTitle"); layout.addWidget(heading)
        if description:
            hint = QLabel(description); hint.setObjectName("panelDescription"); hint.setWordWrap(True); layout.addWidget(hint)
        self.body = QVBoxLayout(); layout.addLayout(self.body)


class MachineSearchField(QLineEdit):
    def __init__(self, placeholder="Search", parent=None):
        super().__init__(parent); self.setPlaceholderText(placeholder); self.setClearButtonEnabled(True)


class MachineBadge(QLabel):
    def __init__(self, text="", parent=None): super().__init__(text, parent); self.setObjectName("mediaDuration")


class MachineDivider(QFrame):
    def __init__(self, parent=None): super().__init__(parent); self.setFrameShape(QFrame.HLine); self.setObjectName("machineDivider")


class MachineEmptyState(QFrame):
    def __init__(self, title, description="", icon_name="folder", parent=None):
        super().__init__(parent); layout = QVBoxLayout(self); layout.setAlignment(Qt.AlignCenter)
        mark = QLabel(); mark.setPixmap(icon(icon_name).pixmap(28, 28)); mark.setAlignment(Qt.AlignCenter); layout.addWidget(mark)
        heading = QLabel(title); heading.setObjectName("emptyTitle"); heading.setAlignment(Qt.AlignCenter); layout.addWidget(heading)
        hint = QLabel(description); hint.setObjectName("hint"); hint.setWordWrap(True); hint.setAlignment(Qt.AlignCenter); layout.addWidget(hint)


class MachineToast(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("machineToast"); self.setAttribute(Qt.WA_TransparentForMouseEvents)
        row = QHBoxLayout(self); row.setContentsMargins(12, 8, 12, 8)
        self.label = QLabel(); row.addWidget(self.label); self.hide()

    def showMessage(self, message, timeout=3000):
        self.label.setText(str(message)); self.adjustSize(); self.show(); self.raise_()
        QTimer.singleShot(max(500, int(timeout)), self.hide)


class MachinePanelHeader(QFrame):
    def __init__(self, title, description="", parent=None):
        super().__init__(parent); self.setObjectName("panelHeader"); row = QHBoxLayout(self); row.setContentsMargins(0, 0, 0, 6)
        labels = QVBoxLayout(); heading = QLabel(title); heading.setObjectName("panelTitle"); labels.addWidget(heading)
        if description:
            hint = QLabel(description); hint.setObjectName("panelDescription"); labels.addWidget(hint)
        row.addLayout(labels); row.addStretch(1); self.actions = QHBoxLayout(); row.addLayout(self.actions)


class MachineToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("machineToolbar"); self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 4, 6, 4); self.layout.setSpacing(4)


class MachineToolbarGroup(QFrame):
    def __init__(self, label="", parent=None):
        super().__init__(parent); self.setObjectName("toolbarGroup"); row = QHBoxLayout(self)
        row.setContentsMargins(3, 0, 3, 0); row.setSpacing(2); self.layout = row
        if label:
            caption = QLabel(label); caption.setObjectName("toolbarLabel"); row.addWidget(caption)


class MachineSwitch(QCheckBox):
    pass

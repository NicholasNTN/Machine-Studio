from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def tokens() -> dict:
    path = Path(__file__).resolve().parents[1] / "design" / "tokens.json"
    return json.loads(path.read_text(encoding="utf-8"))


def application_stylesheet() -> str:
    t = tokens(); c = t["color"]; r = t["radius"]; ctl = t["control"]; typo = t["typography"]
    return f"""
    QMainWindow, QDialog, QWidget {{ background:{c['background']}; color:{c['textPrimary']}; font-family:'{typo['family']}'; font-size:{typo['body']}px; }}
    QToolTip {{ background:{c['surfaceRaised']}; color:{c['textPrimary']}; border:1px solid {c['borderStrong']}; padding:5px 7px; }}
    QFrame#topBar {{ background:{c['surface']}; border:1px solid {c['border']}; border-radius:{r['large']}px; }}
    QLabel#brandLabel {{ color:{c['textPrimary']}; font-size:14px; font-weight:700; padding:0 10px; }}
    QLabel#brandMark {{ color:{c['accent']}; font-size:15px; font-weight:800; }}
    QLabel#projectStatus, QLabel#hint, QLabel#panelDescription {{ color:{c['textMuted']}; font-size:{typo['caption']}px; }}
    QLabel#panelTitle {{ color:{c['textPrimary']}; font-size:{typo['heading']}px; font-weight:700; }}
    QLabel#sectionTitle, QLabel#inspectorHeading {{ color:{c['textSecondary']}; font-weight:650; }}
    QLabel#emptyIcon {{ color:{c['borderStrong']}; font-size:28px; }}
    QLabel#emptyTitle {{ color:{c['textSecondary']}; font-size:13px; font-weight:650; }}
    QFrame#leftWorkspace, QFrame#inspectorPanel, QWidget#toolPage, QFrame#machineCard {{ background:{c['surface']}; border:1px solid {c['border']}; border-radius:{r['large']}px; }}
    QFrame#toolNav {{ background:{c['background']}; border-right:1px solid {c['border']}; }}
    QPushButton, QToolButton {{ min-height:{ctl['compactHeight']}px; background:{c['surfaceRaised']}; color:{c['textPrimary']}; border:1px solid {c['border']}; border-radius:{r['medium']}px; padding:2px 10px; font-weight:600; }}
    QPushButton:hover, QToolButton:hover {{ background:{c['surfaceHover']}; border-color:{c['borderStrong']}; }}
    QPushButton:pressed, QToolButton:pressed {{ background:{c['surfaceSelected']}; }}
    QPushButton:focus, QToolButton:focus {{ border:1px solid {c['accent']}; }}
    QPushButton:disabled, QToolButton:disabled {{ color:{c['textMuted']}; background:{c['surface']}; border-color:{c['border']}; }}
    QPushButton[variant="primary"], QPushButton#topExport, QPushButton#success {{ background:{c['accent']}; color:#FFFFFF; border-color:{c['accent']}; }}
    QPushButton[variant="primary"]:hover, QPushButton#topExport:hover, QPushButton#success:hover {{ background:{c['accentHover']}; border-color:{c['accentHover']}; }}
    QPushButton[variant="danger"], QPushButton#danger, QPushButton#dangerSmall {{ background:{c['danger']}; color:#FFFFFF; border-color:{c['danger']}; }}
    QPushButton[variant="ghost"], QPushButton#navButton, QPushButton#toolButton {{ background:transparent; border-color:transparent; color:{c['textSecondary']}; }}
    QPushButton#navButton {{ padding:2px 12px; }}
    QPushButton#navButton:hover, QPushButton#toolButton:hover {{ background:{c['surfaceHover']}; color:{c['textPrimary']}; }}
    QPushButton#navButton:checked, QPushButton#toolButton:checked {{ background:{c['surfaceSelected']}; color:{c['accent']}; border-color:{c['border']}; }}
    QPushButton#toolButton {{ font-size:10px; padding:3px; text-align:center; }}
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QFontComboBox, QListWidget, QTableWidget {{ background:{c['surface']}; color:{c['textPrimary']}; border:1px solid {c['borderStrong']}; border-radius:{r['medium']}px; padding:5px 8px; selection-background-color:{c['surfaceSelected']}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QFontComboBox {{ min-height:20px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QFontComboBox:hover {{ border-color:{c['textMuted']}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QFontComboBox:focus {{ border-color:{c['accent']}; }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ color:{c['textMuted']}; background:{c['surfaceRaised']}; }}
    QGroupBox {{ border:1px solid {c['border']}; border-radius:{r['medium']}px; margin-top:12px; padding:12px 8px 8px; font-weight:650; }}
    QGroupBox::title {{ color:{c['textSecondary']}; subcontrol-origin:margin; left:9px; padding:0 4px; }}
    QTabWidget::pane {{ border:1px solid {c['border']}; border-radius:{r['medium']}px; }}
    QTabBar::tab {{ background:transparent; color:{c['textSecondary']}; padding:8px 13px; border-bottom:2px solid transparent; }}
    QTabBar::tab:hover {{ color:{c['textPrimary']}; background:{c['surfaceHover']}; }}
    QTabBar::tab:selected {{ color:{c['textPrimary']}; border-bottom-color:{c['accent']}; }}
    QWidget#sequenceTabButton {{ background:transparent; border:1px solid transparent; border-radius:{r['medium']}px; }}
    QWidget#sequenceTabButton:hover {{ background:{c['surfaceHover']}; }}
    QWidget#sequenceTabButton[active="true"] {{ background:{c['surfaceRaised']}; border-color:{c['border']}; border-bottom:2px solid {c['accent']}; }}
    QToolButton#sequenceTabClose, QToolButton#sequenceTabPlus {{ min-height:0; background:transparent; border:0; padding:0; color:{c['textSecondary']}; }}
    QToolButton#sequenceTabClose:hover {{ background:{c['danger']}; color:#FFFFFF; border-radius:8px; }}
    QToolButton#sequenceTabPlus:hover {{ background:{c['surfaceHover']}; color:{c['accent']}; }}
    QFrame#mediaDropArea {{ background:{c['background']}; border:1px dashed {c['borderStrong']}; border-radius:{r['large']}px; }}
    QFrame#mediaDropArea:hover {{ border-color:{c['accent']}; background:{c['surfaceRaised']}; }}
    QFrame#mediaCard {{ background:{c['surfaceRaised']}; border:1px solid {c['border']}; border-radius:{r['medium']}px; }}
    QFrame#mediaCard:hover {{ background:{c['surfaceHover']}; border-color:{c['borderStrong']}; }}
    QLabel#mediaThumb {{ background:{c['preview']}; border-radius:{r['small']}px; color:{c['textMuted']}; }}
    QLabel#mediaDuration {{ background:rgba(11,14,19,210); color:{c['textPrimary']}; border-radius:3px; padding:1px 4px; font-size:10px; }}
    QPushButton#cardAdd {{ min-height:26px; max-height:26px; min-width:26px; max-width:26px; padding:0; border-radius:6px; }}
    QFrame#previewFrame, QLabel#exportPreview {{ background:{c['preview']}; border:1px solid {c['border']}; border-radius:{r['large']}px; }}
    QFrame#audioStrip {{ background:{c['surface']}; border-top:1px solid {c['border']}; }}
    QSplitter::handle {{ background:{c['border']}; }} QSplitter::handle:hover {{ background:{c['accent']}; }}
    QScrollArea {{ border:0; background:transparent; }}
    QScrollBar:vertical {{ background:transparent; width:10px; }} QScrollBar::handle:vertical {{ background:{c['borderStrong']}; min-height:28px; border-radius:5px; }}
    QScrollBar:horizontal {{ background:transparent; height:10px; }} QScrollBar::handle:horizontal {{ background:{c['borderStrong']}; min-width:28px; border-radius:5px; }}
    QHeaderView::section {{ background:{c['surfaceRaised']}; color:{c['textSecondary']}; padding:7px; border:0; border-right:1px solid {c['border']}; }}
    QProgressBar {{ background:{c['surfaceRaised']}; border:0; border-radius:3px; text-align:center; }} QProgressBar::chunk {{ background:{c['accent']}; border-radius:3px; }}
    QPlainTextEdit#blackLog {{ background:{c['preview']}; color:{c['success']}; }}
    QLabel#readyText {{ color:{c['success']}; font-weight:700; }} QLabel#warnText {{ color:{c['warning']}; font-weight:700; }}
    QMenu {{ background:{c['surfaceRaised']}; border:1px solid {c['borderStrong']}; padding:5px; }} QMenu::item {{ padding:6px 24px 6px 10px; border-radius:4px; }} QMenu::item:selected {{ background:{c['surfaceSelected']}; }}
    QFrame#machineToast {{ background:{c['surfaceSelected']}; border:1px solid {c['borderStrong']}; border-left:3px solid {c['success']}; border-radius:{r['medium']}px; }}
    """


def apply_theme(widget) -> None:
    widget.setStyleSheet(application_stylesheet())

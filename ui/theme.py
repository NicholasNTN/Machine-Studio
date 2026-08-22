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
    QToolTip {{ background:#171F29; color:{c['textPrimary']}; border:1px solid #344254; border-radius:5px; padding:6px; }}
    QFrame#topBar {{ background:{c['topBar']}; border:0; border-bottom:1px solid #242E3A; border-radius:{r['large']}px; }}
    QLabel#brandLabel {{ color:{c['textPrimary']}; font-size:13px; font-weight:650; padding:0 14px 0 4px; }}
    QLabel#brandMark {{ color:{c['accent']}; font-size:15px; font-weight:800; }}
    QLabel#savedDot {{ color:{c['success']}; font-size:9px; padding-left:8px; }}
    QLabel#projectStatus, QLabel#hint, QLabel#panelDescription {{ color:{c['textMuted']}; font-size:{typo['caption']}px; }}
    QLabel#panelTitle {{ color:{c['textPrimary']}; font-size:{typo['heading']}px; font-weight:700; }}
    QLabel#sectionTitle, QLabel#inspectorHeading {{ min-height:28px; background:{c['surfaceRaised']}; color:{c['textSecondary']}; border-bottom:1px solid {c['border']}; font-size:11px; font-weight:650; padding-left:8px; }}
    QLabel#emptyIcon {{ color:{c['borderStrong']}; font-size:28px; }}
    QLabel#emptyTitle {{ color:{c['textSecondary']}; font-size:13px; font-weight:650; }}
    QFrame#leftWorkspace, QWidget#toolPage {{ background:{c['surface']}; border:1px solid {c['border']}; border-radius:{r['large']}px; }}
    QFrame#inspectorPanel {{ background:{c['inspector']}; border:0; border-radius:{r['large']}px; }}
    QFrame#machineCard {{ background:{c['surfaceRaised']}; border:0; border-radius:{r['card']}px; }}
    QFrame#machineSection {{ background:{c['inspector']}; border:0; border-radius:{r['medium']}px; }}
    QFrame#toolNav {{ background:{c['toolRail']}; border-right:1px solid #26313D; }}
    QPushButton, QToolButton {{ min-height:{ctl['compactHeight']}px; background:{c['surfaceRaised']}; color:#D4DAE2; border:1px solid #2C3948; border-radius:{r['button']}px; padding:1px 12px; font-weight:600; }}
    QPushButton:hover, QToolButton:hover {{ background:{c['surfaceHover']}; border-color:#3B4C60; }}
    QPushButton:pressed, QToolButton:pressed {{ background:#111820; }}
    QPushButton:checked, QToolButton:checked {{ background:{c['surfaceSelected']}; color:#FFFFFF; border-color:{c['accent']}; }}
    QPushButton:focus, QToolButton:focus {{ border:1px solid {c['accent']}; }}
    QPushButton:disabled, QToolButton:disabled {{ color:{c['disabledText']}; background:{c['disabledSurface']}; border-color:{c['disabledBorder']}; }}
    QPushButton[variant="primary"], QPushButton#topExport, QPushButton#success, QPushButton#hero, QPushButton#greenSmall {{ background:{c['accent']}; color:#FFFFFF; border-color:#5A98FF; }}
    QPushButton[variant="primary"]:hover, QPushButton#topExport:hover, QPushButton#success:hover, QPushButton#hero:hover, QPushButton#greenSmall:hover {{ background:{c['accentHover']}; border-color:{c['accentHover']}; }}
    QPushButton[variant="primary"]:pressed, QPushButton#topExport:pressed, QPushButton#success:pressed, QPushButton#hero:pressed, QPushButton#greenSmall:pressed {{ background:{c['accentPressed']}; }}
    QPushButton[variant="primary"]:disabled, QPushButton#topExport:disabled, QPushButton#success:disabled, QPushButton#hero:disabled, QPushButton#greenSmall:disabled {{ background:{c['disabledSurface']}; color:#667487; border-color:{c['disabledBorder']}; }}
    QPushButton[variant="danger"], QPushButton#danger, QPushButton#dangerSmall {{ background:{c['dangerSurface']}; color:#FF7884; border-color:{c['dangerBorder']}; }}
    QPushButton[variant="danger"]:hover, QPushButton#danger:hover, QPushButton#dangerSmall:hover {{ background:{c['dangerSurfaceHover']}; border-color:{c['danger']}; }}
    QPushButton[variant="ghost"], QPushButton[variant="toolbar"], QToolButton[variant="ghost"], QPushButton#navButton, QPushButton#toolButton {{ background:transparent; border-color:transparent; color:#9CA8B7; }}
    QPushButton[variant="ghost"]:hover, QPushButton[variant="toolbar"]:hover, QToolButton[variant="ghost"]:hover {{ background:#1A2430; color:{c['textPrimary']}; }}
    QPushButton[variant="ghost"]:pressed, QPushButton[variant="toolbar"]:pressed, QToolButton[variant="ghost"]:pressed {{ background:{c['surfaceSelected']}; }}
    QPushButton[variant="ghost"]:checked, QPushButton[variant="toolbar"]:checked, QToolButton[variant="ghost"]:checked {{ background:{c['surfaceSelected']}; color:{c['accent']}; border-color:transparent; }}
    QPushButton#navButton {{ padding:2px 12px; border-bottom:2px solid transparent; }}
    QPushButton#navButton:hover {{ background:#161E28; color:{c['textPrimary']}; }} QPushButton#toolButton:hover {{ background:#151E28; color:{c['textPrimary']}; }}
    QPushButton#navButton:checked {{ background:#1C2938; color:{c['textPrimary']}; border-bottom-color:{c['accent']}; }}
    QPushButton#toolButton:checked {{ background:#182432; color:{c['accent']}; border-left:3px solid {c['accent']}; }}
    QPushButton#toolButton {{ padding:3px; }}
    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QFontComboBox, QListWidget, QTableWidget {{ background:{c['input']}; color:#E7EBF0; border:1px solid {c['inputBorder']}; border-radius:7px; padding:4px 8px; selection-background-color:{c['surfaceSelected']}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QFontComboBox {{ min-height:22px; }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QFontComboBox:hover {{ border-color:{c['inputHoverBorder']}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QFontComboBox:focus {{ border-color:{c['accent']}; }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ color:{c['disabledText']}; background:{c['surface']}; border-color:{c['disabledBorder']}; }}
    QGroupBox {{ background:{c['surfaceRaised']}; border:0; border-radius:{r['large']}px; margin-top:12px; padding:12px 8px 8px; font-weight:650; }}
    QGroupBox::title {{ color:{c['textSecondary']}; subcontrol-origin:margin; left:9px; padding:0 4px; }}
    QTabWidget::pane {{ border:1px solid {c['border']}; border-radius:{r['medium']}px; }}
    QTabBar::tab {{ background:transparent; color:{c['textSecondary']}; padding:8px 13px; border-bottom:2px solid transparent; }}
    QTabBar::tab:hover {{ color:{c['textPrimary']}; background:{c['surfaceHover']}; }}
    QTabBar::tab:selected {{ color:{c['textPrimary']}; border-bottom-color:{c['accent']}; }}
    QWidget#sequenceTabButton {{ background:transparent; border:1px solid transparent; border-radius:{r['small']}px; padding:0 2px; color:#A5AFBC; }}
    QWidget#sequenceTabButton:hover {{ background:#151E28; }}
    QWidget#sequenceTabButton[active="true"] {{ background:#182432; color:#FFFFFF; border-color:transparent; border-bottom:2px solid {c['accent']}; }}
    QToolButton#sequenceTabClose, QToolButton#sequenceTabPlus {{ min-height:0; background:transparent; border:0; padding:0; color:{c['textSecondary']}; }}
    QToolButton#sequenceTabClose:hover {{ background:{c['dangerSurfaceHover']}; color:#FFFFFF; border-radius:{r['small']}px; }}
    QToolButton#sequenceTabPlus:hover {{ background:{c['surfaceHover']}; color:{c['accent']}; }}
    QFrame#mediaDropArea {{ background:{c['background']}; border:1px dashed {c['borderStrong']}; border-radius:{r['large']}px; }}
    QFrame#mediaDropArea:hover {{ border-color:{c['accent']}; background:{c['surfaceRaised']}; }}
    QFrame#mediaCard {{ background:{c['mediaCard']}; border:1px solid #273443; border-radius:{r['medium']}px; }}
    QFrame#mediaCard:hover {{ background:{c['mediaCardHover']}; border-color:{c['borderStrong']}; }}
    QFrame#mediaCard[selected="true"] {{ background:{c['mediaCardSelected']}; border:1px solid {c['accent']}; border-left:3px solid {c['accent']}; }}
    QLabel#mediaThumb {{ background:#070A0E; border-radius:{r['small']}px; color:{c['textMuted']}; }}
    QLabel#mediaName {{ color:{c['textPrimary']}; font-weight:600; }} QLabel#mediaType, QLabel#mediaMetadata {{ color:{c['textMuted']}; font-size:9px; font-weight:500; }}
    QLabel#mediaDuration {{ background:#0C1218; color:#A8B3C1; border-radius:{r['tiny']}px; padding:1px 4px; font-size:9px; font-weight:500; }}
    QPushButton#cardAdd, QToolButton#cardAdd {{ min-height:26px; max-height:26px; min-width:26px; max-width:26px; padding:0; border-radius:{r['small']}px; }}
    QFrame#previewFrame, QLabel#exportPreview {{ background:{c['preview']}; border:1px solid {c['border']}; border-radius:{r['large']}px; }}
    QFrame#machineToolbar {{ min-height:36px; max-height:38px; background:{c['input']}; border:1px solid {c['border']}; border-radius:{r['medium']}px; }}
    QGroupBox#timelinePanel, QWidget#timelineSurface {{ background:{c['timeline']}; border:0; border-top:1px solid #293543; border-radius:{r['large']}px; margin-top:0; padding:0; }}
    QFrame#toolbarGroup {{ background:{c['surfaceRaised']}; border:0; border-radius:6px; }}
    QLabel#toolbarLabel {{ color:{c['textMuted']}; font-size:9px; padding:0 4px; }}
    QToolButton#previewPlay {{ min-width:34px; max-width:34px; min-height:34px; max-height:34px; background:{c['accent']}; border-color:{c['accent']}; border-radius:17px; padding:0; }}
    QToolButton#previewPlay:hover {{ background:{c['accentHover']}; }}
    QToolButton#dangerIcon {{ background:{c['dangerSurface']}; border-color:{c['dangerBorder']}; color:#FF7884; }} QToolButton#dangerIcon:hover {{ background:{c['dangerSurfaceHover']}; border-color:{c['danger']}; color:{c['dangerHover']}; }}
    QFrame#audioStrip {{ background:{c['surface']}; border-top:1px solid {c['border']}; }}
    QSplitter::handle {{ background:{c['border']}; }} QSplitter::handle:hover {{ background:{c['accent']}; }}
    QScrollArea {{ border:0; background:transparent; }}
    QScrollBar:vertical {{ background:transparent; width:10px; }} QScrollBar::handle:vertical {{ background:{c['borderStrong']}; min-height:28px; border-radius:5px; }}
    QScrollBar:horizontal {{ background:transparent; height:10px; }} QScrollBar::handle:horizontal {{ background:{c['borderStrong']}; min-width:28px; border-radius:5px; }}
    QHeaderView::section {{ background:{c['surfaceRaised']}; color:{c['textSecondary']}; padding:7px; border:0; border-right:1px solid {c['border']}; }}
    QProgressBar {{ background:{c['surfaceRaised']}; border:0; border-radius:{r['tiny']}px; text-align:center; }} QProgressBar::chunk {{ background:{c['accent']}; border-radius:{r['tiny']}px; }}
    QCheckBox {{ spacing:7px; color:{c['textSecondary']}; }} QCheckBox::indicator {{ width:30px; height:16px; border-radius:8px; background:#26313D; }}
    QCheckBox::indicator:checked {{ background:{c['accent']}; }} QCheckBox::indicator:disabled {{ background:{c['disabledBorder']}; }}
    QSlider::groove:horizontal {{ height:4px; background:#26313D; border-radius:2px; }} QSlider::sub-page:horizontal {{ background:{c['accent']}; border-radius:2px; }} QSlider::handle:horizontal {{ width:12px; margin:-4px 0; background:{c['textPrimary']}; border:1px solid {c['accent']}; border-radius:6px; }}
    QSlider::groove:vertical {{ width:4px; background:#26313D; border-radius:2px; }} QSlider::sub-page:vertical {{ background:{c['accent']}; border-radius:2px; }} QSlider::handle:vertical {{ height:12px; margin:0 -4px; background:{c['textPrimary']}; border:1px solid {c['accent']}; border-radius:6px; }}
    QPlainTextEdit#blackLog {{ background:{c['preview']}; color:{c['success']}; }}
    QLabel#readyText {{ color:{c['success']}; font-weight:700; }} QLabel#warnText {{ color:{c['warning']}; font-weight:700; }}
    QMenu {{ background:{c['surfaceRaised']}; border:1px solid {c['borderStrong']}; padding:5px; }} QMenu::item {{ padding:6px 24px 6px 10px; border-radius:4px; }} QMenu::item:selected {{ background:{c['surfaceSelected']}; }}
    QFrame#machineToast {{ background:{c['surfaceElevated']}; border:1px solid {c['borderStrong']}; border-left:3px solid {c['success']}; border-radius:{r['card']}px; }}
    QStatusBar {{ min-height:22px; max-height:22px; background:{c['surface']}; color:{c['textMuted']}; border-top:1px solid {c['border']}; }}
    QMainWindow#projectHub {{ background:{c['background']}; }}
    QLabel#hubBrand {{ color:{c['textPrimary']}; font-size:13px; font-weight:700; }}
    QLabel#hubTitle {{ color:{c['textPrimary']}; font-size:24px; font-weight:700; }}
    QLabel#hubSubtitle {{ color:{c['textMuted']}; font-size:11px; }}
    QLabel#hubSectionTitle {{ color:{c['textPrimary']}; font-size:14px; font-weight:650; }}
    QPushButton#projectHero {{ background:{c['accent']}; color:#FFFFFF; border:1px solid #5A98FF; border-radius:{r['large']}px; font-size:14px; font-weight:700; text-align:left; padding-left:20px; }}
    QPushButton#projectHero:hover {{ background:{c['accentHover']}; }} QPushButton#projectHero:pressed {{ background:{c['accentPressed']}; }}
    QFrame#projectCard {{ background:{c['surfaceRaised']}; border:1px solid {c['border']}; border-radius:{r['card']}px; }}
    QFrame#projectCard:hover {{ background:{c['surfaceHover']}; border-color:{c['borderStrong']}; }}
    QFrame#projectCard[selected="true"] {{ background:{c['surfaceSelected']}; border:1px solid {c['accent']}; }}
    QLabel#projectThumbnail {{ background:{c['preview']}; border-radius:{r['medium']}px; color:{c['textMuted']}; }}
    QLabel#projectName {{ color:{c['textPrimary']}; font-size:12px; font-weight:650; }}
    QLabel#projectMeta {{ color:{c['textMuted']}; font-size:9px; }}
    """


def apply_theme(widget) -> None:
    widget.setStyleSheet(application_stylesheet())

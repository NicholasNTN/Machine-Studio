from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFontComboBox, QFormLayout, QFrame, QLabel, QLineEdit, QScrollArea, QSpinBox, QStackedWidget, QTextEdit, QVBoxLayout, QWidget


class InspectorPanel(QFrame):
    """Selection-driven inspector; controls edit the canonical selected object."""
    propertyChanged = Signal(str, object)
    KINDS = ("video",)

    def __init__(self, selection_manager=None, parent=None):
        super().__init__(parent); self.setObjectName("inspectorPanel"); self.setMinimumWidth(280); self._loading = False; self._controls = {}
        root = QVBoxLayout(self); root.setContentsMargins(10, 10, 10, 10)
        title = QLabel("Inspector"); title.setObjectName("panelTitle"); root.addWidget(title)
        self.stack = QStackedWidget(); root.addWidget(self.stack, 1); self.empty_page = self._empty_page(); self.stack.addWidget(self.empty_page); self.pages = {}
        for kind in self.KINDS:
            page = self._make_page(kind); self.pages[kind] = page; self.stack.addWidget(page)
        self._disable_unavailable_controls()
        if selection_manager is not None: selection_manager.selectionChanged.connect(self.set_selection)

    def _disable_unavailable_controls(self):
        unavailable = {
            "audio": ("fade_in", "fade_out"),
            "text": ("bold", "italic", "underline", "alignment", "scale", "rotation", "stroke_width", "stroke_color", "background", "shadow", "shadow_blur", "shadow_x", "shadow_y", "character_spacing", "line_spacing"),
            "subtitle": ("underline", "alignment", "scale", "rotation", "opacity", "shadow_blur", "shadow_x", "shadow_y", "character_spacing", "line_spacing"),
        }
        for kind, keys in unavailable.items():
            for key in keys:
                widget = self._controls.get((kind, key))
                if widget is not None:
                    widget.setEnabled(False)
                    widget.setToolTip("Coming next — not yet supported by Preview and export")
                    widget.setStatusTip("Coming next")

    def _empty_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.addStretch(1)
        icon = QLabel("◇"); icon.setObjectName("emptyIcon"); icon.setAlignment(Qt.AlignCenter); layout.addWidget(icon)
        label = QLabel("Select an item to edit"); label.setObjectName("emptyTitle"); label.setAlignment(Qt.AlignCenter); layout.addWidget(label)
        hint = QLabel("Choose a clip, text, subtitle, blur, or image in the preview or timeline."); hint.setObjectName("hint"); hint.setWordWrap(True); hint.setAlignment(Qt.AlignCenter); layout.addWidget(hint); layout.addStretch(2); return page

    def _make_page(self, kind):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); body = QWidget(); form = QFormLayout(body)
        heading = QLabel("Image / Logo" if kind in ("image", "logo") else kind.title()); heading.setObjectName("inspectorHeading"); form.addRow(heading)
        if kind in ("audio", "text", "subtitle"):
            notice = QLabel("Disabled controls are Coming next and do not affect the project.")
            notice.setObjectName("hint"); notice.setWordWrap(True); form.addRow(notice)
        if kind in ("text", "subtitle"):
            content = QTextEdit(); content.setMaximumHeight(80); self._bind(kind, "text", content, "textChanged", lambda w: w.toPlainText()); form.addRow("Content", content)
            font = QFontComboBox(); self._bind(kind, "font_name", font, "currentFontChanged", lambda w: w.currentFont().family()); form.addRow("Font", font)
            self._spin(form, kind, "font_size", "Font size", 8, 240, 48)
            for key, label in (("bold", "Bold"), ("italic", "Italic"), ("underline", "Underline")): self._check(form, kind, key, label)
            self._line(form, kind, "color", "Color", "#FFFFFF")
            align = QComboBox(); align.addItems(["Left", "Center", "Right"]); self._bind(kind, "alignment", align, "currentTextChanged", lambda w: w.currentText().lower()); form.addRow("Alignment", align)
            for args in (("stroke_width", "Stroke width", 0, 20, 0), ("shadow_blur", "Shadow blur", 0, 50, 0), ("shadow_x", "Shadow X", -100, 100, 0), ("shadow_y", "Shadow Y", -100, 100, 0), ("character_spacing", "Character spacing", -20, 100, 0), ("line_spacing", "Line spacing", 50, 300, 100)): self._spin(form, kind, *args)
            self._line(form, kind, "stroke_color", "Stroke color", "#000000"); self._line(form, kind, "background", "Background", "transparent"); self._check(form, kind, "shadow", "Shadow")
        if kind in ("text", "subtitle", "image", "logo"):
            for args in (("x", "Position X", -200, 200, 50), ("y", "Position Y", -200, 200, 50), ("scale", "Scale", 1, 500, 100), ("rotation", "Rotation", -360, 360, 0), ("opacity", "Opacity", 0, 100, 100)): self._double(form, kind, *args)
        if kind in ("video", "audio"):
            self._double(form, kind, "volume", "Volume", 0, 200, 100); self._check(form, kind, "muted", "Mute")
        if kind == "audio":
            self._double(form, kind, "fade_in", "Fade in", 0, 60, 0); self._double(form, kind, "fade_out", "Fade out", 0, 60, 0)
        if kind == "blur":
            self._double(form, kind, "strength", "Strength", 0, 100, 20); self._double(form, kind, "opacity", "Opacity", 0, 100, 20)
        scroll.setWidget(body); return scroll

    def _bind(self, kind, key, widget, signal_name, getter):
        self._controls[(kind, key)] = widget
        getattr(widget, signal_name).connect(lambda *_, k=key, w=widget, g=getter: None if self._loading else self.propertyChanged.emit(k, g(w)))

    def _spin(self, form, kind, key, label, low, high, value):
        widget = QSpinBox(); widget.setRange(low, high); widget.setValue(value); self._bind(kind, key, widget, "valueChanged", lambda w: w.value()); form.addRow(label, widget)

    def _double(self, form, kind, key, label, low, high, value):
        widget = QDoubleSpinBox(); widget.setRange(low, high); widget.setValue(value); widget.setDecimals(2); self._bind(kind, key, widget, "valueChanged", lambda w: w.value()); form.addRow(label, widget)

    def _check(self, form, kind, key, label):
        widget = QCheckBox(); self._bind(kind, key, widget, "toggled", lambda w: w.isChecked()); form.addRow(label, widget)

    def _line(self, form, kind, key, label, value):
        widget = QLineEdit(value); self._bind(kind, key, widget, "textChanged", lambda w: w.text()); form.addRow(label, widget)

    def set_selection(self, selection):
        if selection is None: self.stack.setCurrentWidget(self.empty_page); return
        kind = selection.kind
        if kind == "editor_layer": kind = "text"
        self.stack.setCurrentWidget(self.pages.get(kind, self.empty_page))

    def load_properties(self, kind, values):
        self._loading = True
        try:
            for (control_kind, key), widget in self._controls.items():
                if control_kind != kind or key not in values: continue
                value = values[key]
                if isinstance(widget, QTextEdit): widget.setPlainText(str(value))
                elif isinstance(widget, QFontComboBox): widget.setCurrentText(str(value))
                elif isinstance(widget, QComboBox): widget.setCurrentText(str(value).title())
                elif isinstance(widget, QCheckBox): widget.setChecked(bool(value))
                elif isinstance(widget, QSpinBox): widget.setValue(int(value))
                elif isinstance(widget, QDoubleSpinBox): widget.setValue(float(value))
                elif isinstance(widget, QLineEdit): widget.setText(str(value))
        finally: self._loading = False

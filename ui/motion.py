from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect

from .theme import tokens


def fade_in(widget, duration=None):
    """Run a cheap, one-shot opacity transition and retain it on the widget."""
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget); widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(int(duration or tokens()["motion"]["panel"]))
    animation.setStartValue(0.0); animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    widget._machine_fade_animation = animation
    animation.start()
    return animation

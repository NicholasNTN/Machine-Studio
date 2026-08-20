from __future__ import annotations


class LayerManager:
    def __init__(self, layers: list[dict] | None = None):
        self.layers = layers if layers is not None else []

    def find(self, layer_id: str) -> dict | None:
        return next((item for item in self.layers if item.get("id") == layer_id), None)

    def add(self, layer: dict) -> dict:
        if not layer.get("id"):
            raise ValueError("Layer requires an id")
        self.layers.append(layer)
        return layer

    def remove(self, layer_id: str) -> dict | None:
        layer = self.find(layer_id)
        if layer is not None:
            self.layers.remove(layer)
        return layer

    def active_at(self, seconds: float) -> list[dict]:
        from core.editor_engine import layer_active
        return [layer for layer in self.layers if layer_active(layer, seconds)]

CANONICAL_LAYER_ORDER = (
    "canvas_background", "base_video", "overlay_video", "sticker", "blur",
    "overlay_text", "subtitle", "logo",
)


def layer_sort_key(layer):
    kind = "overlay_video" if layer.get("type") == "video" else "sticker" if layer.get("type") == "image" else str(layer.get("type", "overlay_text"))
    try: return CANONICAL_LAYER_ORDER.index(kind)
    except ValueError: return len(CANONICAL_LAYER_ORDER)

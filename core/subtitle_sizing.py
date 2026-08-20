from __future__ import annotations


def canonical_font_size(value: int | float) -> int:
    """Return the stored project font size without output-dependent scaling."""
    return max(8, min(240, int(round(float(value or 0)))))


def preview_font_pixels(canonical_size: int | float, viewport_height: int | float, reference_height: int | float = 1920) -> int:
    """Scale only Qt drawing to its viewport; never mutate the stored size."""
    size = canonical_font_size(canonical_size)
    scale = max(0.01, float(viewport_height) / max(1.0, float(reference_height)))
    return max(1, int(round(size * scale)))


def ass_font_size(canonical_size: int | float) -> int:
    """ASS PlayRes matches output size, so the canonical value is written 1:1."""
    return canonical_font_size(canonical_size)

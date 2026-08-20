from __future__ import annotations


def canonical_font_size(value: int | float) -> int:
    """Return the stored project font size without output-dependent scaling."""
    return max(8, min(240, int(round(float(value or 0)))))


def preview_font_pixels(canonical_size: int | float, viewport_width: int | float, viewport_height: int | float, project_width: int | float, project_height: int | float) -> int:
    """Scale from project-output coordinates into the fitted Qt viewport."""
    size = canonical_font_size(canonical_size)
    scale = max(0.01, min(
        float(viewport_width) / max(1.0, float(project_width)),
        float(viewport_height) / max(1.0, float(project_height)),
    ))
    return max(1, int(round(size * scale)))


def ass_font_size(canonical_size: int | float) -> int:
    """ASS PlayRes matches output size, so the canonical value is written 1:1."""
    return canonical_font_size(canonical_size)

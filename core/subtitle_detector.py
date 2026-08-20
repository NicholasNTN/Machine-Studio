from __future__ import annotations

from pathlib import Path
import math


class SubtitleDetectionError(RuntimeError):
    pass


def _fallback_zone():
    return {"x": 8.0, "y": 71.0, "w": 84.0, "h": 11.0, "auto": True}


def detect_source_subtitle_zone(video_path: str, samples: int = 7) -> dict:
    """Estimate the baked-in subtitle band using only local OpenCV analysis.

    The detector intentionally searches the lower half of the video and scores
    horizontal text-like edge bands. It returns percentages, then the user can
    drag/resize the AUTO zone in Live Preview.
    """
    path = Path(video_path)
    if not path.exists():
        raise SubtitleDetectionError(f"Không tìm thấy video: {path}")

    try:
        import cv2
        import numpy as np
    except Exception:
        return _fallback_zone()

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return _fallback_zone()

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0) or 30.0
    if frame_count <= 0:
        duration = float(cap.get(cv2.CAP_PROP_POS_MSEC) or 0) / 1000.0
        frame_count = max(1, round(duration * fps))

    # Avoid intro/outro frames; focus on the middle 85%.
    positions = []
    n = max(3, min(11, int(samples)))
    for i in range(n):
        frac = 0.08 + (0.84 * i / max(1, n - 1))
        positions.append(max(0, min(frame_count - 1, int(frame_count * frac))))

    boxes = []
    for frame_idx in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        h0, w0 = frame.shape[:2]
        if w0 <= 0 or h0 <= 0:
            continue
        scale = 720.0 / max(w0, 720)
        if scale < 0.999:
            frame = cv2.resize(frame, (round(w0 * scale), round(h0 * scale)))
        h, w = frame.shape[:2]

        # Source captions in social videos usually live between 48% and 94% H.
        y0 = int(h * 0.48)
        y1 = int(h * 0.95)
        roi = frame[y0:y1]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Text has strong horizontal/vertical local gradients. Gradient + adaptive
        # morphology is much less color-dependent than looking for white/yellow.
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(gx, gy)
        mag = cv2.convertScaleAbs(mag)
        mag = cv2.GaussianBlur(mag, (3, 3), 0)
        _, bw = cv2.threshold(mag, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)
        bw = cv2.dilate(bw, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 2)), iterations=1)

        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            if cw < w * 0.05 or ch < max(5, h * 0.008):
                continue
            if ch > roi.shape[0] * 0.32 or cw > w * 0.98:
                continue
            aspect = cw / max(1, ch)
            if aspect < 1.1:
                continue
            # Favor center-ish, wide text bands and lower rows.
            cx = x + cw / 2
            center_penalty = abs(cx - w / 2) / max(1, w / 2)
            score = cw * ch * (1.25 - min(1.0, center_penalty) * 0.45)
            candidates.append((score, x, y, cw, ch))

        if not candidates:
            continue
        candidates.sort(reverse=True)
        # Union up to a few nearby components around the strongest line.
        _, x, y, cw, ch = candidates[0]
        ux0, uy0, ux1, uy1 = x, y, x + cw, y + ch
        base_cy = y + ch / 2
        for _, x2, y2, w2, h2 in candidates[1:8]:
            cy2 = y2 + h2 / 2
            if abs(cy2 - base_cy) <= max(ch, h2) * 2.2:
                ux0 = min(ux0, x2); uy0 = min(uy0, y2)
                ux1 = max(ux1, x2 + w2); uy1 = max(uy1, y2 + h2)

        # Padding protects outlines/shadows.
        pad_x = max(8, int(w * 0.025))
        pad_y = max(5, int(h * 0.012))
        ux0 = max(0, ux0 - pad_x); ux1 = min(w, ux1 + pad_x)
        uy0 = max(0, uy0 - pad_y); uy1 = min(roi.shape[0], uy1 + pad_y)
        boxes.append((ux0 / w * 100, (uy0 + y0) / h * 100,
                      (ux1 - ux0) / w * 100, (uy1 - uy0) / h * 100))

    cap.release()
    if not boxes:
        return _fallback_zone()

    import statistics
    xs = [b[0] for b in boxes]
    ys = [b[1] for b in boxes]
    ws = [b[2] for b in boxes]
    hs = [b[3] for b in boxes]

    x = statistics.median(xs)
    y = statistics.median(ys)
    w = statistics.median(ws)
    h = statistics.median(hs)

    # Guardrails: source subtitle mask should not accidentally cover most video.
    # Normalize for a clean centered subtitle mask.
    w = max(36.0, min(90.0, w))
    h = max(5.5, min(16.0, h))
    x = (100.0 - w) / 2.0
    y = max(45.0, min(95.0 - h, y))
    return {
        "x": round(x, 1),
        "y": round(y, 1),
        "w": round(w, 1),
        "h": round(h, 1),
        "auto": True,
    }

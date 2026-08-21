# Editor preview/export parity

Canonical input ownership is `SequenceDocument.state` → `build_render_snapshot(sequence_id)`. Qt preview and FFmpeg use different renderers, but export no longer reads live widgets after capture.

Preview visual order: Canvas background → base video/transform → blur zones → logo → legacy overlay text → editor layers in list order → subtitle. Export order is Canvas/background/base → blur → logo → editor video → editor image → ASS legacy/manual text and subtitle. Mixed editor-layer types and legacy overlay text therefore do not preserve arbitrary overlap order; this is a known limitation rather than claimed parity.

| Feature | Preview | Export | Snapshot field / status |
|---|---:|---:|---|
| Clip trim/order | Yes | Yes | `clips`; timeline concat |
| Per-clip transform, Fit/Fill | Yes | Yes | `clips[].transform` |
| Canvas aspect ratio | Yes | Yes | `output.aspect_ratio`; export dimensions derived from selected resolution |
| Canvas Blur Video | Yes | Yes | `canvas`; generated from each original clip before concat |
| Canvas Solid Color | Yes | Yes | `canvas` |
| Canvas Image | Yes | Yes | `canvas`; missing image is a validation error |
| Canvas None | Yes | Yes | `canvas`; black uncovered area is intentional |
| Speed | Yes | Yes | `effects.speed` |
| Blur zones / auto subtitle blur | Yes | Yes | `blur` |
| Generated subtitle/style | Yes | Yes | `subtitle` |
| Manual text/style/timing | Yes | Yes | `layers[type=text]`; ASS renderer |
| Logo/watermark | Yes | Yes | `logo` |
| Image/sticker | Yes | Yes | `layers[type=image]` |
| Overlay video/chroma key | Yes | Yes | `layers[type=video]` |
| Legacy overlay text | Yes | Yes | `overlay_text` |
| Source audio | Yes | Yes | `audio.source_*` |
| Generated narration | Yes | Yes | `audio.narration_*`; source and final signal checks |
| Separated accompaniment | Yes | Yes | `audio.accompaniment_*` |
| Background music | Yes | Yes | `audio.music_*` |
| Mirror/zoom/auto zoom/brightness/contrast/saturation/sharpen/vignette/border | Controls are not currently sequence-editable | Renderer exists | Snapshot defaults preserve existing behavior; no false parity claim |
| Text animation | Partial | Partial | Existing ASS-supported semantics only |

Known limitations: arbitrary mixed-type editor-layer z-order differs when elements overlap; no pixel-comparison automation; final mixed-stream volume proves audible output but cannot mathematically isolate narration after mixing. Narration input is independently measured before render.

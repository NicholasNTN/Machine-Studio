import unittest

from core.subtitle_sizing import ass_font_size, canonical_font_size, preview_font_pixels
from editor.selection_ref import SelectionRef
from editor.snap_engine import SnapEngine
from editor.timeline_item import TimelineItem, TimelineItemKind
from editor.timeline_state import TimelineState
from editor.track import Track, TrackKind
from editor.subtitle_group import SubtitleGroup, SubtitleGroupStyle
from editor.canvas import CanvasBackground, calculate_fill_rect, calculate_fit_rect
from editor.video_transform import VideoTransform
from core.downloader import safe_output_filename
from core import subtitle_engine
from core.script_roles import assign_role, voice_for_role
from editor.layer_order import CANONICAL_LAYER_ORDER


class EditorDomainTests(unittest.TestCase):
    def test_canvas_fit_geometry_stays_inside_canvas(self):
        cases = ((1080, 1920, 1920, 1080), (1920, 1080, 1080, 1920), (1080, 1350, 1080, 1920), (1080, 1080, 1920, 1080))
        for sw, sh, cw, ch in cases:
            rect = calculate_fit_rect(sw, sh, cw, ch)
            self.assertGreaterEqual(rect.x, -1e-7); self.assertGreaterEqual(rect.y, -1e-7)
            self.assertLessEqual(rect.x + rect.width, cw + 1e-7); self.assertLessEqual(rect.y + rect.height, ch + 1e-7)

    def test_canvas_fill_geometry_intentionally_overflows(self):
        rect = calculate_fill_rect(1080, 1920, 1920, 1080)
        self.assertTrue(rect.width > 1920 or rect.height > 1080)

    def test_canvas_background_round_trip(self):
        state = CanvasBackground(mode="image", image_path="background.png", image_fit="cover", opacity=82)
        self.assertEqual(CanvasBackground.from_dict(state.to_dict()), state)

    def test_video_transform_round_trip(self):
        state = VideoTransform(position_x=12.5, scale_x=135, rotation=8, fit_mode="fill")
        self.assertEqual(VideoTransform.from_dict(state.to_dict()), state)

    def test_downloader_filename_is_windows_safe(self):
        self.assertEqual(safe_output_filename('  bad:<video>?*.mp4. '), "bad__video___.mp4")

    def test_subtitle_preset_library_is_accessible(self):
        self.assertGreaterEqual(len(subtitle_engine.list_presets()), 48)
        self.assertTrue(all(subtitle_engine.preset_category(name) for name in subtitle_engine.list_presets()))

    def test_dual_voice_role_assignment(self):
        roles = [assign_role("Before and after", index, 4) for index in range(4)]
        self.assertEqual(roles, ["before", "before", "after", "after"])
        self.assertEqual(voice_for_role("after", "A", "B", "Before and after"), "B")
        self.assertEqual(voice_for_role("single", "A", "B", "Factory documentary"), "A")

    def test_canonical_composition_order(self):
        self.assertLess(CANONICAL_LAYER_ORDER.index("canvas_background"), CANONICAL_LAYER_ORDER.index("base_video"))
        self.assertLess(CANONICAL_LAYER_ORDER.index("overlay_video"), CANONICAL_LAYER_ORDER.index("subtitle"))
        self.assertEqual(CANONICAL_LAYER_ORDER[-1], "logo")

    def test_non_video_content_extends_trimmed_video_duration(self):
        state = TimelineState(clips=[{"source_start": 10.0, "source_end": 61.523, "enabled": True}])
        track = state.track_for_kind(TimelineItemKind.AUDIO)
        state.items.append(TimelineItem(TimelineItemKind.AUDIO, track.id, 0, 58.0))
        self.assertEqual(state.duration, 58.0)

    def test_trimmed_video_remains_duration_baseline(self):
        state = TimelineState(clips=[{"source_start": 10.0, "source_end": 61.523, "enabled": True}])
        self.assertAlmostEqual(state.duration, 51.523)

    def test_tracks_serialize(self):
        track = Track("Audio", TrackKind.AUDIO, locked=True, muted=True, item_ids=["a1"])
        self.assertEqual(Track.from_dict(track.to_dict()), track)

    def test_snap_and_selection_identity(self):
        self.assertEqual(SnapEngine(0.1).snap(1.04, [(1.0, "playhead")]).target_kind, "playhead")
        self.assertEqual(SelectionRef("subtitle", "s1", "group-a").group_id, "group-a")

    def test_subtitle_size_is_identity_for_ass(self):
        self.assertEqual(canonical_font_size(27), 27)
        self.assertEqual(ass_font_size(27), 27)
        self.assertEqual(preview_font_pixels(27, 960, 540, 1920, 1080), 14)
        self.assertEqual(preview_font_pixels(27, 540, 960, 1080, 1920), 14)

    def test_subtitle_preview_scaling_for_project_canvases(self):
        for project_width, project_height in ((1080, 1920), (1920, 1080), (1080, 1350), (1080, 1080)):
            self.assertEqual(preview_font_pixels(64, project_width / 2, project_height / 2, project_width, project_height), 32)
            self.assertEqual(ass_font_size(64), 64)

    def test_subtitle_group_round_trip(self):
        group = SubtitleGroup("g1", "srt", "captions.srt", SubtitleGroupStyle(font_size=27), ["g1:0"])
        restored = SubtitleGroup.from_dict(group.to_dict())
        self.assertEqual(restored.style.font_size, 27)
        self.assertEqual(restored.segment_ids, ["g1:0"])


if __name__ == "__main__":
    unittest.main()

import unittest

from core.subtitle_sizing import ass_font_size, canonical_font_size, preview_font_pixels
from editor.selection_ref import SelectionRef
from editor.snap_engine import SnapEngine
from editor.timeline_item import TimelineItem, TimelineItemKind
from editor.timeline_state import TimelineState
from editor.track import Track, TrackKind
from editor.subtitle_group import SubtitleGroup, SubtitleGroupStyle, subtitle_group_is_visible, active_subtitle_render_state
from editor.canvas import CanvasBackground, calculate_fill_rect, calculate_fit_rect
from editor.blur_zone import BlurZone, source_zone_canvas_rect, resize_normalized_zone
from editor.video_transform import VideoTransform
from core.downloader import safe_output_filename
from core.audio_state import AudioState, replace_narration_source, audio_source_is_loadable
from core import subtitle_engine
from core.script_roles import assign_role, voice_for_role
from editor.layer_order import CANONICAL_LAYER_ORDER
from editor.preview_binding import PreviewBinding, binding_after_clip_change
from editor.sequence_manager import SequenceManager
from core.ai_styles import AI_STYLES, grouped_styles
from core.speaker_role_service import analyze_speaker_roles


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
        segments = [{"id": str(i), "text": text} for i, text in enumerate(("The old machine was rusted.", "Its output was slow.", "After the rebuild, production doubled.", "Now the line runs cleanly."))]
        roles = [item["speaker_role"] for item in analyze_speaker_roles(segments, "before_after")]
        self.assertEqual(roles, ["before", "before", "after", "after"])
        self.assertEqual(voice_for_role("after", "A", "B", "Before and after"), "B")
        self.assertEqual(voice_for_role("single", "A", "B", "Factory documentary"), "A")

    def test_mystery_roles_keep_explainer_rhetorical_question(self):
        texts = ["What colossal titan lurks here?", "Meet the largest land machine.", "Its wheel cuts through rock.", "Conveyors move earth.", "It works without stopping.", "Can any other machine match it?"]
        classified = analyze_speaker_roles([{"id": str(i), "text": text} for i, text in enumerate(texts)], "mystery_curiosity")
        self.assertEqual([item["speaker_role"] for item in classified], ["questioner", "explainer", "explainer", "explainer", "explainer", "explainer"])

    def test_role_classifier_respects_manual_override(self):
        segment = {"id": "x", "text": "Edited text", "speaker_role": "guest", "role_locked": True}
        self.assertEqual(analyze_speaker_roles([segment], "interview")[0]["speaker_role"], "guest")

    def test_canonical_composition_order(self):
        self.assertLess(CANONICAL_LAYER_ORDER.index("canvas_background"), CANONICAL_LAYER_ORDER.index("base_video"))
        self.assertLess(CANONICAL_LAYER_ORDER.index("overlay_video"), CANONICAL_LAYER_ORDER.index("subtitle"))
        self.assertEqual(CANONICAL_LAYER_ORDER[-1], "logo")

    def test_ai_style_metadata_is_complete_and_unique(self):
        self.assertEqual(len({style.id for style in AI_STYLES}), len(AI_STYLES))
        for style in AI_STYLES:
            self.assertTrue(style.id and style.display_name and style.display_name_vi)
            self.assertIn(style.voice_mode, {"single", "dual", "triple", "multi"})
            self.assertTrue(style.speaker_roles)
        dual_ids = {style.id for style in grouped_styles()["dual"]}
        self.assertTrue({"mystery_curiosity", "before_after", "interview", "question_answer", "debate", "problem_solution"}.issubset(dual_ids))

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

    def test_professional_subtitle_group_visibility_wins(self):
        group = SubtitleGroup("g", "srt", "captions.srt", visible=True)
        legacy_track_visible = False
        self.assertFalse(legacy_track_visible)
        self.assertTrue(subtitle_group_is_visible(True, group))

    def test_subtitle_render_state_does_not_require_selection(self):
        group = SubtitleGroup("g", "srt", "captions.srt", visible=True)
        visible, text, start, end = active_subtitle_render_state(True, group, [(1.0, 3.0, "Visible")], 2.0)
        self.assertTrue(visible)
        self.assertEqual((text, start, end), ("Visible", 1.0, 3.0))

    def test_source_normalized_blur_mapping_across_canvas_ratios(self):
        zone = BlurZone("lower-third", x=.12, y=.73, width=.75, height=.16)
        cases = ((1080, 1920, 1920, 1080), (1920, 1080, 1080, 1920), (1080, 1350, 1080, 1920))
        for sw, sh, cw, ch in cases:
            video = calculate_fit_rect(sw, sh, cw, ch)
            rect = source_zone_canvas_rect(zone, sw, sh, cw, ch, {"fit_mode": "fit"})
            self.assertAlmostEqual((rect.x - video.x) / video.width, zone.x, places=6)
            self.assertAlmostEqual((rect.y - video.y) / video.height, zone.y, places=6)
            self.assertAlmostEqual(rect.width / video.width, zone.width, places=6)
            self.assertAlmostEqual(rect.height / video.height, zone.height, places=6)

    def test_legacy_blur_percentages_upgrade_to_source_coordinates(self):
        zone = BlurZone.from_dict({"x": 12, "y": 73, "w": 75, "h": 16})
        self.assertEqual(zone.coordinate_space, "source_video")
        self.assertAlmostEqual(zone.width, .75)

    def test_normalized_blur_resizes_from_all_corners(self):
        zone = BlurZone("z", x=.2, y=.2, width=.5, height=.4)
        for corner in ("top_left", "top_right", "bottom_left", "bottom_right"):
            resized = resize_normalized_zone(zone, corner, .05, .04)
            self.assertGreaterEqual(resized.width, .03)
            self.assertGreaterEqual(resized.height, .03)

    def test_narration_replacement_preserves_user_audio_state(self):
        state = AudioState(True, .42, True, .67, False, .31)
        replacement = replace_narration_source(state, "new-narration.wav")
        self.assertEqual(replacement.source, "new-narration.wav")
        self.assertEqual(replacement.state, state)
        self.assertFalse(audio_source_is_loadable("missing-narration.wav"))

    def test_preview_binding_clears_after_last_clip_deletion(self):
        current = PreviewBinding("video.mp4", 12.0, 4.0, True)
        self.assertEqual(binding_after_clip_change([], current), PreviewBinding(None, 0.0, 0.0, False))

    def test_multi_sequence_content_and_undo_are_isolated(self):
        manager = SequenceManager(); first = manager.active
        first.state = {"editor_clips": [{"path": "a.mp4"}], "subtitle": "A"}; first.undo_history.append("A edit")
        second = manager.create(); second.state["editor_clips"] = [{"path": "b.mp4"}]; second.undo_history.append("B edit")
        self.assertEqual(first.state["editor_clips"][0]["path"], "a.mp4")
        self.assertEqual(first.undo_history, ["A edit"]); self.assertEqual(second.undo_history, ["B edit"])

    def test_legacy_project_migrates_to_timeline_one_and_persists_active(self):
        manager = SequenceManager.from_dict({}, {"editor_clips": [{"path": "old.mp4"}]})
        self.assertEqual(manager.active.name, "Timeline 1")
        restored = SequenceManager.from_dict(manager.to_dict())
        self.assertEqual(restored.active_sequence_id, manager.active_sequence_id)


if __name__ == "__main__":
    unittest.main()

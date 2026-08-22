import unittest
import tempfile
import json
import sys
import ast
from unittest.mock import patch
from pathlib import Path

from core.subtitle_sizing import ass_font_size, canonical_font_size, preview_font_pixels
from editor.selection_ref import SelectionRef
from editor.snap_engine import SnapEngine
from editor.timeline_item import TimelineItem, TimelineItemKind
from editor.timeline_state import TimelineState
from editor.track import Track, TrackKind
from editor.subtitle_group import SubtitleGroup, SubtitleGroupStyle, subtitle_group_is_visible, active_subtitle_render_state
from editor.canvas import CanvasBackground, calculate_fill_rect, calculate_fit_rect, calculate_video_layout, output_canvas_size
from editor.blur_zone import BlurZone, source_zone_canvas_rect, resize_normalized_zone
from editor.video_transform import VideoTransform
from core.downloader import safe_output_filename
from core.audio_state import AudioState, replace_narration_source, audio_source_is_loadable
from core.last_used_preferences import LastUsedPreferences, safe_int, safe_float, safe_bool, safe_str, safe_splitter_sizes, sanitize_workspace_splitter_sizes
from core import editor_engine, subtitle_engine, ffmpeg_engine
from core.script_roles import assign_role, voice_for_role
from core.media_library import migrate_global_media_library
from core.sequence_context import active_editor_source, find_origin_sequence
from core.sequence_context import sequence_narration_path
from core.file_dialog_history import FileDialogHistory
from core.render_snapshot import build_render_snapshot, snapshot_resolution
from core.narration_state import begin_narration_generation, finish_narration_generation, resolve_export_narration
from services.playback_controller import PlaybackController, narration_status_action
from core.preview_result import cache_processed_preview_result
from editor.text_style import TextStyle
from editor.blur_zone import normalize_blur_zones
from editor.layer_order import CANONICAL_LAYER_ORDER
from editor.preview_binding import PreviewBinding, binding_after_clip_change
from editor.sequence_manager import SequenceManager
from editor.timeline_view import compute_auto_timeline_view
from core.ai_styles import AI_STYLES, grouped_styles
from core.speaker_role_service import analyze_speaker_roles
from core.models import AIProject


class EditorDomainTests(unittest.TestCase):
    def test_ui_design_tokens_are_semantic_and_web_portable(self):
        values = json.loads(Path("design/tokens.json").read_text(encoding="utf-8"))
        self.assertTrue({"color", "spacing", "radius", "typography", "motion", "control"} <= values.keys())
        self.assertTrue({"background", "surface", "surfaceRaised", "textPrimary", "accent", "danger"} <= values["color"].keys())
        self.assertFalse(any(key.startswith("Q") for group in values.values() for key in group))

    def test_ui_visual_system_uses_round_three_palette_and_scale(self):
        values = json.loads(Path("design/tokens.json").read_text(encoding="utf-8"))
        self.assertEqual(values["color"]["background"], "#090D12")
        self.assertEqual(values["color"]["surface"], "#0F141B")
        self.assertEqual(values["color"]["surfaceRaised"], "#141B24")
        self.assertEqual(values["color"]["surfaceElevated"], "#18212C")
        self.assertEqual(values["color"]["accent"], "#4C8DFF")
        self.assertEqual(values["color"]["playhead"], "#FF5968")
        self.assertEqual(list(values["spacing"].values()), [4, 6, 8, 12, 16, 20, 24])
        self.assertEqual(
            [values["radius"][key] for key in ("tiny", "small", "medium", "button", "card", "large", "dialog")],
            [4, 6, 8, 8, 10, 12, 14],
        )

    def test_main_window_static_theme_is_centralized(self):
        source = Path("app.py").read_text(encoding="utf-8")
        style_method = next(node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and node.name == "_style")
        calls = [node for node in ast.walk(style_method) if isinstance(node, ast.Call)]
        self.assertEqual(len(calls), 1)
        self.assertEqual(getattr(calls[0].func, "id", ""), "apply_theme")

    def test_required_bundled_svg_icons_exist(self):
        from ui.icons import REQUIRED_ICONS, icon_path
        missing = [name for name in REQUIRED_ICONS if not icon_path(name).is_file()]
        self.assertEqual(missing, [])

    def test_responsive_timeline_view_scales_with_viewport_and_fits_content(self):
        cases = ((800, 20), (1200, 60), (1800, 80), (2400, 80))
        views = [compute_auto_timeline_view(width, duration) for width, duration in cases]
        for view, (_, duration) in zip(views, cases):
            self.assertGreaterEqual(view.visible_duration, duration + max(5, duration * 0.05))
            self.assertIn(view.major_tick_interval, (0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300))
            self.assertGreater(view.pixels_per_second, 0)
        self.assertGreater(views[3].visible_duration, views[2].visible_duration)

    def test_second_clip_fits_inside_responsive_timeline_range(self):
        view = compute_auto_timeline_view(1400, 60 + 25)
        last_clip_right = 132 + 85 * view.pixels_per_second
        rendered_width = 132 + view.visible_duration * view.pixels_per_second
        self.assertLess(last_clip_right, rendered_width)

    def test_all_export_option_callers_pass_explicit_snapshot(self):
        tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
        methods = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        gather = next(node for node in methods if node.name == "gather_export_options")
        self.assertEqual([arg.arg for arg in gather.args.args], ["self", "snapshot"])
        self.assertEqual(len(gather.args.defaults), 0)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == "gather_export_options"]
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(len(call.args) == 1 for call in calls))
        refresh = next(node for node in methods if node.name == "refresh_processed_preview")
        refresh_calls = [node for node in ast.walk(refresh) if isinstance(node, ast.Call)]
        self.assertTrue(any(getattr(node.func, "id", "") == "build_render_snapshot" for node in refresh_calls))
        resolution_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute) and node.func.attr == "_preview_resolution"]
        self.assertTrue(all(len(call.args) == 2 for call in resolution_calls))

    def test_capture_active_sequence_uses_canonical_narration_resolver(self):
        tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
        methods = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        capture = next(node for node in methods if node.name == "capture_active_sequence")
        calls = [node for node in ast.walk(capture) if isinstance(node, ast.Call)]
        names = {getattr(node.func, "id", "") for node in calls}
        self.assertIn("resolve_export_narration", names)
        self.assertNotIn("active_narration_path", names)
        resolver = next(node for node in calls if getattr(node.func, "id", "") == "resolve_export_narration")
        self.assertEqual(len(resolver.args), 2)

    def test_font_combo_callers_use_guarded_family_fonts(self):
        tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        combo_calls = [node for node in calls if isinstance(node.func, ast.Attribute)
                       and node.func.attr == "setCurrentFont"]
        self.assertGreater(len(combo_calls), 0)
        self.assertTrue(all(not (call.args and isinstance(call.args[0], ast.Call)
                                and getattr(call.args[0].func, "id", "") == "QFont")
                            for call in combo_calls))
        helper = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                      and node.name == "font_family_for_combo")
        set_sizes = [node for node in ast.walk(helper) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Attribute) and node.func.attr == "setPointSize"]
        self.assertEqual(len(set_sizes), 1)

    def test_processed_preview_result_is_cached_without_cross_timeline_display(self):
        manager = SequenceManager(); first = manager.active; second = manager.create()
        manager.activate(second.id)
        self.assertFalse(cache_processed_preview_result(manager.sequences, first.id, manager.active_sequence_id, "preview-a.mp4"))
        self.assertEqual(first.ai_project["processed_preview_path"], "preview-a.mp4")
        self.assertNotIn("processed_preview_path", second.ai_project)
        self.assertTrue(cache_processed_preview_result(manager.sequences, second.id, manager.active_sequence_id, "preview-b.mp4"))
        first.state = {"narration_path": "voice-a.wav", "resolution": "720x1280", "canvas_background": {"mode": "blur"}}
        second.state = {"narration_path": "voice-b.wav", "resolution": "1920x1080", "canvas_background": {"mode": "solid"}}
        options_a = build_render_snapshot(manager.sequences, first.id).export_options()
        options_b = build_render_snapshot(manager.sequences, second.id).export_options()
        self.assertEqual((options_a.narration_path, options_a.canvas_background_mode), ("voice-a.wav", "blur"))
        self.assertEqual((options_b.narration_path, options_b.canvas_background_mode), ("voice-b.wav", "solid"))

    def test_preview_narration_is_export_truth_for_active_sequence(self):
        state = {"narration_path": "legacy.wav", "narration_source_path": "latest.wav",
                 "narration_synced_path": "stale.wav", "narration_revision": 2, "narration_synced_revision": 1}
        self.assertEqual(resolve_export_narration(state, "preview.wav"), "preview.wav")
        self.assertEqual(resolve_export_narration(state), "latest.wav")
        self.assertEqual(resolve_export_narration({}, ""), "")

    def test_sequence_narration_resolution_preserves_timeline_isolation(self):
        states = [
            {"narration_path": "voice-a.wav"},
            {"narration_path": "voice-b.wav"},
            {"narration_path": ""},
        ]
        self.assertEqual([resolve_export_narration(state) for state in states],
                         ["voice-a.wav", "voice-b.wav", ""])

    def test_tts_regeneration_invalidates_then_publishes_synced_revision(self):
        stale = begin_narration_generation({"narration_revision": 4, "narration_synced_revision": 4,
                                            "narration_synced_path": "old.m4a"})
        self.assertEqual(stale["narration_revision"], 5)
        self.assertLess(stale["narration_synced_revision"], stale["narration_revision"])
        completed = finish_narration_generation(stale, "new.m4a")
        self.assertEqual(completed["narration_source_path"], "new.m4a")
        self.assertEqual(completed["narration_synced_path"], "new.m4a")
        self.assertEqual(completed["narration_synced_revision"], completed["narration_revision"])

    def test_final_mix_splits_narration_for_ducking_and_audible_mix(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); video = root / "video.mp4"; voice = root / "voice.wav"; output = root / "out.mp4"
            video.write_bytes(b"video"); voice.write_bytes(b"voice")
            commands = []

            def fake_run(cmd, **_kwargs):
                commands.append(cmd); output.write_bytes(b"x" * 2048); return ""

            info = {"duration": 2.0, "has_audio": True, "width": 640, "height": 360, "normalized_path": str(video)}
            options = ffmpeg_engine.ExportOptions(narration_path=str(voice), source_audio_mode="Giữ âm gốc")
            with patch.object(ffmpeg_engine, "probe", return_value=info), \
                 patch.object(ffmpeg_engine, "find_binary", return_value="ffmpeg"), \
                 patch.object(ffmpeg_engine, "choose_video_encoder", return_value=["-c:v", "libx264"]), \
                 patch.object(ffmpeg_engine, "run", side_effect=fake_run):
                ffmpeg_engine.export_video(str(video), str(output), options)
            graph = commands[-1][commands[-1].index("-filter_complex") + 1]
        self.assertIn("[anar]asplit=2[asidechain][avoice]", graph)
        self.assertIn("[abase][asidechain]sidechaincompress", graph)
        self.assertIn("[aducked][avoice]amix", graph)

    def test_render_snapshot_captures_complete_sequence_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); video = root / "video.mp4"; voice = root / "voice.wav"; logo = root / "logo.png"; image = root / "sticker.png"
            for path in (video, voice, logo, image): path.write_bytes(b"asset")
            manager = SequenceManager(); sequence = manager.active
            sequence.state = {
                "editor_use_timeline": True, "resolution": "1920x1080 (YouTube)", "project_aspect_ratio": "9:16",
                "editor_clips": [{"path": str(video), "enabled": True, "source_start": 1, "source_end": 6,
                                  "transform": {"fit_mode": "fill", "position_x": 42, "scale_x": 115}}],
                "canvas_background": {"mode": "blur", "blur_strength": 31, "brightness": -22, "opacity": 85},
                "narration_path": str(voice), "narration_volume": 77, "mute_original_voice": True,
                "blur_enabled": True, "blur_zones": [{"id": "blur-a", "x": 1, "y": 2, "w": 30, "h": 10}],
                "sub_enabled": True, "subtitle_path": str(root / "captions.srt"), "preview_cues": [[0, 1, "Hi"]],
                "subtitle_style": {"font_name": "Arial", "font_size": 48},
                "logo_enabled": True, "logo_path": str(logo), "logo_opacity": 80,
                "editor_layers": [{"id": "text-a", "type": "text", "enabled": True, "text": "Title", "start": 0, "end": 2},
                                  {"id": "image-a", "type": "image", "enabled": True, "path": str(image)}],
            }
            snapshot = build_render_snapshot(manager.sequences, sequence.id)
        self.assertEqual(snapshot.sequence_id, sequence.id); self.assertEqual(snapshot.canvas["mode"], "blur")
        self.assertEqual(snapshot.video_transform["fit_mode"], "fill"); self.assertEqual(snapshot.audio["narration_path"], str(voice))
        self.assertEqual(snapshot.audio["source_audio_mode"], "Tắt toàn bộ âm gốc")
        self.assertTrue(snapshot.blur["enabled"]); self.assertTrue(snapshot.subtitle["enabled"]); self.assertTrue(snapshot.logo["enabled"])
        self.assertEqual([layer["id"] for layer in snapshot.layers], ["text-a", "image-a"])
        self.assertEqual(snapshot.export_options().resolution, "1080x1920")

    def test_render_snapshot_isolated_and_round_trips_with_sequence_manager(self):
        manager = SequenceManager(); first = manager.active
        first.state = {"narration_path": "voice-a.wav", "canvas_background": {"mode": "blur"}, "editor_layers": [{"id": "a", "type": "text"}]}
        second = manager.create(); second.state = {"narration_path": "voice-b.wav", "canvas_background": {"mode": "solid", "color": "#123456"}}
        third = manager.create(); third.state = {"narration_path": "", "canvas_background": {"mode": "image", "image_path": "missing.png"}}
        before = [build_render_snapshot(manager.sequences, item.id).to_dict() for item in manager.sequences]
        restored = SequenceManager.from_dict(manager.to_dict())
        after = [build_render_snapshot(restored.sequences, item.id).to_dict() for item in restored.sequences]
        self.assertEqual(before, after)
        self.assertEqual(before[0]["audio"]["narration_path"], "voice-a.wav")
        self.assertEqual(before[1]["canvas"]["color"], "#123456")
        self.assertFalse(before[2]["audio"]["narration_enabled"])
        self.assertIn("Canvas image background", build_render_snapshot(restored.sequences, third.id).validate().errors[0])

    def test_export_snapshot_remains_bound_to_origin_while_other_sequence_mutates(self):
        manager = SequenceManager(); origin = manager.active
        origin.state = {"editor_clips": [{"path": "a.mp4", "enabled": True, "source_start": 0, "source_end": 4,
                                           "transform": {"fit_mode": "fit"}}],
                        "blur_zones": [{"id": "a", "x": 10, "y": 70, "w": 80, "h": 10}],
                        "narration_path": "voice-a.wav", "project_aspect_ratio": "16:9",
                        "project_canvas_dimensions": [1920, 1080]}
        other = manager.create(); other.state = {"editor_layers": [{"id": "text-b", "text": "before"}]}
        snapshot = build_render_snapshot(manager.sequences, origin.id)
        origin_id = snapshot.sequence_id
        other.state["editor_layers"][0]["text"] = "after"
        origin.state["blur_zones"][0]["x"] = 90
        manager.activate(other.id)
        self.assertEqual(snapshot.sequence_id, origin_id)
        self.assertEqual(snapshot.blur["zones"][0]["x"], .10)
        self.assertEqual(snapshot.audio["narration_path"], "voice-a.wav")

    def test_export_and_sequence_switch_do_not_use_blocking_or_shared_worker_patterns(self):
        tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
        methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        close_calls = [node for node in ast.walk(methods["closeEvent"]) if isinstance(node, ast.Call)]
        self.assertFalse(any(isinstance(node.func, ast.Attribute) and node.func.attr == "wait" for node in close_calls))
        export = methods["export_batch"]
        nested_job = next(node for node in export.body if isinstance(node, ast.FunctionDef) and node.name == "job")
        job_attributes = {node.attr for node in ast.walk(nested_job) if isinstance(node, ast.Attribute)}
        self.assertNotIn("sequence_manager", job_attributes)
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn('export_job_id = uuid4().hex', source)
        self.assertIn('"render_jobs" / export_job_id', source)
        self.assertIn('self.export_process_holder = {"process": None}', source)
        self.assertIn('self.preview_process_holder = {"process": None}', source)

    def test_snapshot_resolution_follows_preview_canvas_aspect(self):
        self.assertEqual(snapshot_resolution({"resolution": "1920x1080 (YouTube)", "aspect_ratio": "9:16"}), "1080x1920")
        self.assertEqual(snapshot_resolution({"resolution": "1080x1920", "aspect_ratio": "16:9"}), "1920x1080")
        self.assertEqual(snapshot_resolution({"resolution": "Original", "aspect_ratio": "9:16"}), "Original")
        self.assertEqual(snapshot_resolution({"resolution": "Original", "aspect_ratio": "9:16", "canvas_dimensions": [1080, 1920]}), "1080x1920")
        self.assertEqual(snapshot_resolution({"resolution": "1080x1920", "aspect_ratio": "Original", "canvas_dimensions": [1280, 720]}), "1920x1080")

    def test_preview_and_export_share_canonical_video_layout(self):
        cases = (
            (1080, 1920, 1920, 1080),
            (720, 960, 1080, 1920),
            (1920, 1080, 1080, 1920),
        )
        transform = {"fit_mode": "fit", "position_x": 50, "position_y": 50}
        for sw, sh, cw, ch in cases:
            preview = calculate_video_layout(sw, sh, cw, ch, transform)
            export = calculate_video_layout(sw, sh, *output_canvas_size(cw, ch), transform)
            self.assertEqual(preview, export)
            self.assertAlmostEqual(preview.x + preview.width / 2, cw / 2)
            self.assertAlmostEqual(preview.y + preview.height / 2, ch / 2)

    def test_timeline_renderer_emits_all_canvas_background_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); video = root / "video.mp4"; image = root / "background.png"
            video.write_bytes(b"video"); image.write_bytes(b"image")
            clip = {"path": str(video), "enabled": True, "source_start": 0, "source_end": 2, "transform": {"fit_mode": "fit"}}
            graphs = {}

            def fake_run(cmd, **_kwargs):
                Path(cmd[-1]).write_bytes(b"x" * 2048)
                graphs[current[0]] = cmd[cmd.index("-filter_complex") + 1]

            info = {"duration": 2.0, "has_audio": True, "width": 1920, "height": 1080, "normalized_path": str(video)}
            with patch.object(ffmpeg_engine, "probe", return_value=info), \
                 patch.object(ffmpeg_engine, "find_binary", return_value="ffmpeg"), \
                 patch.object(ffmpeg_engine, "run", side_effect=fake_run):
                for mode in ("blur", "solid", "image", "none"):
                    current = [mode]
                    editor_engine.render_timeline(
                        [clip], str(root / f"{mode}.mp4"), target_width=1080, target_height=1920,
                        canvas_background={"mode": mode, "image_path": str(image), "color": "#123456", "blur_strength": 31},
                    )
        self.assertIn("boxblur=31", graphs["blur"])
        self.assertIn("color=c=0x123456", graphs["solid"])
        self.assertIn("force_original_aspect_ratio=increase,crop=1080:1920", graphs["image"])
        self.assertIn("color=c=black", graphs["none"])

    def test_active_sequence_narration_never_falls_back_to_other_timeline(self):
        manager = SequenceManager(); first = manager.active
        first.state["narration_path"] = "voice-a.wav"
        second = manager.create(); second.state["narration_path"] = "voice-b.wav"
        self.assertEqual(sequence_narration_path(manager.sequences, first.id), "voice-a.wav")
        self.assertEqual(sequence_narration_path(manager.sequences, second.id), "voice-b.wav")
        first.state["narration_path"] = ""
        self.assertEqual(sequence_narration_path(manager.sequences, first.id), "")

    def test_narration_only_and_mixed_audio_plans_are_explicit(self):
        label, expression = ffmpeg_engine.audio_mix_filter(["anar"])
        self.assertEqual(label, "anar"); self.assertIsNone(expression)
        label, expression = ffmpeg_engine.audio_mix_filter(["abase", "anar"])
        self.assertEqual(label, "aout"); self.assertIn("normalize=0", expression)
        filters = ffmpeg_engine.normalized_audio_filters(1.0)
        self.assertTrue(any("channel_layouts=stereo" in value for value in filters))

    def test_invalid_narration_and_output_audio_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            empty = Path(folder) / "empty.wav"; empty.touch()
            self.assertFalse(ffmpeg_engine.validate_audio_file(empty)["valid"])
        with patch.object(ffmpeg_engine, "probe", return_value={"has_audio": False, "duration": 5.0}):
            self.assertFalse(ffmpeg_engine.verify_output_audio("out.mp4")["has_audio"])

    def test_audio_signal_inspection_detects_audible_and_silent_sources(self):
        valid = {"path": "voice.wav", "exists": True, "has_audio": True, "duration": 2.0, "valid": True}
        with patch.object(ffmpeg_engine, "validate_audio_file", return_value=valid), \
             patch.object(ffmpeg_engine, "find_binary", return_value="ffmpeg"), \
             patch.object(ffmpeg_engine, "run", return_value="mean_volume: -24.0 dB\nmax_volume: -2.5 dB"), \
             patch.object(Path, "stat") as stat:
            stat.return_value.st_size = 1234
            result = ffmpeg_engine.inspect_audio_signal("voice.wav")
        self.assertTrue(result["audible"]); self.assertEqual(result["max_volume"], -2.5)
        with patch.object(ffmpeg_engine, "validate_audio_file", return_value=valid), \
             patch.object(ffmpeg_engine, "find_binary", return_value="ffmpeg"), \
             patch.object(ffmpeg_engine, "run", return_value="mean_volume: -91.0 dB\nmax_volume: -80.0 dB"), \
             patch.object(Path, "stat") as stat:
            stat.return_value.st_size = 1234
            self.assertFalse(ffmpeg_engine.inspect_audio_signal("voice.wav")["audible"])

    def test_file_dialog_history_is_local_and_handles_missing_paths(self):
        settings = {}; saved = []
        with tempfile.TemporaryDirectory() as folder:
            media = Path(folder) / "media"; media.mkdir(); video = media / "a.mp4"; video.touch()
            history = FileDialogHistory(settings, lambda: saved.append(True))
            history.remember_file("last_media_dir", video)
            self.assertEqual(history.initial_path("last_media_dir"), str(media))
            missing = media / "gone" / "file.mp4"
            history.values["last_project_open_dir"] = str(missing)
            self.assertEqual(history.initial_path("last_project_open_dir"), str(media))
        self.assertIn("file_dialog_history", settings); self.assertTrue(saved)
        self.assertNotIn("narration_path", settings["file_dialog_history"])

    def test_run_persists_full_combined_process_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "logs" / "export_ffmpeg.log"
            output = ffmpeg_engine.run(
                [sys.executable, "-c", "import sys; print('stdout-line'); print('stderr-line', file=sys.stderr)"],
                log_file=path,
            )
            with self.assertRaises(ffmpeg_engine.FFmpegError):
                ffmpeg_engine.run(
                    [sys.executable, "-c", "import sys; print('fatal-detail', file=sys.stderr); sys.exit(3)"],
                    log_file=path,
                )
            saved = path.read_text(encoding="utf-8")
        self.assertIn("stdout-line", output); self.assertIn("stderr-line", output)
        self.assertIn("FULL FFMPEG COMMAND", saved); self.assertIn("return_code=0", saved)
        self.assertIn("EXPORT SUCCESS", saved)
        self.assertIn("fatal-detail", saved); self.assertIn("return_code=3", saved)
        self.assertIn("EXPORT FAILED", saved)

    def test_boxblur_radii_are_safe_for_real_and_tiny_zones(self):
        cases = ((235, 60, 15, (15, 14)), (973, 112, 15, (15, 15)),
                 (20, 12, 15, (5, 2)), (8, 8, 15, (3, 1)))
        for width, height, desired, expected in cases:
            value, luma, chroma = ffmpeg_engine.boxblur_filter(width, height, desired)
            self.assertEqual((luma, chroma), expected)
            self.assertLess(luma, min(width, height) / 2)
            self.assertLess(chroma, min(width, height) / 4)
            self.assertIn(f"chroma_radius={chroma}", value)
            self.assertNotEqual(value, "boxblur=15:2")

    def test_blur_crop_is_even_and_inside_output(self):
        for value in ((-4, -9, 1, 1), (1079, 1919, 99, 99), (802, 80, 235, 60)):
            x, y, width, height = ffmpeg_engine.safe_blur_crop_rect(*value, 1080, 1920)
            self.assertGreaterEqual(x, 0); self.assertGreaterEqual(y, 0)
            self.assertGreaterEqual(width, 2); self.assertGreaterEqual(height, 2)
            self.assertLessEqual(x + width, 1080); self.assertLessEqual(y + height, 1920)
            self.assertEqual((x % 2, y % 2, width % 2, height % 2), (0, 0, 0, 0))

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

    def test_blur_export_uses_primary_video_rect_not_canvas(self):
        zone = BlurZone("subtitle", x=.10, y=.70, width=.80, height=.10)
        portrait = ffmpeg_engine.blur_zone_output_rect(zone, 720, 960, 1080, 1920, {"fit_mode": "fit"})
        landscape = ffmpeg_engine.blur_zone_output_rect(zone, 720, 960, 1920, 1080, {"fit_mode": "fit"})
        self.assertEqual(portrait, (108, 1248, 864, 144))
        self.assertEqual(landscape, (636, 756, 648, 108))
        self.assertNotEqual(landscape, (192, 756, 1536, 108))

    def test_auto_and_manual_blur_share_canonical_export_geometry(self):
        geometry = (720, 960, 1920, 1080, {"fit_mode": "fit", "scale_x": 120, "scale_y": 90,
                                           "position_x": 35, "position_y": 60})
        manual = {"id": "manual", "x": .15, "y": .72, "width": .70, "height": .12, "source": "manual"}
        automatic = {**manual, "id": "auto", "source": "auto_subtitle", "auto": True}
        self.assertEqual(ffmpeg_engine.blur_zone_output_rect(manual, *geometry),
                         ffmpeg_engine.blur_zone_output_rect(automatic, *geometry))

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
        self.assertEqual(manager.active.name, "Timeline")
        restored = SequenceManager.from_dict(manager.to_dict())
        self.assertEqual(restored.active_sequence_id, manager.active_sequence_id)

    def test_sequence_rename_duplicate_close_and_order_persist(self):
        manager = SequenceManager(); first = manager.active; first.state = {"subtitle": "A"}
        manager.rename(first.id, "Machines")
        duplicate = manager.duplicate(first.id); duplicate.state["subtitle"] = "B"
        restored = SequenceManager.from_dict(manager.to_dict())
        self.assertEqual([s.name for s in restored.sequences], ["Machines", "Machines Copy"])
        self.assertEqual(restored.active.state["subtitle"], "B")
        restored.close(duplicate.id)
        self.assertEqual(restored.active.name, "Machines")

    def test_last_used_preferences_never_copy_timeline_content(self):
        settings = {}; prefs = LastUsedPreferences(settings)
        prefs.update(text_font="Oswald", text_color="#FFFF00", subtitle_editor_text="Hello", narration_path="voice.wav", blur_zones=[{"x": .1}])
        self.assertEqual(prefs.text_defaults(), {"font": "Oswald", "color": "#FFFF00"})
        self.assertNotIn("narration_path", settings["last_used_preferences"])

    def test_preference_parsing_survives_missing_empty_and_legacy_settings(self):
        self.assertEqual(LastUsedPreferences({}).values, {})
        self.assertEqual(LastUsedPreferences({"last_used_preferences": {}}).values, {})
        self.assertEqual(LastUsedPreferences({"tts_voice": "legacy"}).values, {})
        self.assertEqual(LastUsedPreferences({"last_used_preferences": "invalid"}).values, {})

    def test_preference_parsing_is_type_safe_for_phase_3d_values(self):
        self.assertEqual(safe_int("64.0", 52), 64)
        self.assertEqual(safe_float("1.25", 1.0), 1.25)
        self.assertFalse(safe_bool("false", True))
        self.assertEqual(safe_str("Oswald", "Arial"), "Oswald")
        self.assertEqual(safe_splitter_sizes({"workspace_horizontal": [240, "900", 320.7]}), {"workspace_horizontal": [240, 900, 320]})

    def test_malformed_preferences_fall_back_independently(self):
        self.assertEqual(safe_int("not-a-number", 48), 48)
        self.assertEqual(safe_float({"bad": True}, 1.0), 1.0)
        self.assertTrue(safe_bool(["bad"], True))
        self.assertEqual(safe_str({"bad": True}, "Default"), "Default")
        self.assertEqual(safe_splitter_sizes({"workspace_horizontal": "bad", "workspace_vertical": [None, "x", 300]}), {"workspace_vertical": [0, 0, 300]})

    def test_workspace_splitter_restore_never_collapses_timeline(self):
        defaults = {"workspace_horizontal": [300, 900, 320], "workspace_vertical": [650, 240]}
        for malformed in (
            {},
            {"workspace_vertical": [900, 0]},
            {"workspace_vertical": [0, 0]},
            {"workspace_vertical": [-1, 220]},
            {"workspace_vertical": ["bad", "values"]},
            {"workspace_vertical": [900]},
        ):
            self.assertEqual(sanitize_workspace_splitter_sizes(malformed), defaults)
        valid = sanitize_workspace_splitter_sizes({"workspace_horizontal": [300, 1000, 320], "workspace_vertical": [700, 220]})
        self.assertEqual(valid["workspace_vertical"], [700, 220])

    def test_settings_store_startup_scenarios_preserve_files(self):
        scenarios = (
            None,
            "",
            json.dumps({"tts_voice": "legacy"}),
            json.dumps({"last_used_preferences": {"text_font_size": "64", "subtitle_bold": "false"}}),
            json.dumps({"last_used_preferences": {"text_font_size": {"bad": True}, "workspace_splitter_sizes": "broken"}}),
        )
        for content in scenarios:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "settings.json"
                if content is not None: path.write_text(content, encoding="utf-8")
                try: saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                except (json.JSONDecodeError, OSError): saved = {}
                if not isinstance(saved, dict): saved = {}
                preferences = LastUsedPreferences(saved)
                self.assertIsInstance(saved, dict); self.assertIsInstance(preferences.values, dict)
                if content is not None: self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_sequence_voice_subtitle_and_blur_state_isolation(self):
        manager = SequenceManager(); first = manager.active
        first.state.update({"narration_path": "voice-a.wav", "preview_cues": [(0, 1, "A")], "blur_zones": [{"id": "a"}]})
        second = manager.create(); second.state.update({"narration_path": "voice-b.wav", "preview_cues": [(0, 1, "B")], "blur_zones": [{"id": "b"}]})
        manager.activate(first.id); self.assertEqual(manager.active.state["narration_path"], "voice-a.wav")
        manager.activate(second.id); self.assertEqual(manager.active.state["blur_zones"][0]["id"], "b")

    def test_narration_status_reentrancy_and_stale_generations(self):
        old_player, old_output = object(), object()
        current_player, current_output = object(), object()
        # A synchronously emitted status during restore is coalesced, not applied.
        self.assertEqual(narration_status_action(
            3, 3, current_player, current_player, current_output, current_output,
            restoring=True,
        ), "defer")
        # A delayed generation-1 callback cannot mutate generation 3.
        self.assertEqual(narration_status_action(
            1, 3, old_player, current_player, old_output, current_output,
        ), "ignore")
        self.assertEqual(narration_status_action(
            3, 3, current_player, current_player, current_output, current_output,
        ), "apply")

    def test_narration_rebuild_installs_session_before_synchronous_status(self):
        class FakeSignal:
            def __init__(self): self.slot = None
            def connect(self, slot): self.slot = slot
            def disconnect(self, slot):
                if self.slot is slot: self.slot = None

        class FakePlayer:
            def __init__(self): self.mediaStatusChanged = FakeSignal(); self.output = None
            def setAudioOutput(self, output): self.output = output
            def setSource(self, _url):
                if self.mediaStatusChanged.slot: self.mediaStatusChanged.slot("synchronous")
            def stop(self): pass
            def deleteLater(self): pass

        class FakeOutput:
            def setVolume(self, value): self.volume = value
            def setMuted(self, value): self.muted = value
            def deleteLater(self): pass

        class FakeController(PlaybackController):
            def _pair(self): return FakePlayer(), FakeOutput()

        controller = FakeController()
        observed = []
        callback = lambda player, output, generation, status: observed.append(
            (player is controller.narration_player, output is controller.narration_output,
             generation == controller.narration_generation, status)
        )
        with patch("services.playback_controller.QTimer.singleShot", side_effect=lambda _, fn: fn()):
            controller.rebuild_narration("", volume=0.5, muted=False, status_callback=callback)
        self.assertEqual(observed, [(True, True, True, "synchronous")])

    def test_auto_blur_is_canonical_sequence_content_and_legacy_state_migrates(self):
        zones = normalize_blur_zones([], {"id": "auto-a", "x": 10, "y": 70, "w": 80, "h": 12})
        self.assertEqual(zones[0]["source"], "auto_subtitle")
        self.assertTrue(zones[0]["auto"])
        manager = SequenceManager(); first = manager.active
        first.state["blur_zones"] = zones
        second = manager.create(); second.state["blur_zones"] = normalize_blur_zones(
            [{"id": "auto-b", "x": 20, "y": 60, "w": 60, "h": 10, "auto": True}]
        )
        manager.activate(first.id); self.assertEqual(manager.active.state["blur_zones"][0]["id"], "auto-a")
        manager.activate(second.id); self.assertEqual(manager.active.state["blur_zones"][0]["id"], "auto-b")

    def test_auto_blur_round_trips_with_project(self):
        manager = SequenceManager(); manager.active.state["blur_zones"] = normalize_blur_zones(
            [{"id": "auto-save", "x": 12, "y": 72, "w": 76, "h": 11, "source": "auto_subtitle"}]
        )
        project = AIProject(active_sequence_id=manager.active_sequence_id, sequences=manager.to_dict()["sequences"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "blur-project.json"; project.save(path); restored = AIProject.load(path)
        zone = restored.sequences[0]["state"]["blur_zones"][0]
        self.assertEqual(zone["id"], "auto-save"); self.assertEqual(zone["source"], "auto_subtitle")

    def test_active_ai_source_uses_only_active_editor_composition(self):
        self.assertEqual(active_editor_source([]), ("empty", ""))
        self.assertEqual(active_editor_source([{"path": "B.mp4", "enabled": True}]), ("single", "B.mp4"))
        self.assertEqual(active_editor_source([{"path": "A.mp4"}, {"path": "B.mp4"}]), ("proxy", ""))

    def test_async_results_resolve_stable_origin_id_or_discard(self):
        manager = SequenceManager(); origin = manager.active; other = manager.create()
        origin.state.update({"script": "A", "narration_path": "voice-a.wav", "preview_cues": [(0, 1, "A")]})
        manager.activate(other.id); other.state.update({"script": "B", "narration_path": "voice-b.wav", "preview_cues": [(0, 1, "B")]})
        target = find_origin_sequence(manager.sequences, origin.id)
        target.state["script"] = "AI result A"
        self.assertEqual(manager.active.state["script"], "B")
        manager.close(origin.id)
        self.assertIsNone(find_origin_sequence(manager.sequences, origin.id))

    def test_manual_text_style_copies_preset_then_diverges_from_subtitle(self):
        subtitle = subtitle_engine.clone_preset("Cinema Gold")
        text = TextStyle.from_subtitle_preset(subtitle)
        text.font_size = 90; text.color = "#FF0000"
        self.assertEqual(subtitle.font_size, 46)
        self.assertEqual(subtitle.primary_color, "#F6D77A")
        layer = editor_engine.make_text_layer("Text", 5.0); layer.update(text.to_dict())
        self.assertEqual(layer["font_size"], 90); self.assertIn("outline_width", layer); self.assertIn("animation", layer)

    def test_manual_text_style_serialization_keeps_object_values(self):
        first = TextStyle(font_name="Oswald", font_size=90, color="#FF0000", rotation=12.5)
        second = TextStyle(font_name="Arial", font_size=50, color="#FFFFFF")
        restored_first = TextStyle.from_dict(first.to_dict())
        restored_second = TextStyle.from_dict(second.to_dict())
        self.assertEqual((restored_first.font_name, restored_first.font_size, restored_first.color), ("Oswald", 90, "#FF0000"))
        self.assertEqual((restored_second.font_name, restored_second.font_size, restored_second.color), ("Arial", 50, "#FFFFFF"))
        self.assertEqual(restored_first.rotation, 12.5)

    def test_multi_sequence_project_schema_round_trip(self):
        manager = SequenceManager(); manager.create("Timeline 2")
        project = AIProject(active_sequence_id=manager.active_sequence_id, sequences=manager.to_dict()["sequences"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "project.json"; project.save(path); restored = AIProject.load(path)
        self.assertEqual(restored.active_sequence_id, manager.active_sequence_id)
        self.assertEqual([item["name"] for item in restored.sequences], ["Timeline", "Timeline 2"])

    def test_media_library_is_global_and_migrates_legacy_sequence_media(self):
        manager = SequenceManager(); first = manager.active; second = manager.create()
        first.state.update({"media_bin": ["A.mp4", "shared.mp4"], "media_display_names": {"A.mp4": "Machine A"}})
        second.state.update({"media_bin": ["B.mp4", "shared.mp4"], "media_display_names": {"B.mp4": "Machine B"}})
        media, names = migrate_global_media_library(["root.mp4"], {"root.mp4": "Root"}, manager.sequences)
        self.assertEqual(media, ["root.mp4", "A.mp4", "shared.mp4", "B.mp4"])
        self.assertEqual(names, {"root.mp4": "Root", "A.mp4": "Machine A", "B.mp4": "Machine B"})
        for sequence in manager.sequences:
            sequence.state.pop("media_bin", None); sequence.state.pop("media_display_names", None)
        project = AIProject(media_library=media, media_display_names=names, active_sequence_id=manager.active_sequence_id, sequences=manager.to_dict()["sequences"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "media-project.json"; project.save(path); restored = AIProject.load(path)
        self.assertEqual(restored.media_library, media)
        self.assertNotIn("media_bin", restored.sequences[0]["state"])

    def test_sequence_auto_names_compact_without_changing_ids(self):
        manager = SequenceManager()
        self.assertEqual(manager.active.name, "Timeline")
        first = manager.create(); second = manager.create()
        self.assertEqual([item.name for item in manager.sequences], ["Timeline", "Timeline 1", "Timeline 2"])
        second_id = second.id
        manager.close(first.id)
        third = manager.create()
        self.assertEqual(third.name, "Timeline 2")
        self.assertEqual([item.name for item in manager.sequences], ["Timeline", "Timeline 1", "Timeline 2"])
        self.assertEqual(second.id, second_id)

    def test_custom_sequence_names_survive_auto_name_compaction(self):
        manager = SequenceManager(); first = manager.create(); custom = manager.create()
        manager.rename(custom.id, "Factory")
        manager.close(first.id)
        self.assertEqual([item.name for item in manager.sequences], ["Timeline", "Factory"])
        self.assertEqual(custom.name_mode, "custom")
        self.assertEqual(manager.create().name, "Timeline 1")
        restored = SequenceManager.from_dict(manager.to_dict())
        self.assertEqual([(item.name, item.name_mode) for item in restored.sequences], [("Timeline", "auto"), ("Factory", "custom"), ("Timeline 1", "auto")])

    def test_integrated_sequence_strip_replaces_fake_qtabbar(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        strip_source = (Path(__file__).resolve().parents[1] / "ui" / "sequence_tab_strip.py").read_text(encoding="utf-8")
        self.assertNotIn("self.sequence_tabs = QTabBar", source)
        self.assertNotIn('addTab("+")', source)
        self.assertIn("self.sequence_strip = SequenceTabStrip()", source)
        self.assertIn("class SequenceTabButton", strip_source)
        self.assertIn("self.close_button.setVisible(False)", strip_source)


if __name__ == "__main__":
    unittest.main()

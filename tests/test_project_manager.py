import json
import tempfile
import unittest
from pathlib import Path

from core.models import AIProject
from core.project_manager import ProjectManager, safe_project_slug


class ProjectManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = {"recent_project_paths": []}
        self.manager = ProjectManager(self.root, self.settings)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_project_has_unique_identity_and_blank_timeline(self):
        first = self.manager.create_project("My Factory Video")
        second = self.manager.create_project("My Factory Video")
        self.assertNotEqual(first.project_id, second.project_id)
        self.assertEqual((first.name, second.name), ("My Factory Video", "My Factory Video 2"))
        self.assertRegex(Path(first.project_path).parent.name, r"my-factory-video_[0-9a-f]{8}")
        project = AIProject.load(first.project_path)
        self.assertEqual(project.media_library, [])
        self.assertEqual(len(project.sequences), 1)
        self.assertEqual(project.sequences[0]["name"], "Timeline")

    def test_slug_is_safe_and_bounded(self):
        self.assertEqual(safe_project_slug("  My Factory / Video  "), "my-factory-video")
        self.assertEqual(safe_project_slug("中文"), "untitled-project")
        self.assertLessEqual(len(safe_project_slug("x" * 100)), 48)

    def test_rename_changes_display_name_not_folder_identity(self):
        record = self.manager.create_project("Before")
        folder = Path(record.project_path).parent
        renamed = self.manager.rename_project(record.project_path, "After")
        self.assertEqual(renamed.name, "After")
        self.assertEqual(Path(renamed.project_path).parent, folder)

    def test_discover_search_inputs_sort_and_deduplicate_recent(self):
        first = self.manager.create_project("Zulu")
        second = self.manager.create_project("Alpha")
        self.settings["recent_project_paths"].append(first.project_path)
        records = self.manager.discover_projects("name_asc")
        self.assertEqual([record.name for record in records], ["Alpha", "Zulu"])
        self.assertEqual(len({record.project_path.casefold() for record in records}), 2)
        self.assertEqual(self.manager.discover_projects("name_desc")[0].name, "Zulu")
        self.assertTrue(second.created_at)

    def test_legacy_metadata_is_backward_compatible_and_stable(self):
        folder = self.root / "projects" / "legacy_folder"; folder.mkdir(parents=True)
        path = folder / "project.json"
        path.write_text(json.dumps({"video_path": "C:/Videos/source.mp4", "scenes": []}), encoding="utf-8")
        first = AIProject.load(path); second = AIProject.load(path)
        self.assertEqual(first.project_id, second.project_id)
        self.assertEqual(first.name, "legacy_folder")
        self.assertTrue(first.created_at and first.updated_at)
        first.save(path)
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["project_id"], first.project_id)

    def test_corrupt_and_missing_projects_do_not_break_discovery(self):
        valid = self.manager.create_project("Valid")
        corrupt = self.root / "projects" / "corrupt"; corrupt.mkdir(parents=True)
        (corrupt / "project.json").write_text("{broken", encoding="utf-8")
        missing = self.root / "missing.json"
        self.settings["recent_project_paths"].extend([str(corrupt / "project.json"), str(missing)])
        records = self.manager.discover_projects()
        self.assertEqual([record.project_path for record in records], [valid.project_path])
        self.assertNotIn(str(missing), self.settings["recent_project_paths"])

    def test_delete_managed_soft_moves_workspace_and_preserves_source_media(self):
        source = self.root / "outside-source.mp4"; source.write_bytes(b"source")
        record = self.manager.create_project("Delete Me")
        project = AIProject.load(record.project_path); project.media_library = [str(source)]; project.video_path = str(source); project.save(record.project_path)
        destination = self.manager.delete_project(record.project_path)
        self.assertTrue(source.is_file())
        self.assertFalse(Path(record.project_path).exists())
        self.assertTrue(destination.is_dir())
        self.assertEqual(destination.parent, self.root / "projects" / ".trash")

    def test_external_remove_keeps_file_and_removes_registration(self):
        external = self.root / "external"; external.mkdir()
        path = external / "editing.json"; AIProject(name="External").save(path)
        self.manager.register_project(path); self.settings["last_project"] = str(path.resolve())
        self.manager.delete_project(path)
        self.assertTrue(path.is_file())
        self.assertEqual(self.settings["recent_project_paths"], [])
        self.assertEqual(self.settings["last_project"], "")

    def test_recent_registry_is_capped(self):
        paths = []
        for index in range(53):
            path = self.root / f"external-{index}.json"; AIProject(name=str(index)).save(path); paths.append(path)
            self.manager.register_project(path)
        self.assertEqual(len(self.settings["recent_project_paths"]), 50)
        self.assertEqual(self.settings["recent_project_paths"][0], str(paths[-1].resolve()))


if __name__ == "__main__":
    unittest.main()

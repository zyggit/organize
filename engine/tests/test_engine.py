import os
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organize_gui.errors import EngineError
from organize_gui.service import EngineService
from organize.__version__ import __version__ as organize_version


class EngineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "下载"
        self.target = self.root / "整理{资料}$"
        self.source.mkdir()
        self.target.mkdir()
        self.service = EngineService(self.root / "data")

    def tearDown(self):
        self.temp.cleanup()

    def profile(self, preset="by-type"):
        return {
            "id": "test-profile",
            "name": "测试方案",
            "presetType": preset,
            "sourceFolders": [str(self.source)],
            "targetFolder": str(self.target),
            "includeSubfolders": True,
            "parameters": {"categories": ["documents", "images", "other"], "olderThanDays": 90},
            "schemaVersion": 1,
        }

    def test_plan_execute_history_and_undo(self):
        source_file = self.source / "合同 预算.pdf"
        source_file.write_bytes(b"contract")
        plan = self.service.create_plan(self.profile())
        self.assertEqual(plan["summary"]["selected"], 1)
        item = plan["items"][0]
        self.assertIn("整理{资料}$", item["target_path"])

        result = self.service.execute(plan["plan_id"])
        self.assertEqual(result["status"], "completed")
        self.assertFalse(source_file.exists())
        moved = Path(item["target_path"])
        self.assertTrue(moved.exists())

        history = self.service.history()
        self.assertEqual(len(history), 1)
        preview = self.service.undo_preview(result["runId"])
        self.assertEqual(preview["items"][0]["state"], "ready")
        undone = self.service.undo(
            result["runId"], [preview["items"][0]["operationId"]]
        )
        self.assertEqual(undone["restored"], 1)
        self.assertTrue(source_file.exists())

    def test_version_and_plan_use_v3_core(self):
        source_file = self.source / "v3.pdf"
        source_file.write_bytes(b"v3")
        self.assertEqual(self.service.version()["organize"], organize_version)
        plan = self.service.create_plan(self.profile())
        self.assertEqual(plan["items"][0]["metadata"]["organizeCore"], organize_version)

    def test_target_conflict_is_renamed_during_planning(self):
        source_file = self.source / "报价单.pdf"
        source_file.write_text("new", encoding="utf-8")
        existing_dir = self.target / "文档"
        existing_dir.mkdir()
        (existing_dir / "报价单.pdf").write_text("old", encoding="utf-8")
        plan = self.service.create_plan(self.profile())
        item = plan["items"][0]
        self.assertTrue(item["target_path"].endswith("报价单 2.pdf"))
        self.assertEqual(item["warning_code"], "TARGET_CONFLICT")

    def test_new_target_after_preview_invalidates_plan(self):
        source_file = self.source / "a.pdf"
        source_file.write_text("a", encoding="utf-8")
        plan = self.service.create_plan(self.profile())
        destination = Path(plan["items"][0]["target_path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("race", encoding="utf-8")
        with self.assertRaises(EngineError) as caught:
            self.service.execute(plan["plan_id"])
        self.assertEqual(caught.exception.code, "PLAN_CHANGED")
        self.assertTrue(source_file.exists())

    def test_temporary_download_is_skipped(self):
        (self.source / "movie.mp4.crdownload").write_bytes(b"partial")
        plan = self.service.create_plan(self.profile())
        self.assertEqual(plan["summary"]["skip"], 1)
        self.assertFalse(plan["items"][0]["selected"])

    def test_duplicate_groups_require_a_choice(self):
        (self.source / "a.bin").write_bytes(b"same payload")
        (self.source / "b.bin").write_bytes(b"same payload")
        profile = self.profile("duplicates")
        profile["parameters"] = {"minimumBytes": 0}
        plan = self.service.create_plan(profile)
        self.assertEqual(plan["summary"]["groups"], 1)
        self.assertEqual(plan["summary"]["selected"], 0)
        self.assertTrue(any(item["metadata"]["recommendedKeep"] for item in plan["items"]))

    def test_quarantine_can_be_restored(self):
        installer = self.source / "旧安装包.dmg"
        installer.write_bytes(b"installer")
        old = (datetime.now(timezone.utc) - timedelta(days=120)).timestamp()
        os.utime(installer, (old, old))
        plan = self.service.create_plan(self.profile("old-installers"))
        result = self.service.execute(plan["plan_id"])
        quarantined = self.service.quarantine()
        self.assertEqual(result["success"], 1)
        self.assertEqual(len(quarantined), 1)
        self.assertFalse(installer.exists())

        restored = self.service.restore_quarantine(
            [quarantined[0]["quarantine_id"]]
        )
        self.assertEqual(restored["restored"], 1)
        self.assertTrue(installer.exists())
        self.assertEqual(self.service.quarantine(), [])

    def test_changed_file_is_not_undone(self):
        source_file = self.source / "a.pdf"
        source_file.write_text("before", encoding="utf-8")
        plan = self.service.create_plan(self.profile())
        result = self.service.execute(plan["plan_id"])
        moved = Path(plan["items"][0]["target_path"])
        moved.write_text("changed", encoding="utf-8")
        preview = self.service.undo_preview(result["runId"])
        self.assertEqual(preview["items"][0]["state"], "changed")
        undone = self.service.undo(
            result["runId"], [preview["items"][0]["operationId"]]
        )
        self.assertEqual(undone["restored"], 0)
        self.assertEqual(undone["failed"], 1)
        self.assertTrue(moved.exists())

    def test_diagnostics_export_is_local_and_complete(self):
        archive = self.root / "organize-diagnostics.zip"
        result = self.service.export_diagnostics(str(archive))
        self.assertEqual(result["path"], str(archive))
        with zipfile.ZipFile(str(archive)) as bundle:
            self.assertIn("diagnostics.json", bundle.namelist())
            contents = bundle.read("diagnostics.json").decode("utf-8")
            self.assertIn('"integrity": "ok"', contents)


if __name__ == "__main__":
    unittest.main()

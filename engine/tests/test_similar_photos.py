import os
import struct
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organize_gui.errors import EngineError
from organize_gui.service import EngineService
from organize_gui.similar import items_from_scan, merge_groups, similar_photos_binary


def write_png(path: Path, width: int, height: int, pixel) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixel(x, y, width, height))
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def scene(x, y, width, height):
    if x < width // 3 and y < height // 5:
        return (240, 20, 20)
    return (20, 30 + (x * 70 // width), 40 + (y * 70 // height))


def rotated(x, y, width, height):
    return scene(y, width - 1 - x, width, height)


def flipped(x, y, width, height):
    return scene(width - 1 - x, y, width, height)


def other(x, y, width, height):
    return (0, 220, 40) if (x + y) % 8 < 4 else (0, 0, 80)


class SimilarPhotoTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "照片"
        self.source.mkdir()
        self.service = EngineService(self.root / "data")

    def tearDown(self):
        self.temp.cleanup()

    def profile(self):
        return {
            "id": "similar",
            "name": "相似照片",
            "presetType": "similar-photos",
            "sourceFolders": [str(self.source)],
            "targetFolder": "",
            "includeSubfolders": True,
            "parameters": {
                "scanExact": True,
                "scanSimilar": True,
                "maxDifference": 5,
                "hashSize": 16,
                "geometricInvariance": True,
                "keepRule": "resolution",
                "minimumBytes": 0,
            },
            "schemaVersion": 1,
        }

    def file(self, name, width, height, difference, modified):
        path = self.source / name
        path.write_bytes(b"img-" + name.encode())
        return {
            "path": str(path),
            "size": path.stat().st_size,
            "width": width,
            "height": height,
            "modified": modified,
            "difference": difference,
            "previewPath": str(path),
        }

    def test_similar_groups_are_not_preselected_and_exact_copies_stay_visible(self):
        original = self.file("original.png", 40, 20, 0, 10)
        copy = self.file("copy.png", 40, 20, 0, 10)
        turned = self.file("rotated.png", 20, 40, 2, 11)
        result = {
            "exact": [{"files": [original, copy]}],
            "similar": [{"files": [original, turned]}],
            "warnings": [],
            "heicDecoder": "none",
        }
        merged = merge_groups(result)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0][0], "similar")
        self.assertEqual(len(merged[0][1]), 3)

        plan_id = "plan"
        profile = self.profile()
        items = items_from_scan(
            plan_id,
            profile,
            result,
            self.service.planner._item,
            lambda source: self.service.planner._quarantine_destination(plan_id, self.source, source),
        )
        self.assertEqual(len(items), 3)
        self.assertTrue(all(not item["selected"] for item in items))
        self.assertTrue(all(item["metadata"]["decision"] == "undecided" for item in items))
        self.assertEqual(sum(item["metadata"]["recommendedKeep"] for item in items), 1)
        self.assertTrue(all(item["operation"] == "quarantine" for item in items))

    def test_keep_rules_pick_resolution_size_time_and_path(self):
        wide = self.file("wide.png", 100, 50, 1, 1)
        tall = self.file("tall.png", 40, 40, 1, 50)
        huge = self.file("huge.png", 10, 10, 1, 1)
        huge["size"] = 999999
        nested = self.source / "a"
        nested.mkdir()
        short = self.file("z.png", 10, 10, 1, 1)
        long = dict(short)
        long_path = nested / "very-long-name.png"
        long_path.write_bytes(b"same-shape")
        long["path"] = str(long_path)
        cases = {
            "resolution": wide["path"],
            "largest": huge["path"],
            "newest": tall["path"],
            "shortest": short["path"],
        }
        for rule, expected in cases.items():
            profile = self.profile()
            profile["parameters"]["keepRule"] = rule
            files = [wide, tall, huge]
            if rule == "shortest":
                files = [long, short]
            items = items_from_scan(
                "plan",
                profile,
                {"exact": [], "similar": [{"files": files}]},
                self.service.planner._item,
                lambda source: self.service.planner._quarantine_destination("plan", self.source, source),
            )
            kept = next(item for item in items if item["metadata"]["recommendedKeep"])
            self.assertEqual(kept["sourcePath"], expected, rule)

    def test_quarantine_and_undo_for_a_similar_group(self):
        keep = self.source / "keep.png"
        drop = self.source / "drop.png"
        write_png(keep, 32, 32, scene)
        write_png(drop, 32, 32, rotated)
        result = {
            "stopped": False,
            "heicDecoder": "none",
            "warnings": [],
            "exact": [],
            "similar": [{"files": [
                {"path": str(keep), "size": keep.stat().st_size, "width": 32, "height": 32,
                 "modified": 2, "difference": 0, "previewPath": str(keep)},
                {"path": str(drop), "size": drop.stat().st_size, "width": 32, "height": 32,
                 "modified": 1, "difference": 3, "previewPath": str(drop)},
            ]}],
        }
        self.service.planner.scan_similar = lambda *args, **kwargs: result
        plan = self.service.create_plan(self.profile())
        self.assertEqual(plan["summary"]["groups"], 1)
        self.assertEqual(plan["summary"]["selected"], 0)
        self.assertTrue(all(item["metadata"]["decision"] == "undecided" for item in plan["items"]))
        drop_item = next(item for item in plan["items"] if item["source_path"].endswith("drop.png"))
        self.service.select_plan_items(plan["plan_id"], [drop_item["item_id"]])
        executed = self.service.execute(plan["plan_id"])
        self.assertEqual(executed["success"], 1)
        self.assertFalse(drop.exists())
        self.assertTrue(keep.exists())
        quarantined = self.service.quarantine()
        self.assertEqual(len(quarantined), 1)
        self.assertIn("相似", quarantined[0]["reason"])
        preview = self.service.undo_preview(executed["runId"])
        undone = self.service.undo(executed["runId"], [preview["items"][0]["operationId"]])
        self.assertEqual(undone["restored"], 1)
        self.assertTrue(drop.exists())
        self.assertEqual(self.service.quarantine(), [])

    def test_identical_heic_files_are_exact_when_decoder_is_absent(self):
        sample = Path(__file__).resolve().parent / "fixtures" / "sample.heic"
        if not sample.is_file():
            payload = b"not-a-real-heic-but-byte-identical"
        else:
            payload = sample.read_bytes()
        first = self.source / "IMG_0001.HEIC"
        second = self.source / "album" / "IMG_0001.HEIC"
        second.parent.mkdir()
        first.write_bytes(payload)
        second.write_bytes(payload)
        result = {
            "exact": [{"files": [
                {"path": str(first), "size": len(payload), "width": 0, "height": 0, "modified": 5, "difference": 0, "previewPath": str(first)},
                {"path": str(second), "size": len(payload), "width": 0, "height": 0, "modified": 5, "difference": 0, "previewPath": str(second)},
            ]}],
            "similar": [],
            "warnings": ["HEIC_DECODE_UNAVAILABLE"],
            "heicDecoder": "none",
        }
        self.service.planner.scan_similar = lambda *args, **kwargs: result
        plan = self.service.create_plan(self.profile())
        self.assertEqual(plan["summary"]["groups"], 1)
        self.assertEqual(plan["summary"]["heicDecoder"], "none")
        self.assertIn("HEIC_DECODE_UNAVAILABLE", plan["summary"]["warnings"])
        self.assertTrue(all(item["metadata"]["kind"] == "exact" for item in plan["items"]))
        self.assertEqual(plan["summary"]["selected"], 0)

    def test_scan_modes_cannot_both_be_off(self):
        profile = self.profile()
        profile["parameters"]["scanExact"] = False
        profile["parameters"]["scanSimilar"] = False
        codes = {issue["code"] for issue in self.service.validate(profile)["issues"]}
        self.assertIn("INVALID_PARAMETER", codes)

    def test_release_sidecar_finds_rotated_and_flipped_copies(self):
        try:
            binary = similar_photos_binary()
        except EngineError:
            self.skipTest("similar-photos sidecar is not built")
        os.environ["ORGANIZE_SIMILAR_PHOTOS"] = str(binary)
        write_png(self.source / "original.png", 48, 48, scene)
        write_png(self.source / "copy.png", 48, 48, scene)
        write_png(self.source / "rotated.png", 48, 48, rotated)
        write_png(self.source / "flipped.png", 48, 48, flipped)
        write_png(self.source / "other.png", 48, 48, other)
        heic = self.source / "pair.heic"
        heic.write_bytes(b"heic-byte-sample")
        (self.source / "pair-copy.heic").write_bytes(b"heic-byte-sample")
        plan = self.service.create_plan(self.profile())
        groups = {}
        for item in plan["items"]:
            groups.setdefault(item["group_id"], []).append(Path(item["source_path"]).name)
        photo_group = next(
            (names for names in groups.values() if "rotated.png" in names and "flipped.png" in names),
            None,
        )
        self.assertIsNotNone(photo_group, groups)
        self.assertIn("original.png", photo_group)
        self.assertIn("copy.png", photo_group)
        self.assertNotIn("other.png", photo_group)
        heic_group = next((names for names in groups.values() if "pair.heic" in names), None)
        self.assertIsNotNone(heic_group, groups)
        self.assertIn("pair-copy.heic", heic_group)
        self.assertTrue(all(not item["selected"] for item in plan["items"]))


if __name__ == "__main__":
    unittest.main()

import csv
import tempfile
import unittest
from pathlib import Path

import command_log as cl


class TestHelpers(unittest.TestCase):
    def test_detect_language(self):
        cases = (
            ("ดูพื้นที่ดิสก์ที่เหลือ", "th"),
            ("show git status", "en"),
            ("ลบไฟล์ notes.txt", "th"),
            ("translate chicken to ไก่", "mixed"),
            ("12345 !!!", "other"),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(cl.detect_language(text), expected)

    def test_classify_risk(self):
        cases = (
            ("ls -la", "safe"),
            ("rm notes.txt", "risky"),
            ("echo hi > out.txt", "risky"),
            ("sudo rm -rf /", "blocked"),
            ("shutdown -h now", "blocked"),
        )
        for cmd, expected in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(cl.classify_risk(cmd), expected)

    def test_make_row_cleans_text_and_validates(self):
        row = cl.make_row(1, "ดูไฟล์\nทั้งหมด", "ls   -la", "manual", True)
        self.assertEqual(row["request"], "ดูไฟล์ ทั้งหมด")
        self.assertEqual(row["command"], "ls -la")
        self.assertEqual(row["executed"], "yes")
        with self.assertRaises(ValueError):
            cl.make_row(2, "   ", "ls", "manual", False)
        with self.assertRaises(ValueError):
            cl.make_row(3, "x", "ls", "alien", False)


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "log.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_is_created_with_header(self):
        rows, bad = cl.load_rows(self.path)
        self.assertEqual((rows, bad), ([], 0))
        self.assertTrue(self.path.exists())
        with self.path.open(encoding="utf-8") as f:
            self.assertEqual(tuple(next(csv.reader(f))), cl.FIELDS)

    def test_append_and_reload_with_ids(self):
        first = cl.append_model_entry("ดูพอร์ต 8080", "lsof -i :8080", "safe", True, self.path)
        second = cl.append_model_entry("show status", "git status", "safe", False, self.path)
        self.assertEqual((first, second), (1, 2))
        rows, bad = cl.load_rows(self.path)
        self.assertEqual(bad, 0)
        self.assertEqual([r["command"] for r in rows], ["lsof -i :8080", "git status"])
        self.assertEqual(rows[0]["source"], "model")

    def test_commas_and_quotes_survive_round_trip(self):
        cmd = 'grep -rn "a,b" .'
        cl.append_model_entry("ค้นหา a,b", cmd, "safe", False, self.path)
        rows, _ = cl.load_rows(self.path)
        self.assertEqual(rows[0]["command"], cmd)

    def test_set_verdict(self):
        rid = cl.append_model_entry("x", "ls", "safe", False, self.path)
        self.assertTrue(cl.set_verdict(rid, "correct", self.path))
        self.assertFalse(cl.set_verdict(999, "wrong", self.path))
        self.assertEqual(cl.load_rows(self.path)[0][0]["verdict"], "correct")
        with self.assertRaises(ValueError):
            cl.set_verdict(rid, "maybe", self.path)

    def test_bad_rows_are_skipped_not_crashed(self):
        cl.ensure_file(self.path)
        with self.path.open("a", encoding="utf-8", newline="") as f:
            f.write("abc,2026-01-01 00:00:00,en,req,cmd,manual,safe,no,unrated,\n")
            f.write("5,2026-01-01 00:00:00,en,req,cmd,robot,safe,no,unrated,\n")
            f.write("6,2026-01-01 00:00:00,en,req,cmd,manual,safe,no,unrated,ok,EXTRA\n")
            f.write("7,2026-01-01 00:00:00,en,req,ls,manual,safe,no,unrated,ok\n")
        rows, bad = cl.load_rows(self.path)
        self.assertEqual(bad, 3)
        self.assertEqual([r["id"] for r in rows], ["7"])

    def test_wrong_header_raises_friendly_error(self):
        self.path.write_text("foo,bar\n1,2\n", encoding="utf-8")
        with self.assertRaises(cl.DataFileError):
            cl.load_rows(self.path)

    def test_non_utf8_file_raises_friendly_error(self):
        self.path.write_bytes(b"\xff\xfe\x00bad")
        with self.assertRaises(cl.DataFileError):
            cl.load_rows(self.path)


class TestStats(unittest.TestCase):
    def test_accuracy_counts_only_rated_model_rows(self):
        rows = [
            cl.make_row(1, "ดูพอร์ต", "lsof -i :80", "model", True, "correct"),
            cl.make_row(2, "นับไฟล์", "wc -l", "model", True, "wrong"),
            cl.make_row(3, "show status", "git status", "model", False, "correct"),
            cl.make_row(4, "show log", "git log", "model", False, "unrated"),
            cl.make_row(5, "ดูไฟล์", "ls -la", "manual", False, "wrong"),
        ]
        st = cl.compute_stats(rows)
        self.assertEqual((st["rated"], st["correct"]), (3, 2))
        self.assertAlmostEqual(st["accuracy"], 66.666, places=2)
        langs = {lang: (n, round(pct)) for lang, n, pct in st["accuracy_by_language"]}
        self.assertEqual(langs, {"th": (2, 50), "en": (1, 100)})
        self.assertEqual(st["top_commands"][0], ("git", 2))

    def test_no_rated_rows_gives_none(self):
        self.assertIsNone(cl.compute_stats([])["accuracy"])
        self.assertEqual(cl.format_stats(cl.compute_stats([])), ["ยังไม่มีข้อมูล"])


if __name__ == "__main__":
    unittest.main()
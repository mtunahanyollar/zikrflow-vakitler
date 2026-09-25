import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fetch_vakitler import parse_table


class ParseTableTests(unittest.TestCase):
    def test_parses_annual_table(self):
        html = (Path(__file__).parent / "fixtures" / "ankara.html").read_text(encoding="utf-8")
        days = parse_table(html, "tab-2")
        self.assertEqual(len(days), 2)
        self.assertEqual(days[0]["t"], "2026-09-25")
        self.assertEqual(days[0]["imsak"], "05:08")
        self.assertEqual(days[1]["yatsi"], "20:04")

    def test_ignores_other_tabs(self):
        html = '<article id="tab-1"><table><tr><td>25 Eylül 2026</td><td>x</td><td>00:00</td></tr></table></article>'
        self.assertEqual(parse_table(html, "tab-2"), [])

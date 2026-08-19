"""
Yksikkötestit BatCLI:n puhtaalle logiikalle.

Nämä testit eivät vaadi curses-päätettä eivätkä verkkoyhteyttä: BatClient
luodaan ilman __init__:iä (ei curses-alustusta) ja testattavat metodit
käsittelevät vain dataa.

Aja:
    python3 -m unittest discover -s tests
    # tai
    python3 tests/test_batclient.py
"""

import os
import sys
import unittest
from collections import deque

# Lisää projektin juuri importtipolkuun
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import curses  # noqa: E402

import batclient  # noqa: E402
from batclient import BatClient, format_debug_bytes, THEMES, _to_curses_rgb  # noqa: E402


def make_client():
    """Luo BatClient ilman __init__:iä (ei curses-alustusta)."""
    c = BatClient.__new__(BatClient)
    c.writer = None
    c.echo_off = False
    c.user_aliases = {}
    return c


class FormatDebugBytesTest(unittest.TestCase):
    def test_plain_text(self):
        self.assertEqual(format_debug_bytes(b"hi"), "hi")

    def test_iac_ga(self):
        data = bytes([batclient.IAC, batclient.GA])
        self.assertEqual(format_debug_bytes(data), "[IAC GA]")

    def test_iac_will_eor(self):
        data = bytes([batclient.IAC, batclient.WILL, batclient.TELOPT_EOR])
        self.assertEqual(format_debug_bytes(data), "[IAC WILL EOR]")

    def test_control_chars(self):
        self.assertEqual(format_debug_bytes(bytes([10])), "[LF]")
        self.assertEqual(format_debug_bytes(bytes([13])), "[CR]")
        self.assertEqual(format_debug_bytes(bytes([27])), "[ESC]")


class HandleTelnetTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()

    def test_plain_text_passthrough(self):
        text, prompt = self.c.handle_telnet("", b"hello")
        self.assertEqual(text, "hello")
        self.assertFalse(prompt)

    def test_ga_marks_prompt(self):
        text, prompt = self.c.handle_telnet("", bytes([batclient.IAC, batclient.GA]))
        self.assertEqual(text, "")
        self.assertTrue(prompt)

    def test_eor_marks_prompt(self):
        text, prompt = self.c.handle_telnet("", bytes([batclient.IAC, batclient.EOR]))
        self.assertEqual(text, "")
        self.assertTrue(prompt)

    def test_text_then_ga(self):
        data = b"abc" + bytes([batclient.IAC, batclient.GA])
        text, prompt = self.c.handle_telnet("", data)
        self.assertEqual(text, "abc")
        self.assertTrue(prompt)

    def test_escaped_iac(self):
        # IAC IAC -> yksi 0xFF tavu (ei komento)
        text, prompt = self.c.handle_telnet("", bytes([batclient.IAC, batclient.IAC]))
        self.assertEqual(text, "\xff")
        self.assertFalse(prompt)

    def test_do_eor_without_writer(self):
        # Ei kaadu vaikka writer puuttuu; komento kuluu eikä jää tekstiin
        data = bytes([batclient.IAC, batclient.DO, batclient.TELOPT_EOR])
        text, prompt = self.c.handle_telnet("", data)
        self.assertEqual(text, "")
        self.assertFalse(prompt)

    def test_will_echo_sets_echo_off(self):
        data = bytes([batclient.IAC, batclient.WILL, batclient.TELOPT_ECHO])
        self.c.handle_telnet("", data)
        self.assertTrue(self.c.echo_off)

    def test_subnegotiation_skipped(self):
        data = bytes([batclient.IAC, batclient.SB, 1, 2, 3,
                      batclient.IAC, batclient.SE])
        text, prompt = self.c.handle_telnet("", data)
        self.assertEqual(text, "")
        self.assertFalse(prompt)


class ExpandAliasTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()

    def test_no_aliases_returns_input(self):
        self.assertEqual(self.c.expand_alias("kk"), "kk")

    def test_alias_without_args(self):
        self.c.user_aliases = {"kk": "kill kobold"}
        self.assertEqual(self.c.expand_alias("kk"), "kill kobold")

    def test_alias_with_args(self):
        self.c.user_aliases = {"kk": "kill"}
        self.assertEqual(self.c.expand_alias("kk kobold"), "kill kobold")

    def test_non_alias_unchanged(self):
        self.c.user_aliases = {"kk": "kill kobold"}
        self.assertEqual(self.c.expand_alias("look"), "look")

    def test_empty_input(self):
        self.c.user_aliases = {"kk": "kill kobold"}
        self.assertEqual(self.c.expand_alias(""), "")


class StripAnsiTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()

    def test_removes_color_codes(self):
        self.assertEqual(self.c.strip_ansi("\x1b[31mhi\x1b[0m"), "hi")

    def test_plain_unchanged(self):
        self.assertEqual(self.c.strip_ansi("plain"), "plain")


class ParseAnsiTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()

    def test_plain_text_single_segment(self):
        result = self.c.parse_ansi("hello")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "hello")
        self.assertEqual(result[0][1], curses.A_NORMAL)

    def test_reset_code_stripped(self):
        result = self.c.parse_ansi("\x1b[0mhi")
        text = "".join(seg for seg, _ in result)
        self.assertEqual(text, "hi")


class ResolveHostPortTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        self.c.env = {}

    def test_defaults_when_env_empty(self):
        self.assertEqual(self.c.resolve_host_port(), (batclient.HOST, batclient.PORT))

    def test_uses_env_values(self):
        self.c.env = {"BATMUD_HOST": "example.org", "BATMUD_PORT": "2000"}
        self.assertEqual(self.c.resolve_host_port(), ("example.org", 2000))

    def test_invalid_port_falls_back(self):
        self.c.env = {"BATMUD_HOST": "example.org", "BATMUD_PORT": "abc"}
        host, port = self.c.resolve_host_port()
        self.assertEqual(host, "example.org")
        self.assertEqual(port, batclient.PORT)


class ThemeDataTest(unittest.TestCase):
    def test_default_theme_exists(self):
        self.assertIn("default", THEMES)

    def test_every_theme_has_8_valid_colors(self):
        for name, theme in THEMES.items():
            colors = theme.get("colors")
            self.assertIsNotNone(colors, name)
            self.assertEqual(len(colors), 8, name)
            for rgb in colors:
                self.assertEqual(len(rgb), 3, name)
                for v in rgb:
                    self.assertTrue(0 <= v <= 255, f"{name}: {v}")

    def test_to_curses_rgb_scaling(self):
        self.assertEqual(_to_curses_rgb(0), 0)
        self.assertEqual(_to_curses_rgb(255), 1000)
        self.assertTrue(0 <= _to_curses_rgb(128) <= 1000)


class WrapSegmentsTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()

    def test_short_line_stays_one_row(self):
        rows = self.c.wrap_segments([("hello", 0)], 20)
        self.assertEqual(rows, [[("hello", 0)]])

    def test_empty_segments_produce_one_empty_row(self):
        # Tyhja rivi ei saa kadota naytolta
        self.assertEqual(self.c.wrap_segments([], 20), [[]])

    def test_exact_width_stays_one_row(self):
        rows = self.c.wrap_segments([("abcd", 0)], 4)
        self.assertEqual(rows, [[("abcd", 0)]])

    def test_breaks_at_word_boundary(self):
        rows = self.c.wrap_segments([("aaa bbb ccc", 0)], 7)
        self.assertEqual(rows, [[("aaa bbb", 0)], [("ccc", 0)]])

    def test_break_drops_the_space_at_wrap_point(self):
        rows = self.c.wrap_segments([("hello world", 0)], 8)
        self.assertEqual(rows, [[("hello", 0)], [("world", 0)]])

    def test_long_word_is_hard_broken(self):
        rows = self.c.wrap_segments([("abcdefghij", 0)], 4)
        self.assertEqual(rows, [[("abcd", 0)], [("efgh", 0)], [("ij", 0)]])

    def test_attribute_survives_continuation_rows(self):
        rows = self.c.wrap_segments([("abcdefghij", curses.A_BOLD)], 4)
        for row in rows:
            for _text, attr in row:
                self.assertEqual(attr, curses.A_BOLD)

    def test_break_between_segments_keeps_both_attributes(self):
        segments = [("hello ", curses.A_BOLD), ("world", curses.A_UNDERLINE)]
        rows = self.c.wrap_segments(segments, 8)
        self.assertEqual(
            rows,
            [[("hello", curses.A_BOLD)], [("world", curses.A_UNDERLINE)]],
        )

    def test_tab_is_expanded_to_the_next_tab_stop(self):
        rows = self.c.wrap_segments([("ab\tcd", 0)], 20)
        self.assertEqual(rows, [[("ab      cd", 0)]])

    def test_tabs_count_toward_the_width(self):
        # Sarkaimet levittyvat ruudulla, joten ne on laskettava mukaan
        rows = self.c.wrap_segments([("ab\tcd\tef\tgh", 0)], 12)
        self.assertGreater(len(rows), 1)
        for row in rows:
            self.assertLessEqual(sum(len(t) for t, _a in row), 12)

    def test_no_row_exceeds_width(self):
        text = "The quick brown fox jumps over the lazy dog again and again"
        rows = self.c.wrap_segments([(text, 0)], 12)
        for row in rows:
            self.assertLessEqual(sum(len(t) for t, _a in row), 12)


class CountingLines:
    """Rivipuskuri joka laskee montako riviä siitä oikeasti luettiin."""

    def __init__(self, lines):
        self._lines = list(lines)
        self.consumed = 0

    def __len__(self):
        return len(self._lines)

    def __reversed__(self):
        for line in reversed(self._lines):
            self.consumed += 1
            yield line


class BuildDisplayRowsTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()

    def test_short_lines_give_one_row_each(self):
        self.c.output_lines = deque(["aa", "bb", "cc"])
        rows = self.c.build_display_rows(20)
        self.assertEqual(len(rows), 3)

    def test_long_line_expands_to_several_rows(self):
        self.c.output_lines = deque(["aaa bbb ccc"])
        rows = self.c.build_display_rows(7)
        self.assertEqual(len(rows), 2)

    def test_max_rows_keeps_the_newest_rows(self):
        self.c.output_lines = deque(["old", "new"])
        rows = self.c.build_display_rows(20, max_rows=1)
        self.assertEqual(rows, [[("new", 0)]])

    def test_only_reads_as_many_lines_as_max_rows_needs(self):
        # PgUp nojaa tahan: vierityksen hinta on suhteessa vierityssyvyyteen,
        # ei puskurin kokoon (10 000 rivin lapikaynti nakyisi viiveena)
        lines = CountingLines(["rivi %d" % i for i in range(1000)])
        self.c.output_lines = lines
        rows = self.c.build_display_rows(20, max_rows=3)
        self.assertEqual(len(rows), 3)
        self.assertLessEqual(lines.consumed, 4)

    def test_ansi_codes_are_not_counted_as_width(self):
        # Varilliset koodit vaatisivat initscr():n, joten kaytetaan bold-koodia
        self.c.output_lines = deque(["\x1b[1mabcd\x1b[0m"])
        rows = self.c.build_display_rows(4)
        self.assertEqual(len(rows), 1)


class MaxScrollOffsetTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        self.c.height = 5  # output-ikkuna on 3 rivia korkea
        self.c.width = 6   # wrapataan 5 sarakkeeseen

    def test_zero_when_everything_fits(self):
        self.c.output_lines = deque(["aa", "bb"])
        self.assertEqual(self.c.max_scroll_offset(), 0)

    def test_counts_wrapped_rows_not_logical_lines(self):
        # Yksi looginen rivi joka wrappautuu neljalle naytoriville
        self.c.output_lines = deque(["aaaa bbbb cccc dddd"])  # 4 x 4 merkkia
        self.assertEqual(self.c.max_scroll_offset(), 1)

class FakeWindow:
    """Minimaalinen curses-ikkunan korvike: kerää mitä ruudulle piirrettiin."""

    def __init__(self):
        self.cells = {}

    def erase(self):
        self.cells = {}

    def addstr(self, y, x, text, attr=0):
        self.cells.setdefault(y, []).append((x, text))

    def noutrefresh(self):
        pass

    def drawn(self):
        """Piirretyt rivit ylhäältä alas merkkijonoina"""
        return [
            "".join(t for _x, t in sorted(self.cells[y]))
            for y in sorted(self.cells)
        ]


class RefreshOutputTest(unittest.TestCase):
    def setUp(self):
        self.c = make_client()
        self.c.height = 5  # output-ikkuna 3 riviä
        self.c.width = 8   # wrapataan 7 sarakkeeseen
        self.c.scroll_offset = 0
        self.c.output_win = FakeWindow()

    def test_long_line_is_wrapped_not_truncated(self):
        self.c.output_lines = deque(["aaa bbb ccc"])
        self.c.refresh_output()
        self.assertEqual(self.c.output_win.drawn(), ["aaa bbb", "ccc"])

    def test_only_the_newest_rows_fit_on_screen(self):
        self.c.output_lines = deque(["aa", "bb", "cc", "dd"])
        self.c.refresh_output()
        self.assertEqual(self.c.output_win.drawn(), ["bb", "cc", "dd"])

    def test_scroll_offset_shows_older_rows(self):
        self.c.output_lines = deque(["aa", "bb", "cc", "dd"])
        self.c.scroll_offset = 1
        self.c.refresh_output()
        self.assertEqual(self.c.output_win.drawn(), ["aa", "bb", "cc"])

    def test_scroll_offset_is_clamped_to_available_rows(self):
        self.c.output_lines = deque(["aa", "bb"])
        self.c.scroll_offset = 10
        self.c.refresh_output()
        self.assertEqual(self.c.scroll_offset, 0)
        self.assertEqual(self.c.output_win.drawn(), ["aa", "bb"])


if __name__ == "__main__":
    unittest.main()

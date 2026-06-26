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


if __name__ == "__main__":
    unittest.main()

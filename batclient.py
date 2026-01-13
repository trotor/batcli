#!/usr/bin/env python3
"""
BatMUD Terminal Client
Yksinkertainen telnet-client BatMUD-peliin (bat.org:23)
"""

import asyncio
import curses
import sys
import re
import os
from collections import deque
from pathlib import Path

# BatMUD palvelimen tiedot
HOST = "bat.org"
PORT = 23


def load_env():
    """Lataa .env tiedosto"""
    env_path = Path(__file__).parent / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    # Poista mahdolliset lainausmerkit
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value

    return env_vars

# ANSI värikoodit -> curses värit
ANSI_COLORS = {
    30: curses.COLOR_BLACK,
    31: curses.COLOR_RED,
    32: curses.COLOR_GREEN,
    33: curses.COLOR_YELLOW,
    34: curses.COLOR_BLUE,
    35: curses.COLOR_MAGENTA,
    36: curses.COLOR_CYAN,
    37: curses.COLOR_WHITE,
    90: curses.COLOR_BLACK,    # Bright black (gray)
    91: curses.COLOR_RED,      # Bright red
    92: curses.COLOR_GREEN,    # Bright green
    93: curses.COLOR_YELLOW,   # Bright yellow
    94: curses.COLOR_BLUE,     # Bright blue
    95: curses.COLOR_MAGENTA,  # Bright magenta
    96: curses.COLOR_CYAN,     # Bright cyan
    97: curses.COLOR_WHITE,    # Bright white
}


class BatClient:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.input_buffer = ""
        self.cursor_pos = 0  # Kursorin paikka input_bufferissa
        self.output_lines = deque(maxlen=10000)
        self.scroll_offset = 0
        self.reader = None
        self.writer = None
        self.command_history = deque(maxlen=100)
        self.history_index = -1

        # Lataa .env asetukset
        self.env = load_env()
        self.username = self.env.get('BATMUD_USER', '')
        self.password = self.env.get('BATMUD_PASS', '')

        # Curses asetukset
        curses.start_color()
        curses.use_default_colors()

        # Luo väriparit (fg, bg)
        for i in range(1, 16):
            curses.init_pair(i, i % 8, -1)

        # Lisää väriparit kirkkailla väreillä
        curses.init_pair(16, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Status bar

        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        curses.curs_set(1)

        self.setup_windows()

    def setup_windows(self):
        """Luo ikkunat: output ylhäällä, input alhaalla"""
        self.height, self.width = self.stdscr.getmaxyx()

        # Output-ikkuna (kaikki paitsi 2 viimeistä riviä)
        self.output_win = curses.newwin(self.height - 2, self.width, 0, 0)
        self.output_win.scrollok(True)
        self.output_win.idlok(True)

        # Status bar
        self.status_win = curses.newwin(1, self.width, self.height - 2, 0)
        self.status_win.bkgd(' ', curses.color_pair(16))

        # Input-ikkuna (viimeinen rivi)
        self.input_win = curses.newwin(1, self.width, self.height - 1, 0)
        self.input_win.keypad(True)
        self.input_win.nodelay(True)

    def parse_ansi(self, text):
        """Parsii ANSI-koodit ja palauttaa listan (teksti, attribuutit) pareja"""
        result = []
        current_attr = curses.A_NORMAL
        current_fg = -1
        bold = False

        # ANSI escape sequence pattern
        ansi_pattern = re.compile(r'\x1b\[([0-9;]*)m')

        pos = 0
        for match in ansi_pattern.finditer(text):
            # Lisää teksti ennen ANSI-koodia
            if match.start() > pos:
                plain_text = text[pos:match.start()]
                attr = current_attr
                if current_fg >= 0:
                    color_pair = (current_fg % 8) + 1
                    attr |= curses.color_pair(color_pair)
                    if bold or current_fg >= 90:
                        attr |= curses.A_BOLD
                result.append((plain_text, attr))

            # Käsittele ANSI-koodi
            codes = match.group(1).split(';') if match.group(1) else ['0']
            for code in codes:
                try:
                    code_int = int(code) if code else 0
                except ValueError:
                    code_int = 0

                if code_int == 0:  # Reset
                    current_attr = curses.A_NORMAL
                    current_fg = -1
                    bold = False
                elif code_int == 1:  # Bold
                    bold = True
                elif code_int == 4:  # Underline
                    current_attr |= curses.A_UNDERLINE
                elif code_int == 7:  # Reverse
                    current_attr |= curses.A_REVERSE
                elif 30 <= code_int <= 37 or 90 <= code_int <= 97:  # Foreground
                    current_fg = code_int
                elif code_int == 39:  # Default foreground
                    current_fg = -1

            pos = match.end()

        # Lisää loppu teksti
        if pos < len(text):
            plain_text = text[pos:]
            attr = current_attr
            if current_fg >= 0:
                color_pair = (current_fg % 8) + 1
                attr |= curses.color_pair(color_pair)
                if bold or current_fg >= 90:
                    attr |= curses.A_BOLD
            result.append((plain_text, attr))

        return result

    def add_output(self, text):
        """Lisää tekstiä output-ikkunaan"""
        # Käsittele rivinvaihdot
        lines = text.split('\n')
        for line in lines:
            # Poista muut kontrollimerkit paitsi ANSI
            clean_line = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1a\x1c-\x1f]', '', line)
            self.output_lines.append(clean_line)

        self.refresh_output()

    def refresh_output(self):
        """Päivitä output-ikkuna"""
        self.output_win.erase()

        output_height = self.height - 2
        total_lines = len(self.output_lines)

        # Laske näytettävät rivit
        start_line = max(0, total_lines - output_height - self.scroll_offset)
        end_line = min(total_lines, start_line + output_height)

        visible_lines = list(self.output_lines)[start_line:end_line]

        for i, line in enumerate(visible_lines):
            if i >= output_height:
                break
            try:
                parsed = self.parse_ansi(line)
                col = 0
                for text, attr in parsed:
                    if col >= self.width - 1:
                        break
                    # Rajoita tekstin pituus
                    max_len = self.width - col - 1
                    text = text[:max_len]
                    try:
                        self.output_win.addstr(i, col, text, attr)
                    except curses.error:
                        pass
                    col += len(text)
            except curses.error:
                pass

        self.output_win.refresh()

    def refresh_status(self):
        """Päivitä status bar"""
        self.status_win.erase()
        status = f" BatMUD Client | {HOST}:{PORT} | Lines: {len(self.output_lines)}"
        if self.scroll_offset > 0:
            status += f" | Scroll: -{self.scroll_offset}"
        try:
            self.status_win.addstr(0, 0, status[:self.width-1], curses.color_pair(16) | curses.A_BOLD)
        except curses.error:
            pass
        self.status_win.refresh()

    def refresh_input(self):
        """Päivitä input-ikkuna"""
        self.input_win.erase()
        prompt = "> "
        available_width = self.width - len(prompt) - 1

        try:
            self.input_win.addstr(0, 0, prompt)

            # Laske mikä osa bufferista näytetään
            # Varmista että kursori on aina näkyvissä
            if self.cursor_pos < available_width:
                # Kursori mahtuu näkyviin alusta
                start = 0
                visible_input = self.input_buffer[:available_width]
                cursor_screen_pos = self.cursor_pos
            else:
                # Scrollaa niin että kursori näkyy
                start = self.cursor_pos - available_width + 1
                visible_input = self.input_buffer[start:start + available_width]
                cursor_screen_pos = available_width - 1

            self.input_win.addstr(0, len(prompt), visible_input)
            self.input_win.move(0, len(prompt) + cursor_screen_pos)
        except curses.error:
            pass
        self.input_win.refresh()

    async def connect(self):
        """Yhdistä BatMUD-palvelimeen"""
        self.add_output(f"Yhdistetään palvelimeen {HOST}:{PORT}...")
        try:
            self.reader, self.writer = await asyncio.open_connection(HOST, PORT)
            self.add_output("Yhteys muodostettu!\n")
            return True
        except Exception as e:
            self.add_output(f"Yhteysvirhe: {e}\n")
            return False

    async def auto_login(self):
        """Automaattinen kirjautuminen .env tiedoista"""
        if self.username and self.password:
            self.add_output("Automaattinen kirjautuminen...\n")
            # Odota hetki että palvelin on valmis
            await asyncio.sleep(1.0)
            await self.send_command(self.username)
            await asyncio.sleep(0.5)
            await self.send_command(self.password)
        elif self.username:
            await asyncio.sleep(1.0)
            await self.send_command(self.username)

    async def read_from_server(self):
        """Lue dataa palvelimelta"""
        try:
            while self.running:
                try:
                    data = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=0.1
                    )
                    if not data:
                        self.add_output("\n*** Yhteys katkennut ***\n")
                        self.running = False
                        break

                    # Dekoodaa ISO-8859-1 (BatMUD käyttää tätä)
                    text = data.decode('iso-8859-1', errors='replace')

                    # Käsittele telnet-komennot (IAC)
                    text = self.handle_telnet(text, data)

                    self.add_output(text)
                    self.refresh_status()

                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    self.add_output(f"\nLukuvirhe: {e}\n")
                    break
        except asyncio.CancelledError:
            pass

    def handle_telnet(self, text, raw_data):
        """Käsittele telnet-protokollan komennot"""
        # Yksinkertainen IAC-käsittely
        # IAC = 255, WILL = 251, WONT = 252, DO = 253, DONT = 254
        result = []
        i = 0
        data = list(raw_data)

        while i < len(data):
            if data[i] == 255 and i + 1 < len(data):  # IAC
                if data[i + 1] == 255:  # Escaped IAC
                    result.append(255)
                    i += 2
                elif data[i + 1] in (251, 252, 253, 254) and i + 2 < len(data):
                    # WILL/WONT/DO/DONT - vastaa WONT/DONT
                    cmd = data[i + 1]
                    opt = data[i + 2]

                    if cmd == 253:  # DO -> vastaa WONT
                        response = bytes([255, 252, opt])
                        if self.writer:
                            self.writer.write(response)
                    elif cmd == 251:  # WILL -> vastaa DONT
                        response = bytes([255, 254, opt])
                        if self.writer:
                            self.writer.write(response)

                    i += 3
                else:
                    i += 2
            else:
                result.append(data[i])
                i += 1

        return bytes(result).decode('iso-8859-1', errors='replace')

    async def send_command(self, cmd):
        """Lähetä komento palvelimelle"""
        if self.writer:
            try:
                self.writer.write((cmd + "\n").encode('iso-8859-1'))
                await self.writer.drain()

                # Lisää komentoon historiaan
                if cmd.strip():
                    self.command_history.append(cmd)
                    self.history_index = -1
            except Exception as e:
                self.add_output(f"\nLähetysvirhe: {e}\n")

    async def handle_input(self):
        """Käsittele käyttäjän syöte"""
        try:
            while self.running:
                try:
                    # Käytä get_wch() unicode-tukeen
                    try:
                        key = self.input_win.get_wch()
                    except curses.error:
                        await asyncio.sleep(0.01)
                        continue

                    # get_wch palauttaa joko int (erikoisnäppäin) tai str (merkki)
                    if isinstance(key, str):
                        char = key
                        keycode = ord(char)
                    else:
                        char = None
                        keycode = key

                    if keycode == curses.KEY_RESIZE:
                        self.setup_windows()
                        self.refresh_output()
                        self.refresh_status()
                        self.refresh_input()

                    elif keycode in (curses.KEY_ENTER, 10, 13):  # Enter
                        if self.input_buffer.strip().lower() == '/quit':
                            self.add_output("\n*** Suljetaan client... ***\n")
                            self.running = False
                            break
                        await self.send_command(self.input_buffer)
                        self.input_buffer = ""
                        self.cursor_pos = 0
                        self.scroll_offset = 0
                        self.refresh_input()
                        self.refresh_output()

                    elif keycode in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
                        if self.cursor_pos > 0:
                            self.input_buffer = (
                                self.input_buffer[:self.cursor_pos - 1] +
                                self.input_buffer[self.cursor_pos:]
                            )
                            self.cursor_pos -= 1
                            self.refresh_input()

                    elif keycode == curses.KEY_DC:  # Delete
                        if self.cursor_pos < len(self.input_buffer):
                            self.input_buffer = (
                                self.input_buffer[:self.cursor_pos] +
                                self.input_buffer[self.cursor_pos + 1:]
                            )
                            self.refresh_input()

                    elif keycode == curses.KEY_LEFT:  # Nuoli vasemmalle - kursori vasemmalle
                        if self.cursor_pos > 0:
                            self.cursor_pos -= 1
                            self.refresh_input()

                    elif keycode == curses.KEY_RIGHT:  # Nuoli oikealle - kursori oikealle
                        if self.cursor_pos < len(self.input_buffer):
                            self.cursor_pos += 1
                            self.refresh_input()

                    elif keycode == curses.KEY_UP:  # Nuoli ylös - rivin alkuun
                        self.cursor_pos = 0
                        self.refresh_input()

                    elif keycode == curses.KEY_DOWN:  # Nuoli alas - rivin loppuun
                        self.cursor_pos = len(self.input_buffer)
                        self.refresh_input()

                    elif keycode == 16:  # Ctrl-P - edellinen historia
                        if self.command_history:
                            if self.history_index < len(self.command_history) - 1:
                                self.history_index += 1
                                self.input_buffer = self.command_history[-(self.history_index + 1)]
                                self.cursor_pos = len(self.input_buffer)
                                self.refresh_input()

                    elif keycode == 14:  # Ctrl-N - seuraava historia
                        if self.history_index > 0:
                            self.history_index -= 1
                            self.input_buffer = self.command_history[-(self.history_index + 1)]
                            self.cursor_pos = len(self.input_buffer)
                        elif self.history_index == 0:
                            self.history_index = -1
                            self.input_buffer = ""
                            self.cursor_pos = 0
                        self.refresh_input()

                    elif keycode == 1:  # Ctrl-A - rivin alkuun
                        self.cursor_pos = 0
                        self.refresh_input()

                    elif keycode == 5:  # Ctrl-E - rivin loppuun
                        self.cursor_pos = len(self.input_buffer)
                        self.refresh_input()

                    elif keycode == 21:  # Ctrl-U - tyhjennä rivi
                        self.input_buffer = ""
                        self.cursor_pos = 0
                        self.refresh_input()

                    elif keycode == 11:  # Ctrl-K - poista kursorista loppuun
                        self.input_buffer = self.input_buffer[:self.cursor_pos]
                        self.refresh_input()

                    elif keycode == curses.KEY_PPAGE:  # Page Up - scroll
                        self.scroll_offset = min(
                            self.scroll_offset + (self.height - 3),
                            max(0, len(self.output_lines) - (self.height - 2))
                        )
                        self.refresh_output()
                        self.refresh_status()

                    elif keycode == curses.KEY_NPAGE:  # Page Down - scroll
                        self.scroll_offset = max(0, self.scroll_offset - (self.height - 3))
                        self.refresh_output()
                        self.refresh_status()

                    elif keycode == curses.KEY_HOME:  # Home - scroll alkuun
                        self.scroll_offset = max(0, len(self.output_lines) - (self.height - 2))
                        self.refresh_output()
                        self.refresh_status()

                    elif keycode == curses.KEY_END:  # End - scroll loppuun
                        self.scroll_offset = 0
                        self.refresh_output()
                        self.refresh_status()

                    elif keycode == 27:  # ESC - ei tehdä mitään (tai voi poistua)
                        pass

                    elif char is not None and char.isprintable():  # Unicode-merkki
                        self.input_buffer = (
                            self.input_buffer[:self.cursor_pos] +
                            char +
                            self.input_buffer[self.cursor_pos:]
                        )
                        self.cursor_pos += 1
                        self.refresh_input()

                except curses.error:
                    await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            pass

    async def run(self):
        """Pääsilmukka"""
        self.refresh_output()
        self.refresh_status()
        self.refresh_input()

        if not await self.connect():
            self.add_output("Paina ESC poistuaksesi.")
            while self.running:
                key = self.input_win.getch()
                if key == 27:
                    break
                await asyncio.sleep(0.1)
            return

        # Käynnistä tehtävät
        read_task = asyncio.create_task(self.read_from_server())
        input_task = asyncio.create_task(self.handle_input())
        login_task = asyncio.create_task(self.auto_login())

        try:
            await asyncio.gather(read_task, input_task)
        except asyncio.CancelledError:
            pass
        finally:
            read_task.cancel()
            input_task.cancel()

            if self.writer:
                self.writer.close()
                try:
                    await self.writer.wait_closed()
                except:
                    pass


def main(stdscr):
    """Main wrapper curses:lle"""
    asyncio.run(BatClient(stdscr).run())


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Virhe: {e}")
        sys.exit(1)

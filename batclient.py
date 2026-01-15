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

import cmds

# BatMUD palvelimen tiedot
HOST = "bat.org"
PORT = 23
VERSION = "0.8.6"

# Telnet protokolla konstantit
IAC = 255   # Interpret As Command
GA = 249    # Go Ahead (prompt marker)
EOR = 239   # End Of Record (prompt marker)
SB = 250    # Subnegotiation Begin
SE = 240    # Subnegotiation End
WILL = 251
WONT = 252
DO = 253
DONT = 254
TELOPT_EOR = 25  # End of Record option
TELOPT_ECHO = 1  # Echo option


# Telnet-komentojen nimet debug-tulostukseen
TELNET_NAMES = {
    255: 'IAC', 254: 'DONT', 253: 'DO', 252: 'WONT', 251: 'WILL',
    250: 'SB', 249: 'GA', 248: 'EL', 247: 'EC', 246: 'AYT',
    245: 'AO', 244: 'IP', 243: 'BRK', 242: 'DM', 241: 'NOP',
    240: 'SE', 239: 'EOR',
}

TELOPT_NAMES = {
    0: 'BINARY', 1: 'ECHO', 3: 'SGA', 24: 'TTYPE', 25: 'EOR',
    31: 'NAWS', 32: 'TSPEED', 33: 'RFLOW', 34: 'LINEMODE',
    39: 'NEWENV', 85: 'COMPRESS', 86: 'COMPRESS2', 201: 'GMCP',
}


def format_debug_bytes(data):
    """Muotoile raakadata luettavaan muotoon erikoismerkeillä"""
    result = []
    i = 0
    data_list = list(data)

    while i < len(data_list):
        b = data_list[i]

        if b == IAC and i + 1 < len(data_list):
            next_b = data_list[i + 1]

            if next_b in TELNET_NAMES:
                cmd_name = TELNET_NAMES[next_b]

                # Jos on WILL/WONT/DO/DONT, näytä myös optio
                if next_b in (WILL, WONT, DO, DONT) and i + 2 < len(data_list):
                    opt = data_list[i + 2]
                    opt_name = TELOPT_NAMES.get(opt, str(opt))
                    result.append(f"[IAC {cmd_name} {opt_name}]")
                    i += 3
                else:
                    result.append(f"[IAC {cmd_name}]")
                    i += 2
            else:
                result.append(f"[IAC {next_b}]")
                i += 2
        elif b == 27:  # ESC
            result.append("[ESC]")
            i += 1
        elif b == 10:
            result.append("[LF]")
            i += 1
        elif b == 13:
            result.append("[CR]")
            i += 1
        elif b == 8:
            result.append("[BS]")
            i += 1
        elif b < 32 or b == 127:
            result.append(f"[{b}]")
            i += 1
        else:
            # Tavallinen merkki
            try:
                result.append(chr(b))
            except:
                result.append(f"[{b}]")
            i += 1

    return "".join(result)


def load_env():
    """Lataa .env tiedosto"""
    # resolve() seuraa symlinkit todelliseen sijaintiin
    env_path = Path(__file__).resolve().parent / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    # Poista inline-kommentit (# ja sen jälkeen)
                    if '#' in value:
                        value = value.split('#')[0]
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
        self.mud_prompt = ""  # MUD:n lähettämä prompt (IAC GA/EOR jälkeen)
        self.partial_line = ""  # Keskeneräinen rivi (ei vielä \n tai IAC GA/EOR)
        self.debug_mode = False  # Debug-tila näyttää raakadatan
        self.version = VERSION  # Versio helppiä varten
        self.log_file = None  # Lokitiedosto (avattu file handle)
        self.log_filename = None  # Lokitiedoston polku
        self.user_aliases = {}  # Käyttäjän aliakset {nimi: komento}
        self.echo_off = False  # Salasanatila (TELOPT ECHO)
        self.exit_message = None  # Viesti joka näytetään ohjelman lopussa

        # Lataa .env asetukset
        self.env = load_env()
        self.username = self.env.get('BATMUD_USER', '')
        self.password = self.env.get('BATMUD_PASS', '')
        self.auto_log = self.env.get('AUTO_LOG', '').lower() == 'true'
        self.log_dir = self.env.get('LOG_DIR', '')

        # Curses asetukset
        curses.start_color()
        curses.use_default_colors()

        # Luo väriparit (fg, bg)
        for i in range(1, 16):
            curses.init_pair(i, i % 8, -1)

        # Lisää väriparit kirkkailla väreillä
        curses.init_pair(16, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Status bar

        curses.halfdelay(1)  # Palauta get_wch():stä 100ms jälkeen
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
        # Poista CR (telnet käyttää CR+LF, meille riittää LF)
        text = text.replace('\r', '')

        # Kirjoita lokiin (ilman ANSI-koodeja)
        if self.log_file:
            try:
                clean_text = self.strip_ansi(text)
                self.log_file.write(clean_text)
                self.log_file.flush()
            except Exception:
                pass  # Älä kaada ohjelmaa loggausvirheeseen

        # Käsittele rivinvaihdot
        lines = text.split('\n')

        # Jos teksti päättyi \n, viimeinen elementti on tyhjä - älä lisää sitä
        if lines and lines[-1] == '':
            lines = lines[:-1]

        for line in lines:
            # Poista muut kontrollimerkit paitsi ANSI (ESC)
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

        self.output_win.noutrefresh()

    def refresh_status(self):
        """Päivitä status bar"""
        self.status_win.erase()
        status = f" BatCLI {VERSION} | {HOST}:{PORT}"
        if self.log_file:
            status += " | LOG"
        if self.debug_mode:
            status += " | DBG"
        if self.scroll_offset > 0:
            status += f" | ↑{self.scroll_offset}"
        # Täytä koko rivi välilyönneillä jotta tausta on yhtenäinen
        status = status.ljust(self.width - 1)
        try:
            self.status_win.addstr(0, 0, status, curses.color_pair(16) | curses.A_BOLD)
        except curses.error:
            pass
        self.status_win.noutrefresh()

    def strip_ansi(self, text):
        """Poista ANSI-koodit tekstistä"""
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    def get_prompt_display_length(self):
        """Laske promptin näyttöpituus (ilman ANSI-koodeja)"""
        return len(self.strip_ansi(self.mud_prompt))

    def refresh_input(self):
        """Päivitä input-ikkuna MUD-promptilla"""
        self.input_win.erase()

        # Käytä MUD:n promptia jos se on asetettu, muuten "> "
        if self.mud_prompt:
            # Näytä prompt väreineen
            prompt_col = 0
            parsed = self.parse_ansi(self.mud_prompt)
            for text, attr in parsed:
                try:
                    max_len = self.width - prompt_col - 1
                    text = text[:max_len]
                    self.input_win.addstr(0, prompt_col, text, attr)
                    prompt_col += len(text)
                except curses.error:
                    pass
            prompt_len = prompt_col
        else:
            prompt = "> "
            try:
                self.input_win.addstr(0, 0, prompt)
            except curses.error:
                pass
            prompt_len = len(prompt)

        available_width = self.width - prompt_len - 1

        try:
            # Salasanatilassa ei näytetä syötettä
            if self.echo_off:
                self.input_win.move(0, prompt_len)
            else:
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

                self.input_win.addstr(0, prompt_len, visible_input)
                self.input_win.move(0, prompt_len + cursor_screen_pos)
        except curses.error:
            pass
        self.input_win.touchwin()  # Merkitse ikkuna muuttuneeksi
        self.input_win.refresh()

    async def connect(self):
        """Yhdistä BatMUD-palvelimeen"""
        self.add_output(f"*** Yhdistetään palvelimeen {HOST}:{PORT}... ***\n")
        curses.doupdate()  # Päivitä näyttö heti
        try:
            # Yhteyden muodostus timeoutilla (10 sekuntia)
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(HOST, PORT),
                timeout=10.0
            )
            self.add_output("*** TCP-yhteys muodostettu, odotetaan palvelimen vastausta... ***\n")
            curses.doupdate()  # Päivitä näyttö heti

            # Odota ensimmäistä dataa palvelimelta (15 sekuntia)
            try:
                first_data = await asyncio.wait_for(
                    self.reader.read(1024),
                    timeout=15.0
                )
                if not first_data:
                    self.add_output("*** Palvelin sulki yhteyden - BatMUD saattaa olla alhaalla ***\n")
                    return False

                # Palvelin vastasi - käsittele ensimmäinen data
                self.add_output("*** Yhteys muodostettu! ***\n")

                # Käsittele saatu data normaalisti
                if self.debug_mode:
                    debug_str = format_debug_bytes(first_data)
                    self.add_output(f"[DEBUG] {debug_str}\n")

                text, prompt_detected = self.handle_telnet("", first_data)
                if text:
                    self.add_output(text)
                if prompt_detected:
                    last_newline = text.rfind('\n')
                    if last_newline >= 0:
                        self.mud_prompt = text[last_newline + 1:]
                    else:
                        self.mud_prompt = text
                    self.refresh_input()

                return True

            except asyncio.TimeoutError:
                self.add_output("*** Palvelin ei vastaa - BatMUD saattaa olla alhaalla ***\n")
                if self.writer:
                    self.writer.close()
                return False

        except asyncio.TimeoutError:
            self.add_output("*** Yhteysaikakatkaisu - palvelimeen ei saatu yhteyttä ***\n")
            return False
        except ConnectionRefusedError:
            self.add_output("*** Yhteys evätty - palvelin ei hyväksy yhteyksiä ***\n")
            return False
        except OSError as e:
            self.add_output(f"*** Verkkovirhe: {e} ***\n")
            return False
        except Exception as e:
            self.add_output(f"*** Yhteysvirhe: {e} ***\n")
            return False

    def start_auto_log(self):
        """Käynnistä automaattinen loggaus jos asetettu .env:ssä."""
        if not self.auto_log:
            return

        from datetime import datetime
        from pathlib import Path

        # Määritä logs-kansio
        if self.log_dir:
            logs_dir = Path(self.log_dir)
        else:
            logs_dir = Path(__file__).resolve().parent / "logs"

        logs_dir.mkdir(exist_ok=True)

        # Luo tiedostonimi
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        log_path = logs_dir / f"{timestamp}.log"

        try:
            self.log_file = open(log_path, 'a', encoding='utf-8')
            self.log_filename = str(log_path)

            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"\n{'='*60}\n")
            self.log_file.write(f"Automaattinen loggaus aloitettu: {start_time}\n")
            self.log_file.write(f"{'='*60}\n\n")
            self.log_file.flush()

            self.add_output(f"*** Auto-log: {log_path} ***\n")
        except Exception as e:
            self.add_output(f"*** Auto-log virhe: {e} ***\n")

    async def auto_login(self):
        """Automaattinen kirjautuminen .env tiedoista"""
        if self.username and self.password:
            self.add_output("*** Automaattinen kirjautuminen... ***\n")
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
                        self.exit_message = "Yhteys palvelimeen katkennut."
                        self.running = False
                        break

                    # Debug: näytä raakadata luettavassa muodossa
                    if self.debug_mode:
                        debug_str = format_debug_bytes(data)
                        self.add_output(f"[DEBUG] {debug_str}\n")

                    # Käsittele telnet-komennot (IAC)
                    text, prompt_detected = self.handle_telnet("", data)

                    # Debug: näytä prompt-tila
                    if self.debug_mode and prompt_detected:
                        self.add_output(f"[DEBUG] >>> PROMPT DETECTED <<<\n")

                    # Yhdistä edellinen keskeneräinen rivi
                    text = self.partial_line + text
                    self.partial_line = ""

                    if prompt_detected:
                        # Etsi viimeinen rivinvaihto - sen jälkeinen teksti on prompt
                        last_newline = text.rfind('\n')
                        if last_newline >= 0:
                            # Tulosta kaikki ennen promptia
                            self.add_output(text[:last_newline + 1])
                            # Tallenna prompt
                            self.mud_prompt = text[last_newline + 1:]
                        else:
                            # Ei rivinvaihtoja - koko teksti on prompt
                            self.mud_prompt = text
                        self.refresh_input()
                    else:
                        # Tarkista onko keskeneräinen rivi (ei pääty \n)
                        if text and not text.endswith('\n'):
                            last_newline = text.rfind('\n')
                            if last_newline >= 0:
                                self.add_output(text[:last_newline + 1])
                                self.partial_line = text[last_newline + 1:]
                            else:
                                self.partial_line = text
                        else:
                            self.add_output(text)

                    self.refresh_status()
                    curses.doupdate()

                except asyncio.TimeoutError:
                    pass
                except (ConnectionResetError, BrokenPipeError, OSError) as e:
                    self.add_output(f"\n*** Yhteys katkesi: {e} ***\n")
                    self.exit_message = f"Yhteys katkesi: {e}"
                    self.running = False
                    break
                except Exception as e:
                    self.add_output(f"\n*** Yhteysvirhe: {e} ***\n")
                    self.exit_message = f"Yhteysvirhe: {e}"
                    self.running = False
                    break
        except asyncio.CancelledError:
            pass

    def handle_telnet(self, text, raw_data):
        """Käsittele telnet-protokollan komennot ja tunnista promptit"""
        result = []
        prompt_detected = False
        i = 0
        data = list(raw_data)

        while i < len(data):
            if data[i] == IAC and i + 1 < len(data):
                next_byte = data[i + 1]

                if next_byte == IAC:  # Escaped IAC
                    result.append(IAC)
                    i += 2

                elif next_byte == GA:  # Go Ahead - prompt marker
                    prompt_detected = True
                    i += 2

                elif next_byte == EOR:  # End of Record - prompt marker
                    prompt_detected = True
                    i += 2

                elif next_byte in (WILL, WONT, DO, DONT) and i + 2 < len(data):
                    cmd = next_byte
                    opt = data[i + 2]

                    if cmd == DO:
                        if opt == TELOPT_EOR:
                            # Hyväksy EOR - vastaa WILL
                            response = bytes([IAC, WILL, TELOPT_EOR])
                        else:
                            # Muut - vastaa WONT
                            response = bytes([IAC, WONT, opt])
                        if self.writer:
                            self.writer.write(response)

                    elif cmd == WILL:
                        if opt == TELOPT_EOR:
                            # Hyväksy EOR - vastaa DO
                            response = bytes([IAC, DO, TELOPT_EOR])
                        elif opt == TELOPT_ECHO:
                            # Palvelin hoitaa echon (salasana) - vastaa DO
                            response = bytes([IAC, DO, TELOPT_ECHO])
                            self.echo_off = True
                        else:
                            # Muut - vastaa DONT
                            response = bytes([IAC, DONT, opt])
                        if self.writer:
                            self.writer.write(response)

                    elif cmd == WONT:
                        if opt == TELOPT_ECHO:
                            # Palvelin ei enää hoida echoa - vastaa DONT
                            response = bytes([IAC, DONT, TELOPT_ECHO])
                            self.echo_off = False
                            if self.writer:
                                self.writer.write(response)

                    i += 3

                elif next_byte == SB:  # Subnegotiation - ohita
                    # Etsi SE
                    j = i + 2
                    while j < len(data) - 1:
                        if data[j] == IAC and data[j + 1] == SE:
                            break
                        j += 1
                    i = j + 2

                else:
                    i += 2
            else:
                result.append(data[i])
                i += 1

        return bytes(result).decode('iso-8859-1', errors='replace'), prompt_detected

    async def handle_client_command(self, cmd):
        """Käsittele client-komento. Palauttaa False jos pitää lopettaa."""
        parts = cmd.split(maxsplit=1)
        cmd_name = parts[0][1:].lower()  # Poista / alusta
        args = parts[1] if len(parts) > 1 else ""

        # Sisäänrakennetut komennot (quit, debug)
        if cmd_name == 'quit':
            self.add_output("*** Suljetaan client... ***\n")
            self.running = False
            return False

        elif cmd_name == 'debug':
            args_lower = args.lower()
            if args_lower == 'on':
                self.debug_mode = True
                self.add_output("*** Debug-tila ON ***\n")
                self.refresh_status()
            elif args_lower == 'off':
                self.debug_mode = False
                self.add_output("*** Debug-tila OFF ***\n")
                self.refresh_status()
            else:
                self.add_output("*** Käyttö: /debug on | /debug off ***\n")

        else:
            # Etsi komento moduuleista ja luo instanssi
            command = cmds.create_command(cmd_name, self)
            if command:
                result = await command.execute(args)
                if result is False:
                    return False
            else:
                self.add_output(f"*** Tuntematon komento: /{cmd_name} - kirjoita /help ***\n")

        self.refresh_output()
        return True

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

    def expand_alias(self, cmd):
        """Laajenna alias jos löytyy."""
        if not cmd or not self.user_aliases:
            return cmd

        # Tarkista onko ensimmäinen sana alias
        parts = cmd.split(maxsplit=1)
        first_word = parts[0]

        if first_word in self.user_aliases:
            alias_cmd = self.user_aliases[first_word]
            # Jos oli argumentteja, lisää ne aliaksen perään
            if len(parts) > 1:
                return f"{alias_cmd} {parts[1]}"
            return alias_cmd

        return cmd

    async def handle_input(self):
        """Käsittele käyttäjän syöte"""
        try:
            while self.running:
                try:
                    # Käytä get_wch() unicode-tukeen
                    try:
                        key = self.input_win.get_wch()
                    except curses.error:
                        # halfdelay timeout - anna muille tehtäville aikaa
                        await asyncio.sleep(0)
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
                        cmd = self.input_buffer.strip()

                        if cmd.startswith('//'):
                            # // -> lähetä palvelimelle yhdellä /
                            await self.send_command(cmd[1:])
                        elif cmd.startswith('/'):
                            # Client-komento
                            if not await self.handle_client_command(cmd):
                                break  # /quit
                        else:
                            # Tarkista alias ja lähetä palvelimelle
                            expanded = self.expand_alias(cmd)
                            await self.send_command(expanded)

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
            self.add_output("*** Paina ESC poistuaksesi. ***\n")
            while self.running:
                key = self.input_win.getch()
                if key == 27:
                    break
                await asyncio.sleep(0.1)
            return

        # Aloita automaattinen loggaus jos määritelty
        self.start_auto_log()

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


exit_message = None


def main(stdscr):
    """Main wrapper curses:lle"""
    global exit_message
    client = BatClient(stdscr)
    asyncio.run(client.run())
    exit_message = client.exit_message


if __name__ == "__main__":
    try:
        curses.wrapper(main)
        if exit_message:
            print(f"\n{exit_message}")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Virhe: {e}")
        sys.exit(1)

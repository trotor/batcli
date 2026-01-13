# BatCLI

A simple terminal-based MUD client for [BatMUD](https://www.bat.org) (bat.org:23).

## Features

- Telnet connection to BatMUD
- ANSI color support
- ISO-8859-1 character encoding (Nordic characters)
- Unicode input support
- Command history (Ctrl-P / Ctrl-N)
- Line editing with cursor movement
- Scroll back through output history
- Auto-login from .env file

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Installation

```bash
git clone https://github.com/yourusername/batcli.git
cd batcli
```

### Optional: Auto-login setup

```bash
cp .env_sample .env
# Edit .env with your credentials
```

## Usage

```bash
python3 batclient.py
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| Enter | Send command |
| Left/Right | Move cursor |
| Up | Move to beginning of line |
| Down | Move to end of line |
| Ctrl-P | Previous command from history |
| Ctrl-N | Next command from history |
| Ctrl-A | Move to beginning of line |
| Ctrl-E | Move to end of line |
| Ctrl-U | Clear line |
| Ctrl-K | Delete from cursor to end |
| Page Up/Down | Scroll output history |
| Home/End | Scroll to top/bottom |

### Commands

| Command | Action |
|---------|--------|
| `/quit` | Exit the client |

## License

MIT

## Links

- [BatMUD](https://www.bat.org) - The game
- [BatMUD Wiki](https://batmud.fandom.com) - Game wiki

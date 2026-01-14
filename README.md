# BatCLI

A simple terminal-based MUD client for [BatMUD](https://www.bat.org) (bat.org:23).

> :finland: [Lue ohjeet suomeksi](README_FI.md)

## Features

- Telnet connection to BatMUD
- ANSI color support
- ISO-8859-1 character encoding (Nordic characters)
- Unicode input support
- Command history (Ctrl-P / Ctrl-N)
- Line editing with cursor movement
- Scroll back through output history
- Auto-login from .env file
- **Prompt hold**: MUD prompt (IAC GA/EOR) displayed on input line
- **Debug mode**: View raw telnet data with `/debug on`

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Installation

```bash
git clone https://github.com/yourusername/batcli.git
cd batcli
```

### Global command setup (optional)

Make `batcli` available as a command from anywhere:

```bash
# Make the script executable
chmod +x batclient.py

# Create ~/bin directory and add to PATH (if not already done)
mkdir -p ~/bin
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc  # or ~/.bashrc for bash

# Create symlink
ln -sf "$(pwd)/batclient.py" ~/bin/batcli

# Reload shell config
source ~/.zshrc  # or ~/.bashrc
```

Now you can run `batcli` from any directory.

### Optional: Auto-login setup

```bash
cp .env_sample .env
# Edit .env with your credentials
```

## Usage

```bash
# If installed globally:
batcli

# Or run directly from the project directory:
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
| `/debug on` | Enable debug mode (shows raw data from server) |
| `/debug off` | Disable debug mode |

## Security Note

Telnet is an unencrypted protocol. Your credentials are transmitted in plain text. This is a limitation of the MUD protocol, not this client. Use unique passwords for MUD games.

## License

MIT

## Links

- [BatMUD](https://www.bat.org) - The game
- [BatMUD Wiki](https://batmud.fandom.com) - Game wiki

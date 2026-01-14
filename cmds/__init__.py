"""
Komentomoduulien lataus.

Jokainen .py tiedosto tässä kansiossa (paitsi _ alkuiset) ladataan automaattisesti.
Moduulin tulee sisältää:
  - NAME: str - komennon nimi (ilman /)
  - DESCRIPTION: str - lyhyt kuvaus
  - execute(client, args: str) -> bool - async funktio, palauttaa False jos client pitää sulkea
"""

import importlib
import pkgutil
from pathlib import Path

# Ladatut komennot: {nimi: moduuli}
commands = {}


def load_commands():
    """Lataa kaikki komennot cmds/ kansiosta"""
    global commands
    commands = {}

    package_dir = Path(__file__).parent

    for finder, name, ispkg in pkgutil.iter_modules([str(package_dir)]):
        if name.startswith('_'):
            continue

        try:
            module = importlib.import_module(f'.{name}', package='cmds')

            # Tarkista että moduulissa on tarvittavat attribuutit
            if hasattr(module, 'NAME') and hasattr(module, 'execute'):
                cmd_name = module.NAME.lower()
                commands[cmd_name] = module
        except Exception as e:
            print(f"Virhe ladattaessa komentoa {name}: {e}")


def get_command(name):
    """Hae komento nimellä"""
    return commands.get(name.lower())


def get_all_commands():
    """Palauta kaikki komennot"""
    return commands


# Lataa komennot kun moduuli importataan
load_commands()

"""
Komentomoduulien lataus.

Jokainen .py tiedosto tässä kansiossa (paitsi _ alkuiset ja base.py)
ladataan automaattisesti.

Komennot voivat olla:
1. Luokkapohjaisia (perivät Command-luokan) - SUOSITELTU
2. Funktiopohjaisia (NAME, DESCRIPTION, execute) - legacy

Esimerkki luokkapohjaisesta komennosta:
    from cmds.base import Command

    class MyCommand(Command):
        name = "mycommand"
        aliases = ["mc", "my"]
        description = "Kuvaus"
        usage = "/mycommand <arg>"

        async def execute(self, args):
            self.output(f"Args: {args}")
            return True
"""

import importlib
import inspect
import pkgutil
from pathlib import Path

from cmds.base import Command

# Ladatut komento-luokat: {nimi: Command-luokka}
_command_classes = {}

# Aliakset: {alias: nimi}
_aliases = {}


def load_commands():
    """Lataa kaikki komennot cmds/ kansiosta."""
    global _command_classes, _aliases
    _command_classes = {}
    _aliases = {}

    package_dir = Path(__file__).parent

    for finder, name, ispkg in pkgutil.iter_modules([str(package_dir)]):
        # Ohita _ alkuiset ja base.py
        if name.startswith('_') or name == 'base':
            continue

        try:
            module = importlib.import_module(f'.{name}', package='cmds')

            # Etsi Command-luokan perivät luokat
            for item_name, item in inspect.getmembers(module, inspect.isclass):
                if (issubclass(item, Command) and
                    item is not Command and
                    hasattr(item, 'name') and
                    item.name):

                    cmd_name = item.name.lower()
                    _command_classes[cmd_name] = item

                    # Rekisteröi aliakset
                    for alias in getattr(item, 'aliases', []):
                        _aliases[alias.lower()] = cmd_name

        except Exception as e:
            print(f"Virhe ladattaessa komentoa {name}: {e}")


def get_command(name):
    """
    Hae komento-luokka nimellä tai aliaksella.

    Args:
        name: Komennon nimi tai alias

    Returns:
        Command-luokka tai None
    """
    name = name.lower()

    # Tarkista ensin suora nimi
    if name in _command_classes:
        return _command_classes[name]

    # Tarkista aliakset
    if name in _aliases:
        return _command_classes.get(_aliases[name])

    return None


def get_all_commands():
    """
    Palauta kaikki komento-luokat.

    Returns:
        dict: {nimi: Command-luokka}
    """
    return _command_classes.copy()


def get_aliases():
    """
    Palauta kaikki aliakset.

    Returns:
        dict: {alias: komennon_nimi}
    """
    return _aliases.copy()


def create_command(name, client):
    """
    Luo komento-instanssi.

    Args:
        name: Komennon nimi tai alias
        client: BatClient instanssi

    Returns:
        Command instanssi tai None
    """
    cmd_class = get_command(name)
    if cmd_class:
        return cmd_class(client)
    return None


# Lataa komennot kun moduuli importataan
load_commands()

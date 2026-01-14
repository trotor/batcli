"""
/help - Näytä ohje client-komennoista
"""

NAME = "help"
DESCRIPTION = "Näytä ohje"


async def execute(client, args):
    """Näytä ohje"""
    from cmds import get_all_commands

    help_lines = [
        "",
        f"*** Dino's mini Batmud Client v{client.version} - Ohjeet ***",
        "",
        "CLIENT-KOMENNOT (alkavat /):",
    ]

    # Listaa kaikki ladatut komennot
    commands = get_all_commands()
    for name, module in sorted(commands.items()):
        desc = getattr(module, 'DESCRIPTION', '')
        help_lines.append(f"  /{name:12} - {desc}")

    # Sisäänrakennetut komennot
    help_lines.extend([
        "  /debug on    - Ota debug-tila käyttöön",
        "  /debug off   - Poista debug-tila käytöstä",
        "  /quit        - Sulje client",
        "",
        "HUOM: // lähettää yhden / palvelimelle (esim. //who -> /who)",
        "",
        "PIKANÄPPÄIMET:",
        "  Ctrl-P/N      - Komentohistoria eteen/taakse",
        "  Ctrl-A/E      - Rivin alku/loppu",
        "  Ctrl-U        - Tyhjennä rivi",
        "  Ctrl-K        - Poista kursorista loppuun",
        "  Page Up/Down  - Vieritä historiaa",
        "  Home/End      - Vieritä alkuun/loppuun",
        "",
    ])

    client.add_output("\n".join(help_lines) + "\n")
    return True

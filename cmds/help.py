"""
/help - Näytä ohje client-komennoista
"""

from cmds.base import Command


class HelpCommand(Command):
    name = "help"
    aliases = ["h", "?"]
    description = "Näytä ohje"
    usage = "/help [komento]"

    async def execute(self, args):
        """Näytä ohje."""
        if args:
            # Näytä tietyn komennon ohje
            self.show_command_help(args.strip())
        else:
            # Näytä yleinen ohje
            self.show_general_help()
        return True

    def show_command_help(self, cmd_name):
        """Näytä tietyn komennon ohje."""
        from cmds import get_command, get_aliases

        cmd_class = get_command(cmd_name)
        if not cmd_class:
            self.error(f"Tuntematon komento: /{cmd_name}")
            return

        # Luo väliaikainen instanssi saadaksemme tiedot
        lines = [
            "",
            f"*** /{cmd_class.name} ***",
            "",
        ]

        if cmd_class.description:
            lines.append(f"  {cmd_class.description}")
            lines.append("")

        if cmd_class.usage:
            lines.append(f"  Käyttö: {cmd_class.usage}")

        if cmd_class.aliases:
            aliases_str = ", ".join(f"/{a}" for a in cmd_class.aliases)
            lines.append(f"  Aliakset: {aliases_str}")

        lines.append("")
        self.output("\n".join(lines))

    def show_general_help(self):
        """Näytä yleinen ohje."""
        from cmds import get_aliases

        lines = [
            "",
            f"*** Dino's mini Batmud Client v{self.version} ***",
            "",
            "KOMENNOT:",
        ]

        # Listaa kaikki ladatut komennot
        commands = self.get_all_commands()
        for name in sorted(commands.keys()):
            cmd_class = commands[name]
            desc = cmd_class.description or ""
            aliases = cmd_class.aliases or []

            if aliases:
                alias_str = f" ({', '.join(aliases)})"
            else:
                alias_str = ""

            lines.append(f"  /{name:12}{alias_str:15} - {desc}")

        # Sisäänrakennetut komennot
        lines.extend([
            "",
            "SISÄÄNRAKENNETUT:",
            "  /debug on/off              - Debug-tila",
            "  /quit                      - Sulje client",
            "",
            "HUOM: // lähettää / palvelimelle (esim. //who -> /who)",
            "",
            "PIKANÄPPÄIMET:",
            "  Ctrl-P/N      - Komentohistoria",
            "  Ctrl-A/E      - Rivin alku/loppu",
            "  Ctrl-U/K      - Tyhjennä rivi / poista loppuun",
            "  Page Up/Down  - Vieritä historiaa",
            "",
            "Kirjoita /help <komento> saadaksesi lisätietoja.",
            "",
        ])

        self.output("\n".join(lines))

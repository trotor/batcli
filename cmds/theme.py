"""
/theme - Vaihda väriteema
"""

from cmds.base import Command


class ThemeCommand(Command):
    name = "theme"
    aliases = ["teema"]
    description = "Vaihda väriteema"
    usage = "/theme [nimi]"

    async def execute(self, args):
        """Näytä tai vaihda väriteema."""
        name = args.strip().lower()
        themes = self.client.list_themes()

        if not name:
            self.show_themes(themes)
            return True

        if name not in themes:
            self.error(f"Tuntematon teema: {name}")
            self.output("  Saatavilla: " + ", ".join(themes) + "\n")
            return True

        self.client.apply_theme(name)
        return True

    def show_themes(self, themes):
        """Listaa teemat ja näytä nykyinen."""
        self.info(f"Väriteema: {self.client.theme_name}")
        self.output("  Saatavilla:\n")
        for name in themes:
            marker = "  <- käytössä" if name == self.client.theme_name else ""
            self.output(f"    {name}{marker}\n")
        self.output("  Vaihda: /theme <nimi>\n")

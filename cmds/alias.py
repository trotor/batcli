"""
/alias - Luo ja hallitse pikakomentoja
"""

from cmds.base import Command


class AliasCommand(Command):
    name = "alias"
    aliases = ["al"]
    description = "Luo ja hallitse pikakomentoja"
    usage = "/alias [nimi] [komento] | /alias -d <nimi> | /alias -l"

    async def execute(self, args):
        """Hallitse aliaksia."""
        if not args:
            self.show_aliases()
            return True

        parts = args.split(maxsplit=1)
        first = parts[0]

        # Poista alias
        if first == "-d" or first == "--delete":
            if len(parts) < 2:
                self.error("Anna poistettavan aliaksen nimi")
                return True
            self.delete_alias(parts[1])
            return True

        # Listaa aliakset
        if first == "-l" or first == "--list":
            self.show_aliases()
            return True

        # Näytä tai luo alias
        alias_name = first

        if len(parts) < 2:
            # Näytä yksittäinen alias
            self.show_alias(alias_name)
        else:
            # Luo uusi alias
            alias_command = parts[1]
            self.create_alias(alias_name, alias_command)

        return True

    def create_alias(self, name, command):
        """Luo uusi alias."""
        # Tarkista ettei alias ole client-komento
        if name.startswith('/'):
            name = name[1:]

        # Tarkista ettei ylikirjoita client-komentoja
        from cmds import get_command
        if get_command(name) or name in ('quit', 'debug'):
            self.error(f"'{name}' on varattu client-komento")
            return

        self.client.user_aliases[name] = command
        self.info(f"Alias luotu: {name} -> {command}")

    def delete_alias(self, name):
        """Poista alias."""
        if name.startswith('/'):
            name = name[1:]

        if name in self.client.user_aliases:
            del self.client.user_aliases[name]
            self.info(f"Alias poistettu: {name}")
        else:
            self.error(f"Alias '{name}' ei ole olemassa")

    def show_alias(self, name):
        """Näytä yksittäinen alias."""
        if name.startswith('/'):
            name = name[1:]

        if name in self.client.user_aliases:
            cmd = self.client.user_aliases[name]
            self.output(f"  {name} -> {cmd}\n")
        else:
            self.error(f"Alias '{name}' ei ole olemassa")

    def show_aliases(self):
        """Näytä kaikki aliakset."""
        aliases = self.client.user_aliases

        if not aliases:
            self.info("Ei aliaksia")
            self.output("  Luo: /alias <nimi> <komento>\n")
            self.output("  Esim: /alias kk kill kobold\n")
            return

        self.info(f"Aliakset ({len(aliases)} kpl)")
        for name, cmd in sorted(aliases.items()):
            self.output(f"  {name} -> {cmd}\n")

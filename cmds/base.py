"""
Komentojen base-luokka ja apufunktiot.
"""


class Command:
    """
    Komennon base-luokka. Kaikki komennot perivät tämän.

    Attribuutit:
        name: str - Komennon nimi (ilman /)
        aliases: list - Vaihtoehtoisia nimiä komennolle
        description: str - Lyhyt kuvaus /help listaukseen
        usage: str - Käyttöohje (esim. "/cmd <arg>")

    Metodit:
        execute(args) - Suorita komento (async)
        output(text) - Tulosta tekstiä näytölle
        send(cmd) - Lähetä komento MUD-palvelimelle (async)
    """

    name = ""
    aliases = []
    description = ""
    usage = ""

    def __init__(self, client):
        """
        Alusta komento.

        Args:
            client: BatClient instanssi
        """
        self.client = client

    async def execute(self, args):
        """
        Suorita komento.

        Args:
            args: str - Argumentit merkkijonona

        Returns:
            bool - True jatkaakseen, False sulkeakseen clientin
        """
        raise NotImplementedError(f"Komento {self.name} ei ole toteutettu")

    # === Apumetodit ===

    def output(self, text):
        """Tulosta tekstiä output-ikkunaan."""
        self.client.add_output(text)

    def error(self, text):
        """Tulosta virheilmoitus."""
        self.client.add_output(f"*** Virhe: {text} ***\n")

    def info(self, text):
        """Tulosta info-viesti."""
        self.client.add_output(f"*** {text} ***\n")

    async def send(self, cmd):
        """Lähetä komento MUD-palvelimelle."""
        await self.client.send_command(cmd)

    def show_usage(self):
        """Näytä käyttöohje."""
        if self.usage:
            self.output(f"Käyttö: {self.usage}\n")
        else:
            self.output(f"Käyttö: /{self.name}\n")

    @property
    def debug_mode(self):
        """Onko debug-tila päällä."""
        return self.client.debug_mode

    @property
    def version(self):
        """Sovelluksen versio."""
        return self.client.version

    def get_command(self, name):
        """Hae toinen komento nimellä."""
        from cmds import get_command
        return get_command(name)

    def get_all_commands(self):
        """Hae kaikki komennot."""
        from cmds import get_all_commands
        return get_all_commands()

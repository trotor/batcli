"""
/connect - Yhdistä palvelimelle
"""

from cmds.base import Command


class ConnectCommand(Command):
    name = "connect"
    aliases = ["conn"]
    description = "Yhdistä palvelimelle"
    usage = "/connect [host] [port]"

    async def execute(self, args):
        """
        Yhdistä palvelimelle.

        Args:
            args: Komennon argumentit (host port tai tyhjä)

        Returns:
            True jatkaakseen
        """
        # Tarkista onko jo yhteys
        if self.client.reader is not None and self.client.writer is not None:
            self.error("Olet jo yhteydessä palvelimelle.\n")
            self.info("Käytä ensin /disconnect katkaistaaksesi yhteyden.\n")
            return True

        host = None
        port = None

        # Parsitaan argumentit
        if args:
            parts = args.strip().split()
            if len(parts) >= 2:
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    self.error(f"Virheellinen porttinumero: {parts[1]}\n")
                    self.show_usage()
                    return True
            elif len(parts) == 1:
                self.error("Anna sekä palvelin että portti.\n")
                self.show_usage()
                return True

        # Jos ei parametreja, yritä käyttää .env:n arvoja
        if host is None or port is None:
            # Tarkista .env
            env_host = self.client.env.get('BATMUD_HOST', '').strip()
            env_port_str = self.client.env.get('BATMUD_PORT', '').strip()

            if env_host and env_port_str:
                host = env_host
                try:
                    port = int(env_port_str)
                except ValueError:
                    self.error(f"Virheellinen BATMUD_PORT .env tiedostossa: {env_port_str}\n")
                    return True
            else:
                # Ei .env:ssä, käytetään oletusarvoja
                self.info("Ei yhteystietoja annettu eikä .env-tiedostossa.\n")
                self.info("Käytetään oletuspalvelinta bat.org:23\n\n")
                self.info("Voit määrittää palvelimen kahdella tavalla:\n")
                self.info("1. Komennolla: /connect <host> <port>\n")
                self.info("2. .env tiedostossa: BATMUD_HOST=<host> ja BATMUD_PORT=<port>\n")
                host = "bat.org"
                port = 23

        # Yhdistä
        import asyncio
        self.output(f"Yhdistetään palvelimeen {host}:{port}...\n")
        try:
            self.client.reader, self.client.writer = await asyncio.open_connection(host, port)
            self.info("Yhteys muodostettu!\n")

            # Päivitä statusbaari
            self.client.refresh_status()

            # Käynnistä automaattinen loggaus jos asetettu
            self.client.start_auto_log()

            # Käynnistä read task jos ei ole käynnissä
            if not hasattr(self.client, 'read_task') or self.client.read_task.done():
                self.client.read_task = asyncio.create_task(self.client.read_from_server())

            # Käynnistä auto-login jos määritelty
            if self.client.username and self.client.password:
                asyncio.create_task(self.client.auto_login())

            return True
        except Exception as e:
            self.error(f"Yhteysvirhe: {e}\n")
            return True

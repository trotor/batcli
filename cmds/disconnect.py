"""
/disconnect - Katkaise yhteys palvelimelle
"""

from cmds.base import Command


class DisconnectCommand(Command):
    name = "disconnect"
    aliases = ["dc"]
    description = "Katkaise yhteys palvelimelle"
    usage = "/disconnect"

    async def execute(self, args):
        """
        Katkaise yhteys palvelimelle.

        Args:
            args: Komennon argumentit (ei käytössä)

        Returns:
            True jatkaakseen
        """
        if self.client.reader is None and self.client.writer is None:
            self.info("Et ole yhteydessä palvelimelle.\n")
            return True

        try:
            # Sulje yhteys
            if self.client.writer:
                self.client.writer.close()
                await self.client.writer.wait_closed()

            self.client.reader = None
            self.client.writer = None

            # Päivitä statusbaari
            self.client.refresh_status()

            self.info("Yhteys palvelimelle katkaistu.\n")
            self.info("Voit muodostaa uuden yhteyden komennolla /connect\n")
        except Exception as e:
            self.error(f"Virhe yhteyden katkaisussa: {e}\n")

        return True

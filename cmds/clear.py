"""
/clear - Tyhjennä näyttö
"""

from cmds.base import Command


class ClearCommand(Command):
    name = "clear"
    aliases = ["cls", "c"]
    description = "Tyhjennä näyttö"
    usage = "/clear"

    async def execute(self, args):
        """Tyhjennä output-ikkuna."""
        self.client.output_lines.clear()
        self.client.scroll_offset = 0
        self.client.refresh_output()
        self.info("Näyttö tyhjennetty")
        return True

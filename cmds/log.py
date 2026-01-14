"""
/log - Sessioiden tallennus tiedostoon
"""

import os
from datetime import datetime
from pathlib import Path

from cmds.base import Command


class LogCommand(Command):
    name = "log"
    aliases = ["l"]
    description = "Aloita/lopeta loggaus tiedostoon"
    usage = "/log [on|off|status] [tiedosto]"

    async def execute(self, args):
        """Hallitse loggausta."""
        parts = args.split() if args else []
        action = parts[0].lower() if parts else "status"
        filename = parts[1] if len(parts) > 1 else None

        if action == "on":
            self.start_logging(filename)
        elif action == "off":
            self.stop_logging()
        elif action == "status":
            self.show_status()
        else:
            # Jos annettu vain tiedostonimi, aloita loggaus siihen
            if action and action not in ("on", "off", "status"):
                self.start_logging(action)
            else:
                self.show_usage()

        return True

    def start_logging(self, filename=None):
        """Aloita loggaus."""
        if self.client.log_file:
            self.error("Loggaus on jo käynnissä")
            self.output(f"  Tiedosto: {self.client.log_filename}\n")
            return

        # Luo logs-kansio
        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Määritä tiedostonimi
        if filename:
            if not filename.endswith('.log'):
                filename += '.log'
            log_path = logs_dir / filename
        else:
            # Oletusformaatti: vuosikkpvhhmin.log
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            log_path = logs_dir / f"{timestamp}.log"

        try:
            self.client.log_file = open(log_path, 'a', encoding='utf-8')
            self.client.log_filename = str(log_path)

            # Kirjoita aloitusmerkintä
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.client.log_file.write(f"\n{'='*60}\n")
            self.client.log_file.write(f"Loggaus aloitettu: {start_time}\n")
            self.client.log_file.write(f"{'='*60}\n\n")
            self.client.log_file.flush()

            self.info(f"Loggaus aloitettu: {log_path.name}")

        except Exception as e:
            self.error(f"Loggauksen aloitus epäonnistui: {e}")

    def stop_logging(self):
        """Lopeta loggaus."""
        if not self.client.log_file:
            self.error("Loggaus ei ole käynnissä")
            return

        try:
            # Kirjoita lopetusmerkintä
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.client.log_file.write(f"\n{'='*60}\n")
            self.client.log_file.write(f"Loggaus lopetettu: {end_time}\n")
            self.client.log_file.write(f"{'='*60}\n")
            self.client.log_file.close()

            filename = self.client.log_filename
            self.client.log_file = None
            self.client.log_filename = None

            self.info(f"Loggaus lopetettu: {Path(filename).name}")

        except Exception as e:
            self.error(f"Loggauksen lopetus epäonnistui: {e}")

    def show_status(self):
        """Näytä loggauksen tila."""
        if self.client.log_file:
            self.info("Loggaus ON")
            self.output(f"  Tiedosto: {self.client.log_filename}\n")
        else:
            self.info("Loggaus OFF")
            self.output("  Käynnistä: /log on [tiedosto]\n")

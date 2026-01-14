# Claude-ohjeet tälle projektille

## Versionumerointi

Versionumero sijaitsee tiedostossa `batclient.py` rivillä `VERSION = "x.x.x"`.

Kun sovellusta päivitetään ja muutokset commitoidaan GitHubiin:
- **Patch** (0.0.x): Pienet bugikorjaukset, typojen korjaukset
- **Minor** (0.x.0): Uudet ominaisuudet, parannukset
- **Major** (x.0.0): Isot muutokset, yhteensopivuutta rikkovat muutokset

Päivitä VERSION-muuttuja ennen commitia.

## Projektin rakenne

- `batclient.py` - Pääsovellus (telnet-client BatMUD:iin)
- `cmds/` - Client-komennot (modulaarinen)
  - `__init__.py` - Komentojen latausmekanismi
  - `base.py` - Command base-luokka
  - `help.py` - /help komento
- `.env` - Käyttäjän tunnukset (ei versionhallinnassa)
- `.env_sample` - Esimerkki .env-tiedostosta

## Uuden komennon lisääminen

Luo uusi tiedosto `cmds/` kansioon, esim. `cmds/esimerkki.py`:

```python
"""
/esimerkki - Komennon kuvaus
"""

from cmds.base import Command


class EsimerkkiCommand(Command):
    name = "esimerkki"
    aliases = ["ex", "e"]  # Vaihtoehtoisia nimiä
    description = "Lyhyt kuvaus /help listaukseen"
    usage = "/esimerkki <teksti>"

    async def execute(self, args):
        """
        Suorita komento.

        Args:
            args: Komennon argumentit merkkijonona

        Returns:
            True jatkaakseen, False sulkeakseen clientin
        """
        if not args:
            self.show_usage()
            return True

        self.output(f"Sait argumentin: {args}\n")
        return True
```

Komento latautuu automaattisesti käynnistyksen yhteydessä.

### Command-luokan attribuutit

- `name` - Komennon nimi (pakollinen)
- `aliases` - Lista vaihtoehtoisista nimistä
- `description` - Lyhyt kuvaus /help listaukseen
- `usage` - Käyttöohje

### Command-luokan metodit

**Tulostus:**
- `self.output(text)` - Tulosta tekstiä näytölle
- `self.error(text)` - Tulosta virheilmoitus
- `self.info(text)` - Tulosta info-viesti
- `self.show_usage()` - Näytä käyttöohje

**Palvelinyhteys:**
- `await self.send(cmd)` - Lähetä komento MUD-palvelimelle

**Tila:**
- `self.debug_mode` - Debug-tila päällä/pois (property)
- `self.version` - Sovelluksen versio (property)
- `self.client` - BatClient instanssi

**Muut komennot:**
- `self.get_command(name)` - Hae toinen komento
- `self.get_all_commands()` - Hae kaikki komennot

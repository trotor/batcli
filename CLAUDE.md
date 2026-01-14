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
  - `help.py` - /help komento
- `.env` - Käyttäjän tunnukset (ei versionhallinnassa)
- `.env_sample` - Esimerkki .env-tiedostosta

## Uuden komennon lisääminen

Luo uusi tiedosto `cmds/` kansioon, esim. `cmds/esimerkki.py`:

```python
"""
/esimerkki - Komennon kuvaus
"""

NAME = "esimerkki"
DESCRIPTION = "Lyhyt kuvaus /help listaukseen"

async def execute(client, args):
    """
    Suorita komento.

    Args:
        client: BatClient instanssi
        args: Komennon argumentit merkkijonona

    Returns:
        True jatkaakseen, False sulkeakseen clientin
    """
    client.add_output("Hei maailma!\n")
    return True
```

Komento latautuu automaattisesti käynnistyksen yhteydessä.

### Client-objektin hyödyllisiä metodeja

- `client.add_output(text)` - Tulosta tekstiä näytölle
- `client.refresh_output()` - Päivitä näyttö
- `client.refresh_status()` - Päivitä status bar
- `await client.send_command(cmd)` - Lähetä komento palvelimelle
- `client.debug_mode` - Debug-tila päällä/pois
- `client.version` - Sovelluksen versio

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
- `.env` - Käyttäjän tunnukset (ei versionhallinnassa)
- `.env_sample` - Esimerkki .env-tiedostosta

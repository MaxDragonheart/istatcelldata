# ISTAT Census Data

[![CI](https://github.com/MaxDragonheart/istat-census-data/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxDragonheart/istat-census-data/actions/workflows/ci.yml)
[![Documentation](https://github.com/MaxDragonheart/istat-census-data/actions/workflows/docs.yml/badge.svg)](https://maxdragonheart.github.io/istat-census-data/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/istat-census-data.svg)](https://badge.fury.io/py/istat-census-data)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Con **ISTAT Census Data** puoi ottenere facilmente il set di dati riferiti ai censimenti ISTAT in cui sono stati
rilasciati anche i dati delle celle censuarie.

E' possibile scaricare e processare i dati dal 1991 al 2021.

## Installazione

```bash
pip install istat-census-data
```

## Rinomina del progetto e manutenzione

`istat-census-data` è la distribuzione PyPI mantenuta.

Il nome della distribuzione PyPI è `istat-census-data`. A partire dalla versione
1.5.0, il package Python consigliato da importare è `istat_census_data`:

```python
import istat_census_data
```

La vecchia pagina PyPI
[`istatcelldata`](https://pypi.org/project/istatcelldata/) non è più mantenuta e non
riceverà nuove release, perché il progetto si è spostato su
[`istat-census-data`](https://pypi.org/project/istat-census-data/).

Aggiorna le dipendenze di installazione a `istat-census-data`.

Il vecchio import `istatcelldata` resta disponibile per compatibilità, così il codice
Python esistente continua a funzionare durante la migrazione.

## Pubblicazione release

Le nuove release PyPI devono essere pubblicate da GitHub Actions tramite PyPI Trusted
Publishing. Il workflow di rilascio non usa token PyPI salvati in locale o nei GitHub
secrets.

Prima della prima pubblicazione, configura su PyPI un pending Trusted Publisher che
corrisponda al workflow di rilascio del repository e usa un environment GitHub protetto
per approvare la pubblicazione.

Per pubblicare, crea una GitHub Release sul tag che corrisponde alla versione in
`pyproject.toml`. Lo script `release.sh` resta solo una verifica locale pre-rilascio:
non pubblica più su PyPI e non effettua il deploy della documentazione.

!!! INFO

    Questo progetto non è collegato ad ISTAT nè supportato da ISTAT ed è una iniziativa autonoma di [Massimiliano Moraca](https://massimilianomoraca.me/).

Questo repository è stato creato grazie a [MkDocs](https://www.mkdocs.org/), [Material for MkDocs](https://squidfunk.github.io/mkdocs-material) e [mkdocstring](https://mkdocstrings.github.io/).

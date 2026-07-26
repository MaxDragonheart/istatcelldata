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

L'installazione base include `pyarrow`, usato per gli intermedi
Parquet/GeoParquet nei workflow H3.

Le elaborazioni H3 usano un bordo robusto `boundary_ring_size=3` e scrivono gli
indicatori additivi come conteggi interi nella tabella attributi degli esagoni.

Per usare il backend opzionale Dask nelle elaborazioni H3 parallele:

```bash
pip install "istat-census-data[dask]"
```

## Rinomina del progetto e manutenzione

`istat-census-data` è la distribuzione PyPI mantenuta.

Il nome della distribuzione PyPI è `istat-census-data`. A partire dalla versione
2.0.0, l'unico package Python supportato da importare è `istat_census_data`:

```python
import istat_census_data
```

La vecchia pagina PyPI [`istatcelldata`](https://pypi.org/project/istatcelldata/)
non è più mantenuta e non riceverà nuove release, perché il progetto si è spostato su
[`istat-census-data`](https://pypi.org/project/istat-census-data/).

Aggiorna le dipendenze di installazione a `istat-census-data`.
Aggiorna anche il codice Python sostituendo `import istatcelldata` con
`import istat_census_data`.

## Tutorial notebook

I notebook sotto `notebooks/tutorial/` mostrano download, preprocessamento,
finalizzazione, catalogo degli indicatori, comparabilita' tra anni e workflow H3. I
notebook inglesi sono in `notebooks/tutorial/en/`.


!!! INFO

    Questo progetto non è collegato ad ISTAT nè supportato da ISTAT ed è una iniziativa autonoma di [Massimiliano Moraca](https://massimilianomoraca.me/).

Questo repository è stato creato grazie a [MkDocs](https://www.mkdocs.org/), [Material for MkDocs](https://squidfunk.github.io/mkdocs-material) e [mkdocstring](https://mkdocstrings.github.io/).

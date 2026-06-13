# ISTAT Cell Data

Con **ISTAT Cell Data** puoi ottenere facilmente il set di dati riferiti ai censimenti ISTAT in cui sono stati 
rilasciati anche i dati delle celle censuarie.

E' possibile scaricare e processare i dati dal 1991 al 2021.

## Installazione

```bash
pip install istat-census-data
```

## Rinomina del progetto e manutenzione

`istat-census-data` è la distribuzione PyPI mantenuta a partire dalla versione 1.4.0
ed è la continuazione del precedente progetto `istatcelldata`.

Il nome della distribuzione PyPI è `istat-census-data`, mentre il package Python
da importare resta `istatcelldata`:

```python
import istatcelldata
```

La vecchia distribuzione/repository `istatcelldata` non è più mantenuta e non riceverà
nuove release. Aggiorna le dipendenze di installazione da `istatcelldata` a
`istat-census-data`; il codice Python esistente può continuare a usare
`import istatcelldata`.

!!! INFO

    Questo progetto non è collegato ad ISTAT nè supportato da ISTAT ed è una iniziativa autonoma di [Massimiliano Moraca](https://massimilianomoraca.me/).

Questo repository è stato creato grazie a [MkDocs](https://www.mkdocs.org/), [Material for MkDocs](https://squidfunk.github.io/mkdocs-material) e [mkdocstring](https://mkdocstrings.github.io/).

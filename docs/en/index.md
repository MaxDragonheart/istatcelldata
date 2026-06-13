# ISTAT Cell Data

With **ISTAT Cell Data** you can easily obtain datasets from ISTAT censuses that include census grid cell data.

It is possible to download and process data from 1991 to 2021.

## Installation

```bash
pip install istat-census-data
```

## Project rename and maintenance

`istat-census-data` is the maintained PyPI distribution starting with version 1.4.0
and is the continuation of the previous `istatcelldata` project.

The PyPI distribution name is `istat-census-data`, while the Python package import
remains `istatcelldata`:

```python
import istatcelldata
```

The old `istatcelldata` distribution/repository is no longer maintained and will not
receive new releases. Update installation dependencies from `istatcelldata` to
`istat-census-data`; existing Python code can keep using `import istatcelldata`.

!!! INFO

    This project is not affiliated with or supported by ISTAT and is an independent initiative by [Massimiliano Moraca](https://massimilianomoraca.me/).

This repository was created using [MkDocs](https://www.mkdocs.org/), [Material for MkDocs](https://squidfunk.github.io/mkdocs-material), and [mkdocstring](https://mkdocstrings.github.io/).

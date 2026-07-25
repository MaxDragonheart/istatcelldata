# Documentation

The developed functions allow managing both census data and geodata in their entirety. You can
download data and geodata and then process them.

## Census Cell Data Over the Years

Census data differs from year to year not only in content but especially in the data structure
used by ISTAT itself.

In particular, the years 1991 and 2001 have the same data structure but are different from 2011
and 2021, which are similar to each other.

For 2021, there is also a complete change in file nomenclature as well as download URLs for data
only.

## Region Code

Starting from version `0.6.0`, it is possible to process data not necessarily for all of Italy but
also for one or more regions, as the user chooses. The choice of region or regions to process is
made using the code of the region of interest.

| **Code** | **Region**                   |
|----------|------------------------------|
| 01       | Piemonte                     |
| 02       | Valle d'Aosta/Vallée d'Aoste |
| 03       | Lombardia                    |
| 04       | Trentino-Alto Adige/Südtirol |
| 05       | Veneto                       |
| 06       | Friuli-Venezia Giulia        |
| 07       | Liguria                      |
| 08       | Emilia-Romagna               |
| 09       | Toscana                      |
| 10       | Umbria                       |
| 11       | Marche                       |
| 12       | Lazio                        |
| 13       | Abruzzo                      |
| 14       | Molise                       |
| 15       | Campania                     |
| 16       | Puglia                       |
| 17       | Basilicata                   |
| 18       | Calabria                     |
| 19       | Sicilia                      |
| 20       | Sardegna                     |

The source of the previous table is [this](https://www.istat.it/it/archivio/104317).

## Census Indicator Catalogue

The package exposes a machine-readable catalogue for ISTAT census section indicators. It replaces
the previous static shared-field list with one packaged JSON catalogue generated from the local
trace records for 1991, 2001, 2011, and 2021 plus a curated semantic mapping for known comparable
fields.

```python
from istat_census_data import (
    get_census_index_catalog,
    get_comparable_indexes,
    list_census_indexes,
)

available_2021_codes = list_census_indexes(year=2021)
catalog_2021 = get_census_index_catalog(year=2021)
strict_population_indexes = get_comparable_indexes(
    years=[1991, 2001, 2011, 2021],
    strict=True,
)
```

`get_census_index_catalog()` returns one row per `(year, source_code)` with these fields:

- `canonical_id`
- `year`
- `source_code`
- `label_it`
- `theme`
- `measure_type`
- `is_additive`
- `is_population_count`
- `comparable_group`
- `comparability_note`
- `source`

Use `is_additive` to identify count-like variables that can be considered for area-weighted
workflows. Identifiers, text columns, and unknown fields are marked as non-additive.

## Comparability Caveats

Code equality is not enough to compare indicators across years. For example, `P18` keeps the same
resident-population age-group meaning across all supported years, so it is mapped to the stable
group `resident_population_age_20_24`.

Other codes changed meaning. In the 2021 local trace, `P67` to `P82` are female age-group fields.
In older local traces, the same code range represented labour or occupational variables, so the
catalogue maps those 2021 fields semantically and does not compare them by field code alone.

Labour-force fields such as `P60`, `P61`, and `P62` are mapped for 1991, 2001, and 2011, but they
are reported with `2021` in `missing_years` when users request non-strict comparability across all
four years.

The 2021 census belongs to the permanent-census system and uses a different geocoding process from
the older traditional census rounds. Comparable groups should therefore be treated as documented
metadata, not as proof that every methodology detail is identical.

ISTAT has also published 2023 section-level data, but this package currently supports only 1991,
2001, 2011, and 2021. Adding 2023 support is outside the current package scope.

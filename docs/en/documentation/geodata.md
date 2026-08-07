# GeoData Module
The Geodata module provides tools for managing and preprocessing geographic data, including administrative boundaries and census data. The functions in this module facilitate reading, filtering, and converting data into formats suitable for geographic analysis, such as GeoDataFrame and GeoPackage.

New code should import from `istat_census_data`. The reference below is generated
from the implementation module so the full function documentation remains visible.

## H3 census estimates

Use `estimate_h3_census_indexes()` after creating the finalized `census_data.gpkg`
with `finalize_census_data()`. By default, the function reads layer `census<year>`,
uses the packaged census catalogue to select additive indicators available in the
layer, generates level-11 H3 cells for the AOI, and distributes source census-section values
by area-weighted interpolation.

```python
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from istat_census_data import estimate_h3_census_indexes, generate_h3_grid

aoi = gpd.GeoDataFrame(
    geometry=[box(12.0, 41.0, 12.2, 41.2)],
    crs="EPSG:4326",
)

h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    h3_resolution=11,
    indexes=["P1", "P2"],
    workers=4,
    chunk_size=5000,
    max_in_flight_chunks=4,
    output_path=Path("h3_census_2021.gpkg"),
)
```

The estimator enforces H3 resolution 11. The `h3_resolution` argument can be
omitted because level 11 is the default, but any other value is rejected.
H3 boundary cells are expanded by three neighbour rings by default through
`boundary_ring_size=3`, which avoids dropping cells that intersect complex AOI
edges.

`generate_h3_grid()` stores reuse metadata and a fingerprint in the returned
GeoDataFrame attributes. The fingerprint includes the normalized AOI CRS, H3
resolution, `boundary_ring_size`, `area_crs`, grid CRS, AOI bounds, AOI area, and
hashes of the validated unified AOI geometry. Advanced callers can pass that grid
back through `h3_grid` to avoid regenerating identical cells:

```python
h3_grid = generate_h3_grid(
    aoi=aoi,
    h3_resolution=11,
    boundary_ring_size=3,
)

h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=["P1", "P2"],
    h3_grid=h3_grid,
)
```

The estimator validates the fingerprint before reuse. A different AOI geometry,
even with the same bounding box, or a different grid-defining parameter causes a
clear error instead of silently reusing stale cells.

Additive index columns in the returned H3 table and written GeoPackage are stored
as integer counts. The estimator first validates the continuous area-weighted
calculation in `total_validation`, then allocates integer cell values with a
largest-remainder step and records post-allocation checks in
`integer_total_validation`. Density columns remain floating-point values.

The same workflow is available as an editable example script in
`scripts/estimate_h3_census.py`. Set the module-level values such as
`census_data_path`, `aoi_path`, `selected_year`, `selected_indexes`,
`boundary_ring_size`, `workers`, and `chunk_size`, then run the script. Use
`selected_indexes = []` to estimate every additive index from the catalogue that
is present in the source layer.

## H3 intermediate storage

H3 estimation uses Parquet/GeoParquet-backed intermediate storage by default.
`pyarrow` is a required package dependency, so no extra install is needed for this
mode. The estimator writes prepared census sections, prepared H3 grid chunks, and
compact chunk result files to a temporary workspace, then reads the chunk results
back for the final GeoPackage output.

This reduces peak RAM because workers do not need to return large GeoDataFrames to
the parent process. It also avoids building many result columns one by one when
`selected_indexes = []` expands to all additive indicators.

The default Parquet path also clips the H3 overlay grid to the AOI one chunk at a
time before estimation starts. Large AOIs therefore produce observable
`grid_chunks/` files instead of waiting for one full in-memory clipped H3 grid to
finish. Retained intermediate directories no longer include a full
`h3_grid.parquet` file.

Parallel chunk scheduling is bounded by `max_in_flight_chunks`. When the value is
omitted, the estimator schedules at most the active worker count at one time.
That default keeps Dask, thread, and process runs from queuing every AOI chunk in
memory at once.

Use `intermediate_dir` when you want predictable intermediate locations. Use
`keep_intermediates=True` to inspect retained files, and `reuse_intermediates=True`
to reuse matching retained chunk result files from the same directory.

```python
h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=[],
    workers=4,
    chunk_size=5000,
    max_in_flight_chunks=4,
    intermediate_dir=Path("h3_intermediates"),
    keep_intermediates=True,
)
```

Set `intermediate_storage="memory"` only when you explicitly want the legacy
in-memory path for small AOIs or debugging. The final user-facing output remains
GeoPackage unless you omit `output_path` and work with the returned GeoDataFrame
directly.

## Parallel execution and benchmarking

H3 estimation is serial by default: `workers=1`. For larger AOIs, set `workers`
above 1 and choose a `chunk_size` to split the H3 grid into deterministic
cell-owned chunks. Each H3 cell is processed by exactly one chunk, so parallel
results contain the same cells as the serial path and should match serial totals
within the estimator tolerance.

```python
h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=["P1", "P2"],
    workers=4,
    chunk_size=5000,
    max_in_flight_chunks=4,
)
```

With the default Parquet/GeoParquet intermediate storage, thread, process, and Dask
workers write one result file per chunk and return file paths to the parent
process. By default, the parent performs the final merge after chunks complete.
When `stream_output=True` is used with `output_path`, finalization streams those
result chunks directly to the GeoPackage, creates the layer spatial index and a
unique table index on `h3_index`, and returns a metadata-only GeoDataFrame with
`row_count` and validation tables in `attrs`. Use `parallel_backend="process"`
only after benchmarking on your machine: it can help CPU-bound overlays, but it
adds worker startup and disk I/O overhead.

Use the optional Dask backend when you want Dask to schedule the same deterministic
H3 chunks locally:

```bash
pip install "istat-census-data[dask]"
```

```python
h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=["P1", "P2"],
    workers=4,
    chunk_size=5000,
    parallel_backend="dask",
    max_in_flight_chunks=4,
)
```

The Dask backend currently uses Dask's local threaded scheduler and the same
Parquet chunk contract as the standard backends. It is an optional runtime path,
not a required dependency for normal package installs.

Start with `workers` no higher than the physical CPU cores available to the
process. For H3 level 11, `chunk_size` values between 2,000 and 10,000 cells are
a practical first range. Smaller chunks give earlier progress updates but create
more scheduling overhead; larger chunks reduce overhead but can leave workers
idle near the end of a run.

Keep `max_in_flight_chunks` equal to `workers` for the first large run. Increase
it only after benchmarking shows scheduling overhead is more important than
memory pressure. For large AOIs such as an entire region, prefer
`intermediate_storage="parquet"` and avoid Dask settings that queue more chunks
than the machine can comfortably hold in memory. In Parquet mode, `chunk_size`
also controls how many H3 cells are projected and clipped to the AOI during each
grid-preparation batch.

Use `scripts/benchmark_h3_estimation.py` on finalized data to compare settings
before running a large production AOI. Edit `worker_counts`, `chunk_sizes`,
`parallel_backend`, `max_in_flight_chunks`, `boundary_ring_size`,
`intermediate_storage`, `keep_intermediates`, `reuse_intermediates`, and `runs`
in the script. Keep `selected_indexes = []`
when you want the benchmark to estimate all additive catalogue indexes present in
the source layer.

The benchmark output reports elapsed seconds, H3 cell count, and whether total
validation passed for each worker/chunk setting. Records are logged and written to
JSON after every completed benchmark run, so long executions have observable
progress. Treat small AOI timings as a correctness and overhead check; medium or
large AOIs are more useful for deciding whether parallel execution actually helps.

### Configuring the benchmark script

`scripts/benchmark_h3_estimation.py` is configured by editing module-level
variables in the file. It is not intended to be used through CLI arguments.

```python
main_path = Path("/home/max/Desktop/census_test")
census_data_path = main_path / "census_data.gpkg"
aoi_path = main_path / "aoi.gpkg"
benchmark_output_path = main_path / "h3_benchmark.json"

selected_year = 2021
selected_indexes: list[str] = []
boundary_ring_size = DEFAULT_BOUNDARY_RING_SIZE

worker_counts = [1, 2, 4]
chunk_sizes = [DEFAULT_H3_CHUNK_SIZE]
parallel_backend = "thread"
max_in_flight_chunks = None

intermediate_storage = "parquet"
intermediate_dir = main_path / "h3_intermediates"
keep_intermediates = True
reuse_intermediates = False

runs = 1
```

Use `worker_counts = [1]` for a serial-only run. Include values greater than 1
to compare parallel execution. Start with `parallel_backend = "thread"`; test
`parallel_backend = "process"` or `parallel_backend = "dask"` only after a
baseline benchmark. The Dask backend requires the optional Dask install.
Leave `max_in_flight_chunks = None` to schedule at most the active worker count,
or set an explicit positive integer when you need repeatable batch sizing.

Keep `boundary_ring_size = DEFAULT_BOUNDARY_RING_SIZE` unless you are studying a
specific AOI edge case. The current default is 3 and is included in benchmark JSON
records so runs with different boundary coverage are comparable.

Set `reuse_intermediates = False` for a cold run that rebuilds intermediate
files. Set it to `True` only for a later warm run that should reuse compatible
retained chunks. Keep `keep_intermediates = True` when you want to inspect or
reuse the Parquet/GeoParquet files; set it to `False` to remove them after the
run.

## End-to-end H3 workflow

Use `run_h3_census_workflow()` or `scripts/run_h3_census_analysis.py` when you
want the selected census years to drive the whole pipeline. The workflow downloads
only the requested years, preprocesses them, finalizes `census_data.gpkg`, and then
writes one H3 level-11 output layer per year.

For same-AOI multi-year runs, the workflow generates the H3 grid once before the
year loop and passes it to each yearly estimate. Census source preparation,
overlay, validation, and layer writing still run independently for every year.

The editable example script `scripts/run_h3_census_analysis.py` exposes the same
workflow through module-level settings. Set `list_year`, `main_path`,
`aoi_path`, `list_region`, `municipalities_code`, and performance controls in the
script. Use `selected_indexes = []` to estimate all additive indicators available
in each selected year. The H3 level is fixed at 11 and the special/fictitious
section policy defaults to `exclude`.

The end-to-end workflow exposes the same PRP-012 performance controls as the
finalized-data estimator. Edit `workers`, `chunk_size`, `parallel_backend`, and
`max_in_flight_chunks` in the script to tune large jobs. After installing
`istat-census-data[dask]`, set `parallel_backend = "dask"` to use the optional
local Dask backend.

For multi-year regional runs, set `retain_results=False`. With the default
Parquet intermediate storage, the workflow then streams each yearly result layer
from `result_chunks/` to GeoPackage instead of materializing the full yearly
GeoDataFrame. The returned workflow result still records `row_counts`,
`total_validations`, and `integer_total_validations` for each year.

If the data already exists, skip completed stages by setting `run_download`,
`run_preprocess`, or `run_finalize` to `False` in the script.

When `--skip-finalize` is used, `<data-dir>/census_data.gpkg` must already exist.

The same process is available from Python:

```python
from pathlib import Path

import geopandas as gpd

from istat_census_data import run_h3_census_workflow

aoi = gpd.read_file("aoi.gpkg", layer="aoi")

result = run_h3_census_workflow(
    years=[2021],
    data_folder=Path("./census"),
    aoi=aoi,
    indexes=["P1", "P2"],
    municipality_codes=[58091],
    workers=4,
    chunk_size=5000,
    parallel_backend="thread",
    max_in_flight_chunks=4,
    retain_results=False,
)

print(result.output_path)
print(result.layers)
```

The method assumes uniform density inside each source census section. This is
transparent and preserves additive totals against the clipped source-cell total,
but it is not a dasymetric model and should not be interpreted as exact household
or building-level placement.

## Special and fictitious census sections

`estimate_h3_census_indexes()` flags source census sections whose section code
contains one of these markers:

| Marker | Meaning | Data delivered in those rows | H3 interpretation |
|---|---|---|---|
| `888888` | Fictitious sections for people without housing or without a fixed address who are registered in the municipal registry. ISTAT also documents their use for people registered through associations or reception facilities. | The rows can carry the same census variables released for section-level files. For these sections, population and person/family indicators may be meaningful, while dwelling or building indicators should not be read as physical conditions at the drawn polygon. | The geometry is conventional. ISTAT notes that these sections are drawn in uninhabited areas, preferably near the town hall. H3 densities over that polygon are therefore an allocation device, not a residential-location estimate. |
| `999999` | Fictitious sections related to contested zones claimed by two or more municipalities. | The rows can carry resident-individual counts for the municipality to which the contested geography was not assigned for census purposes. They can also flow through the normal section-level variable schema when present in the finalized layer. | Treat the result as an administrative allocation. Do not interpret the H3 cell as a precise location of residence unless the contested-zone geometry is analytically appropriate for your use case. |
| `7777777` | 2011 Abruzzo-only fictitious sections for municipalities affected by the April 2009 earthquake. | ISTAT documents these sections as the placement for families that, at the census date, were temporarily domiciled in a municipality different from their registry municipality. Additive population/family indicators may therefore be present, but their geometry is not ordinary residence geography. | Use care in local density maps and overlays: the rows preserve census accounting, but the geometry encodes a post-earthquake administrative convention. |

These markers are not treated as missing data, but H3 estimation excludes them by
default because their conventional geometries can create misleading local
densities. With `special_section_policy="exclude"`, the estimator removes these
source rows before the area-weighted overlay; totals in the result therefore
exclude those records.

Use `special_section_policy="include"` only when you need full census accounting
inside the AOI and accept that conventional polygons can receive people who are
not physically distributed there. In that mode, the estimator includes their
values in the area-weighted overlay and sets `intersects_special_section=True`
for any H3 cell receiving area from one of them.

Use a stricter policy when that convention is not acceptable:

```python
h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=["P1"],
    special_section_policy="raise",
)
```

- `exclude`: default for H3 processes; remove these source rows before estimating,
  so totals exclude those records.
- `include`: keep the rows and flag intersecting H3 cells.
- `raise`: stop with an error if any special or fictitious section intersects the
  AOI.

Inspect flagged output cells with:

```python
flagged_cells = h3_estimates[h3_estimates["intersects_special_section"]]
```

The script example exposes the same policy through the `special_section_policy`
argument passed to `run()`.

Sources: ISTAT documents `888888x` and `999999x` in
[Dati per sezioni di censimento](https://www.istat.it/notizia/dati-per-sezioni-di-censimento/).
ISTAT documents zones in contestation, sections for people without housing, and
the 2011 Abruzzo `7777777` convention in
[Basi territoriali: anni 1991, 2001, 2011 e 2021](https://www.istat.it/wp-content/uploads/2024/07/Descrizione-dei-dati-Basi-territoriali.pdf).

::: istat_census_data.geodata

::: istat_census_data.h3_estimation

::: istat_census_data.h3_workflow

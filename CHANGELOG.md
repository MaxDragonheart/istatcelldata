# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.3] - 2026-08-07

### Fixed
- Hardened H3 AOI grid generation for multi-million-cell regions by filtering
  candidate cells in bounded chunks with a prepared AOI geometry and Shapely
  vectorized predicates, reducing exposure to long Python-level GEOS predicate
  loops that previously hit a native `SIGSEGV` during real-data validation.

## [2.6.2] - 2026-08-05

### Fixed
- Hardened Parquet-backed H3 result finalization so unreadable result-chunk WKB
  geometries can be diagnosed and, for full-cell output, rebuilt from `h3_index`
  instead of losing a completed chunk run during the final merge.
- Added fatal exception logging to `scripts/run_h3_census_analysis.py` so the
  timestamped official run log records full tracebacks instead of leaving them
  only in terminal, tmux, or stderr output.

### Changed
- Real-data Ubuntu run documentation now explains how to recover retained H3
  intermediates after finalization failures and how to verify fatal traceback
  logging.

## [2.6.1] - 2026-08-04

### Fixed
- Changed the default Parquet-backed H3 estimator path to prepare AOI-clipped H3
  overlay grid chunks directly, avoiding the previous full-grid
  `_prepare_h3_overlay_grid()` clipping step before intermediate creation.
- Added progress logging for every prepared H3 overlay grid chunk, including
  retained positive-area cells and elapsed seconds.

### Changed
- Bumped the H3 intermediate metadata schema so retained Parquet caches are
  separated by the chunked grid-preparation layout and chunk size.
- Retained Parquet intermediate directories now store prepared H3 grid chunks
  under `grid_chunks/` instead of writing a full `h3_grid.parquet` file.

## [2.6.0] - 2026-07-27

### Added
- Added reusable H3 grid metadata and fingerprints to `generate_h3_grid()`.
- Added optional `h3_grid` reuse to `estimate_h3_census_indexes()` with
  validation of AOI bounds, AOI area, AOI geometry hash, CRS, H3 resolution,
  boundary ring size, and area CRS.
- Added workflow-level H3 grid reuse so multi-year same-AOI runs generate the
  H3 grid once and reuse it for every yearly overlay.

### Changed
- H3 intermediate metadata schema was bumped to separate retained chunk caches by
  reusable grid fingerprint.

## [2.5.0] - 2026-07-27

### Added
- Added `max_in_flight_chunks` to H3 estimation, workflow, benchmark, and example
  scripts so thread, process, and optional Dask chunk execution can be scheduled
  in bounded batches.
- Added `retain_results` to the end-to-end H3 workflow so large multi-year
  output-writing runs can discard full yearly GeoDataFrames after writing while
  keeping row counts and validation metadata.
- Added progress logging for H3 year start/end, prepared input sizes, bounded
  chunk batches, and GeoPackage writes.

### Changed
- Dask H3 execution no longer calls `compute()` with every chunk task at once.
  It computes bounded batches using the same Parquet chunk contract.
- Thread and process H3 execution now refill a bounded future queue instead of
  submitting every chunk at once.
- The editable all-year H3 workflow script defaults to `retain_results=False` to
  reduce peak memory after each yearly layer is written.

## [2.4.1] - 2026-07-26

### Fixed
- Fixed H3 municipality filtering when finalized historical census layers store
  `PRO_COM` as an integral floating-point value such as `63049.0`. The H3 direct
  estimator and end-to-end workflow now treat equivalent integer municipality
  code representations consistently.

## [2.4.0] - 2026-07-26

### Added
- Added exported `DEFAULT_BOUNDARY_RING_SIZE` for H3 level-11 workflows and scripts.
- Added `integer_total_validation` metadata for post-allocation H3 integer counts.
- Added `boundary_ring_size` configuration to the editable H3 benchmark, direct
  estimation, and end-to-end workflow scripts.

### Changed
- H3 grid generation now defaults to `boundary_ring_size=3` to keep boundary
  cells that intersect complex AOI edges and avoid total-validation failures
  caused by under-covered AOI borders.
- H3 additive index columns are now written as integer counts in returned
  GeoDataFrames and final GeoPackage outputs. The continuous area-weighted
  validation remains available in `total_validation`; density columns remain
  floating-point values.
- H3 Parquet intermediate metadata schema was bumped so retained caches are
  separated from earlier boundary-ring and chunk-column behavior.

## [2.3.0] - 2026-07-26

### Added
- Added mandatory `pyarrow` support for H3 Parquet/GeoParquet intermediate
  processing.
- Added Parquet/GeoParquet-backed H3 intermediate execution with retained and
  reusable chunk result files.
- Added H3 controls for `intermediate_storage`, `intermediate_dir`,
  `keep_intermediates`, and `reuse_intermediates`.
- Added benchmark progress logging before and after every worker/chunk/run
  combination.
- Added incremental benchmark JSON writing after every completed run.
- Added tests for retained intermediates, Dask Parquet chunk execution,
  incremental benchmark output, and fragmentation-warning avoidance.

### Changed
- H3 estimation now defaults to Parquet/GeoParquet-backed intermediates while
  keeping GeoPackage as the default final output format.
- H3 contribution and density columns are built in batches to avoid Pandas/
  GeoPandas frame fragmentation on all-additive index runs.
- Thread, process, and optional Dask H3 workers now exchange chunk result paths
  instead of returning large GeoDataFrames in the default storage mode.
- H3 scripts expose editable module-level intermediate-storage settings.

### Upgrade Notes
- Install or upgrade with `pip install --upgrade istat-census-data`.
- `pyarrow` is now installed with the base package because it is required for the
  default H3 intermediate storage mode.
- Dask remains optional; install it with `pip install "istat-census-data[dask]"`.
- Set `intermediate_storage="memory"` only when you explicitly need the legacy
  in-memory path for small AOIs or debugging.

## [2.2.0] - 2026-07-26

### Added
- Added expanded tutorial notebooks with study-first guidance before running the
  download, preprocessing, finalization, catalogue, H3 estimation, workflow, and
  benchmarking procedures.
- Added English tutorial notebooks for the advanced catalogue and H3 procedures.
- Added Italian tutorial notebooks `d_*`, `e_*`, and `f_*` for catalogue
  comparability, H3 estimation, and H3 workflow/benchmarking.
- Added regression coverage for tutorial notebook structure and expected content.

### Changed
- Aligned the post-2.0.0 H3 scripts with the syntax style of the older project
  scripts by using editable module-level configuration instead of CLI-first
  argument parsing.
- Changed H3 index selection so `selected_indexes = []` in the example scripts,
  and an empty index iterable in the public H3 API, selects all additive indexes
  available for the layer.
- Updated H3 documentation and tutorial guidance to describe editable script
  settings and the empty-selection convention.

### Upgrade Notes
- Install or upgrade with `pip install --upgrade istat-census-data`.
- Use `selected_indexes = []` in H3 scripts when all additive census indexes should
  be estimated.
- H3 scripts remain editable processing examples; configure their module-level
  variables before running them directly.

## [2.1.0] - 2026-07-25

### Added
- Added a packaged census indicator catalogue with public APIs for listing indexes and
  selecting comparable cross-year census indicators.
- Added fixed level-11 H3 grid generation and area-weighted census estimation APIs.
- Added user-facing H3 estimation and selected-year end-to-end workflow scripts.
- Added deterministic H3 overlay chunking with thread, process, and optional Dask
  backends, plus benchmark tooling.

### Changed
- H3 estimation workflows default to excluding special/fictitious census sections and
  document the interpretation limits for those records.
- The selected-year H3 workflow exposes worker count, chunk size, and backend controls.

### Upgrade Notes
- Install or upgrade with `pip install --upgrade istat-census-data`.
- Install optional Dask support with `pip install "istat-census-data[dask]"`.
- This release adds public functionality without breaking the 2.0.0
  `istat_census_data` import path.

## [2.0.0] - 2026-07-25

### Removed
- Removed the legacy `istatcelldata` Python import package.
- Removed the compatibility facade that re-exported the implementation through
  `istatcelldata`.

### Changed
- Moved the implementation package to `istat_census_data`.
- Updated package metadata, tests, CI coverage, mypy, docs, and mkdocstrings to use
  `istat_census_data` only.

### Upgrade Notes
- Install or upgrade with `pip install --upgrade istat-census-data`.
- Replace Python imports from `istatcelldata` with `istat_census_data`.
- This is a breaking change and requires code updates for users still importing
  `istatcelldata`.

## [1.5.0] - 2026-06-13

### Added
- Added the preferred `istat_census_data` Python import facade for the
  `istat-census-data` distribution.
- Added regression tests to verify that `istat_census_data` and `istatcelldata`
  expose the same metadata, public objects, and submodules without import warnings.

### Changed
- Updated scripts, tutorials, documentation, and CI examples to use
  `istat_census_data` as the preferred import path.
- Kept the existing `istatcelldata` import path available for compatibility during
  the migration period.

### Upgrade Notes
- Install or upgrade with `pip install --upgrade istat-census-data`.
- New code should import `istat_census_data`.
- Existing code that imports `istatcelldata` continues to work in this release.

## [1.4.0] - 2026-06-12

### Changed
- Renamed the installable distribution from `istatcelldata` to `istat-census-data`.
- Kept the Python import package unchanged as `istatcelldata` for backward-compatible
  imports.
- Updated package metadata, documentation links, badges, installation examples, and
  tutorial installation text for the new distribution name.

### Upgrade Notes
- Install or upgrade with `pip install --upgrade istat-census-data`.
- Existing Python code should continue importing `istatcelldata`.
- `istat-census-data` is the maintained continuation of the previous `istatcelldata`
  distribution.
- The old `istatcelldata` distribution/repository is no longer maintained and will not
  receive new releases. Update dependency declarations from `istatcelldata` to
  `istat-census-data`.

## [1.3.0] - 2025-12-03

### Added
- **Explicit Optional Type Hints**: Added proper type annotations for optional parameters following PEP 484 standards, improving IDE support and static type checking
- **GitHub Actions CI/CD**: Comprehensive automated testing and documentation deployment workflows
  - Automated test suite execution on Python 3.10, 3.11, and 3.12
  - Automatic deployment of bilingual documentation to GitHub Pages
  - Status badges for build, coverage, Python versions, PyPI, and license
- **Release Documentation**: Added comprehensive guides for package maintenance and deployment
- **Test Coverage Improvements**: Expanded test suite achieving 94.25% code coverage (up from ~60%)
  - Added unit tests for core functionality
  - Added integration tests for data processing workflows
  - Added edge case testing for error handling

### Changed
- **Documentation Language**: Translated all inline documentation (docstrings, comments, logging messages) from Italian to English for better international accessibility
  - 2 function docstrings updated with Google Style format
  - 38 logging messages translated to natural English
  - Maintained Italian language support for end-user documentation via bilingual MkDocs site
- **Code Quality**: Achieved 100% compliance with Ruff linting standards (eliminated 102+ style inconsistencies)
- **Docstring Format**: Standardized all docstrings to Google Style format for consistency and readability
- **Type Safety**: Enhanced type annotations across 7 modules (36 parameters updated)
  - `logger_config.py`: 4 parameters
  - `census1991/utils.py`: 2 parameters
  - `census2021/utils.py`: 1 parameter
  - `executor/process.py`: 1 parameter
  - `executor/preprocess.py`: 1 parameter
  - `data.py`: 9 parameters
  - `geodata.py`: 18 parameters

### Improved
- **Testing Infrastructure**: Enhanced test organization and reliability
  - Clear separation between unit and integration tests
  - Deterministic test data for reproducible results
  - Skip markers for tests requiring external data downloads
- **Documentation Build**: Zero warnings in strict MkDocs build mode
- **Developer Experience**: Better IDE autocomplete and type checking support throughout the codebase

### Fixed
- **Type Checking**: Resolved 24 implicit Optional type violations that could cause mypy warnings in downstream projects
- **Code Style**: Fixed all Ruff linting violations for consistent code formatting
- **Import Issues**: Ensured package is properly importable with all modules exposed correctly

### Technical Details

**Quality Metrics:**
- Test Coverage: 94.25% (exceeds 80% target)
- Ruff Compliance: 100% (0 errors)
- Supported Python Versions: 3.10, 3.11, 3.12
- Documentation Languages: English + Italian

**Compatibility:**
- ✅ Fully backward compatible with v1.2.1
- ✅ No breaking API changes
- ✅ All existing code continues to work without modifications
- ✅ Type hints are additive and don't affect runtime behavior

**Upgrade Notes:**
- Direct upgrade from v1.2.1 to v1.3.0 requires no code changes
- Users will benefit from improved IDE support and documentation
- Logging messages now appear in English (previously Italian)

---

## [1.2.1] - Previous Release

See Git history for details on versions prior to v1.3.0.

---

## How to Upgrade

```bash
# Using pip
pip install --upgrade istat-census-data

# Using poetry
poetry update istat-census-data

# Verify installation
python -c "import istat_census_data; print(istat_census_data.__version__)"
```

---

## Links

- **Homepage**: https://maxdragonheart.github.io/istat-census-data/
- **Repository**: https://github.com/MaxDragonheart/istat-census-data
- **PyPI**: https://pypi.org/project/istat-census-data/
- **Documentation**: https://maxdragonheart.github.io/istat-census-data/
- **Issue Tracker**: https://github.com/MaxDragonheart/istat-census-data/issues

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

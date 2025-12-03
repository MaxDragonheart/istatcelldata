# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
pip install --upgrade istatcelldata

# Using poetry
poetry update istatcelldata

# Verify installation
python -c "import istatcelldata; print(istatcelldata.__version__)"
```

---

## Links

- **Homepage**: https://maxdragonheart.github.io/istatcelldata/
- **Repository**: https://github.com/MaxDragonheart/istatcelldata
- **PyPI**: https://pypi.org/project/istatcelldata/
- **Documentation**: https://maxdragonheart.github.io/istatcelldata/
- **Issue Tracker**: https://github.com/MaxDragonheart/istatcelldata/issues

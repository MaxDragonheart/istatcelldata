import json
from pathlib import Path

import pandas as pd
import pytest

import istat_census_data
from istat_census_data.catalog import (
    CATALOG_RESOURCE_PATH,
    SUPPORTED_CENSUS_YEARS,
    get_census_index_catalog,
    get_comparable_indexes,
    list_census_indexes,
)


def test_list_census_indexes_loads_all_supported_years():
    expected_counts = {
        1991: 207,
        2001: 204,
        2011: 152,
        2021: 127,
    }

    for year, expected_count in expected_counts.items():
        indexes = list_census_indexes(year=year)

        assert len(indexes) == expected_count
        assert "P18" in indexes


def test_root_package_exports_catalogue_api():
    assert "get_census_index_catalog" in istat_census_data.__all__
    assert "get_comparable_indexes" in istat_census_data.__all__
    assert "list_census_indexes" in istat_census_data.__all__
    assert callable(istat_census_data.get_census_index_catalog)
    assert callable(istat_census_data.get_comparable_indexes)
    assert callable(istat_census_data.list_census_indexes)


def test_packaged_catalog_uses_single_json_resource():
    resource_files = sorted(path.name for path in CATALOG_RESOURCE_PATH.parent.iterdir())
    payload = json.loads(CATALOG_RESOURCE_PATH.read_text(encoding="utf-8"))

    assert CATALOG_RESOURCE_PATH.name == "census_index_catalog.json"
    assert "census_index_catalog.json" in resource_files
    assert not [name for name in resource_files if name.startswith("tracciato_")]
    assert payload["supported_years"] == list(SUPPORTED_CENSUS_YEARS)
    assert set(payload["years"]) == {str(year) for year in SUPPORTED_CENSUS_YEARS}


def test_catalog_classifies_additive_counts_and_identifiers():
    catalog = get_census_index_catalog(year=1991)

    p18 = _single_row(catalog, "P18")
    assert "20 - 24 anni" in p18["label_it"]
    assert p18["theme"] == "population"
    assert p18["measure_type"] == "additive_count"
    assert bool(p18["is_additive"]) is True
    assert bool(p18["is_population_count"]) is True

    province_code = _single_row(catalog, "COD_PRO")
    assert province_code["measure_type"] == "identifier"
    assert bool(province_code["is_additive"]) is False
    assert province_code["comparable_group"] == ""


def test_catalog_normalizes_nome_campo_and_nome_campo_headers(tmp_path: Path):
    trace_file = tmp_path / "custom_trace.csv"
    trace_file.write_text(
        "NOME CAMPO;DESCRIZIONE\n"
        "P18;Popolazione residente - eta 20 - 24 anni\n"
        "COD_TEST;Codice di test\n",
        encoding="utf-8",
    )

    catalog = get_census_index_catalog(year=1991, trace_files={1991: trace_file})

    assert catalog["source_code"].tolist() == ["P18", "COD_TEST"]
    assert _single_row(catalog, "P18")["comparable_group"] == "resident_population_age_20_24"
    assert _single_row(catalog, "COD_TEST")["measure_type"] == "identifier"


def test_comparable_indexes_strict_maps_p18_across_all_supported_years():
    comparable = get_comparable_indexes(years=SUPPORTED_CENSUS_YEARS, strict=True)
    p18_group = comparable[comparable["comparable_group"] == "resident_population_age_20_24"]

    assert p18_group["year"].tolist() == [1991, 2001, 2011, 2021]
    assert p18_group["source_code"].tolist() == ["P18", "P18", "P18", "P18"]
    assert p18_group["missing_years"].tolist() == ["", "", "", ""]
    assert p18_group["is_strict_match"].tolist() == [True, True, True, True]


def test_comparable_indexes_reports_missing_years_for_labour_fields():
    non_strict = get_comparable_indexes(years=SUPPORTED_CENSUS_YEARS, strict=False)
    labour_group = non_strict[non_strict["comparable_group"] == "labour_force_total"]

    assert labour_group["year"].tolist() == [1991, 2001, 2011]
    assert labour_group["missing_years"].tolist() == ["2021", "2021", "2021"]
    assert labour_group["is_strict_match"].tolist() == [False, False, False]

    strict = get_comparable_indexes(years=SUPPORTED_CENSUS_YEARS, strict=True)
    assert "labour_force_total" not in strict["comparable_group"].tolist()


def test_2021_changed_code_mapping_is_semantic_not_code_only():
    catalog_2021 = get_census_index_catalog(year=2021)
    p67_2021 = _single_row(catalog_2021, "P67")

    assert p67_2021["canonical_id"] == "resident_population_female_age_under_5"
    assert p67_2021["theme"] == "population"
    assert "code-only matching is unsafe" in p67_2021["comparability_note"]

    catalog_1991 = get_census_index_catalog(year=1991)
    p67_1991 = _single_row(catalog_1991, "P67")

    assert p67_1991["canonical_id"] == "unmapped_1991_p67"
    assert p67_1991["comparable_group"] == ""

    non_strict = get_comparable_indexes(years=[1991, 2021], strict=False)
    female_age_group = non_strict[
        non_strict["comparable_group"] == "resident_population_female_age_under_5"
    ]

    assert female_age_group["year"].tolist() == [2021]
    assert female_age_group["missing_years"].tolist() == ["1991"]


def test_invalid_year_is_reported_clearly():
    with pytest.raises(ValueError, match="Unsupported census year 2023"):
        list_census_indexes(year=2023)


def _single_row(catalog: pd.DataFrame, source_code: str) -> pd.Series:
    row = catalog[catalog["source_code"] == source_code]
    assert len(row) == 1
    return row.iloc[0]

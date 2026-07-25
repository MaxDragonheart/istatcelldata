"""Catalogue ISTAT census indicators and curated cross-year comparability."""

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

import pandas as pd

from istat_census_data.utils import check_encoding

SUPPORTED_CENSUS_YEARS = (1991, 2001, 2011, 2021)
CATALOG_RESOURCE_PATH = Path(__file__).parent.joinpath("resources", "census_index_catalog.json")

CATALOG_COLUMNS = [
    "canonical_id",
    "year",
    "source_code",
    "label_it",
    "theme",
    "measure_type",
    "is_additive",
    "is_population_count",
    "comparable_group",
    "comparability_note",
    "source",
]

FIELD_NAME_COLUMNS = ("NOME CAMPO", "NOME_CAMPO")
LABEL_COLUMNS = ("DEFINIZIONE", "DESCRIZIONE")


def list_census_indexes(
    year: int,
    trace_files: Mapping[int, str | Path] | None = None,
) -> list[str]:
    """List available ISTAT source field codes for one supported census year.

    Args:
        year: Census year to inspect. Supported values are 1991, 2001, 2011,
            and 2021.
        trace_files: Optional mapping from census year to trace CSV path. Values
            supplied here override the packaged JSON catalogue for those years.

    Returns:
        Source field codes in the same order as the trace record.

    Raises:
        ValueError: If `year` is not supported or the trace/catalogue shape is invalid.
        FileNotFoundError: If the selected trace file is missing.
    """
    catalog = get_census_index_catalog(year=year, trace_files=trace_files)
    return [str(source_code) for source_code in catalog["source_code"].tolist()]


def get_census_index_catalog(
    year: int | None = None,
    trace_files: Mapping[int, str | Path] | None = None,
) -> pd.DataFrame:
    """Return census indicator metadata for one year or all supported years.

    The default catalogue is read from a packaged JSON resource generated from
    local ISTAT trace records and curated semantic mappings. Unknown fields are
    still listed, but they do not receive a cross-year comparable group.

    Args:
        year: Optional census year. If omitted, all supported years are returned.
        trace_files: Optional mapping from census year to trace CSV path. Values
            supplied here override the packaged JSON catalogue for those years.

    Returns:
        DataFrame with one row per `(year, source_code)` and the public catalogue
        columns documented in `CATALOG_COLUMNS`.

    Raises:
        ValueError: If `year` is not supported or a trace/catalogue shape is invalid.
        FileNotFoundError: If a selected trace file is missing.
    """
    years = _catalog_years(year)
    catalog_parts = [
        _build_year_catalog(selected_year, trace_files)
        if trace_files is not None and selected_year in trace_files
        else _load_packaged_catalog(selected_year)
        for selected_year in years
    ]
    catalog = pd.concat(catalog_parts, ignore_index=True)
    return catalog[CATALOG_COLUMNS]


def get_comparable_indexes(
    years: Iterable[int],
    strict: bool = True,
    trace_files: Mapping[int, str | Path] | None = None,
) -> pd.DataFrame:
    """Return indexes with curated semantic comparability across selected years.

    Args:
        years: Census years to compare.
        strict: If True, return only comparable groups present in every selected
            year. If False, return comparable groups present in at least one
            selected year and include missing-year metadata.
        trace_files: Optional mapping from census year to trace CSV path. Values
            supplied here override the packaged JSON catalogue for those years.

    Returns:
        DataFrame containing catalogue rows for comparable groups, plus
        `available_years`, `missing_years`, and `is_strict_match` columns.

    Raises:
        ValueError: If `years` is empty or contains an unsupported census year.
        FileNotFoundError: If a selected trace file is missing.
    """
    selected_years = _parse_years(years)
    selected_set = set(selected_years)
    catalog = get_census_index_catalog(trace_files=trace_files)
    comparable = catalog[
        catalog["year"].isin(selected_set) & catalog["comparable_group"].ne("")
    ].copy()

    group_years = {
        group: set(group_data["year"].tolist())
        for group, group_data in comparable.groupby("comparable_group")
    }
    strict_groups = {
        group for group, available_years in group_years.items() if selected_set <= available_years
    }

    if strict:
        comparable = comparable[comparable["comparable_group"].isin(strict_groups)].copy()

    comparable["available_years"] = comparable["comparable_group"].map(
        lambda group: _format_years(group_years[group] & selected_set)
    )
    comparable["missing_years"] = comparable["comparable_group"].map(
        lambda group: _format_years(selected_set - group_years[group])
    )
    comparable["is_strict_match"] = comparable["comparable_group"].isin(strict_groups)

    return comparable.sort_values(["comparable_group", "year", "source_code"]).reset_index(
        drop=True
    )


def _catalog_years(year: int | None) -> list[int]:
    return [_validate_year(year)] if year is not None else list(SUPPORTED_CENSUS_YEARS)


def _load_packaged_catalog(year: int) -> pd.DataFrame:
    payload = _read_catalog_payload()
    years_payload = payload.get("years")
    if not isinstance(years_payload, dict):
        raise ValueError("Packaged census catalogue is missing the 'years' object.")

    year_records = years_payload.get(str(_validate_year(year)))
    if not isinstance(year_records, list):
        raise ValueError(f"Packaged census catalogue is missing year {year}.")

    catalog = pd.DataFrame(year_records)
    missing_columns = [column for column in CATALOG_COLUMNS if column not in catalog.columns]
    if missing_columns:
        missing_column_list = ", ".join(missing_columns)
        raise ValueError(
            f"Packaged census catalogue for {year} is missing columns: {missing_column_list}."
        )

    return catalog[CATALOG_COLUMNS].copy()


def _read_catalog_payload() -> dict[str, Any]:
    if not CATALOG_RESOURCE_PATH.exists():
        raise FileNotFoundError(f"Packaged census catalogue was not found: {CATALOG_RESOURCE_PATH}")

    with CATALOG_RESOURCE_PATH.open(encoding="utf-8") as catalog_file:
        payload = json.load(catalog_file)

    if not isinstance(payload, dict):
        raise ValueError("Packaged census catalogue must contain a JSON object.")

    return cast(dict[str, Any], payload)


def _build_year_catalog(
    year: int,
    trace_files: Mapping[int, str | Path] | None,
) -> pd.DataFrame:
    trace = _load_trace(year, trace_files)
    rows = []
    for source_order, trace_row in trace.iterrows():
        source_code = _clean_string(trace_row["source_code"]).upper()
        label_it = _clean_string(trace_row["label_it"])
        if not source_code:
            continue

        base_metadata = _infer_metadata(year=year, source_code=source_code, label_it=label_it)
        curated_metadata = _CURATED_INDEXES.get((year, source_code), {})
        rows.append(
            {
                **base_metadata,
                **curated_metadata,
                "year": year,
                "source_code": source_code,
                "label_it": label_it,
                "source_order": source_order,
            }
        )

    catalog = pd.DataFrame(rows)
    catalog = catalog.sort_values("source_order").reset_index(drop=True)
    return catalog.drop(columns=["source_order"])


def _load_trace(
    year: int,
    trace_files: Mapping[int, str | Path] | None,
) -> pd.DataFrame:
    trace_path = _get_trace_path(year=year, trace_files=trace_files)
    if not trace_path.exists():
        raise FileNotFoundError(f"Census trace file for {year} was not found: {trace_path}")

    trace = pd.read_csv(
        filepath_or_buffer=trace_path,
        sep=";",
        encoding=check_encoding(data=trace_path),
        dtype=str,
    ).fillna("")
    trace.columns = [_clean_string(column) for column in trace.columns]

    field_column = _find_column(trace.columns, FIELD_NAME_COLUMNS, "field name")
    label_column = _find_column(trace.columns, LABEL_COLUMNS, "label")

    return trace.rename(columns={field_column: "source_code", label_column: "label_it"})[
        ["source_code", "label_it"]
    ]


def _get_trace_path(
    year: int,
    trace_files: Mapping[int, str | Path] | None,
) -> Path:
    validated_year = _validate_year(year)
    if trace_files is not None and validated_year in trace_files:
        return Path(trace_files[validated_year])

    raise FileNotFoundError(f"No trace override was provided for census year {validated_year}.")


def _find_column(columns: Iterable[str], candidates: tuple[str, ...], description: str) -> str:
    normalized_columns = {_clean_string(column): column for column in columns}
    for candidate in candidates:
        if candidate in normalized_columns:
            return normalized_columns[candidate]

    available_columns = ", ".join(normalized_columns)
    expected_columns = " or ".join(candidates)
    raise ValueError(
        f"Trace file is missing the {description} column. Expected {expected_columns}; "
        f"available columns: {available_columns}"
    )


def _infer_metadata(year: int, source_code: str, label_it: str) -> dict[str, object]:
    theme = _infer_theme(source_code=source_code, label_it=label_it)
    measure_type = _infer_measure_type(source_code=source_code, label_it=label_it)
    is_additive = measure_type == "additive_count"

    return {
        "canonical_id": f"unmapped_{year}_{source_code.lower()}",
        "theme": theme,
        "measure_type": measure_type,
        "is_additive": is_additive,
        "is_population_count": _is_population_count(label_it),
        "comparable_group": "",
        "comparability_note": "",
        "source": "local_trace",
    }


def _infer_theme(source_code: str, label_it: str) -> str:
    normalized_label = _normalize_for_matching(label_it)
    if source_code.startswith("PF") or "famigl" in normalized_label:
        return "family"
    if source_code.startswith("A") or _contains_any(
        normalized_label, ["abitaz", "allogg", "stanze", "superficie"]
    ):
        return "dwelling"
    if _contains_any(
        normalized_label,
        ["forze di lavoro", "occupat", "disoccup", "non appartenente", "casalingh"],
    ):
        return "labour"
    if _contains_any(
        normalized_label,
        ["laurea", "diploma", "licenza", "alfabet", "analfabet", "titolo di studio"],
    ):
        return "education"
    if _is_population_count(label_it):
        return "population"
    return "other"


def _infer_measure_type(source_code: str, label_it: str) -> str:
    normalized_label = _normalize_for_matching(label_it)
    if _is_identifier(source_code=source_code, normalized_label=normalized_label):
        return "identifier"
    if normalized_label.startswith("denominazione"):
        return "text"
    if _looks_like_additive_indicator(source_code=source_code, normalized_label=normalized_label):
        return "additive_count"
    return "unknown"


def _is_identifier(source_code: str, normalized_label: str) -> bool:
    identifier_prefixes = (
        "COD",
        "PRO_COM",
        "SEZ",
        "NSEZ",
        "ACE",
        "COM_ASC",
        "LOC",
        "ISAM",
        "ZIC",
    )
    return source_code.startswith(identifier_prefixes) or normalized_label.startswith("codice")


def _looks_like_additive_indicator(source_code: str, normalized_label: str) -> bool:
    indicator_prefixes = ("P", "PF", "A", "IT", "ST")
    indicator_words = (
        "popolazione",
        "famigl",
        "abitaz",
        "allogg",
        "stanze",
        "stranieri",
        "italiani",
        "occupat",
        "disoccup",
    )
    return source_code.startswith(indicator_prefixes) or _contains_any(
        normalized_label, indicator_words
    )


def _is_population_count(label_it: str) -> bool:
    normalized_label = _normalize_for_matching(label_it)
    return _contains_any(normalized_label, ["popolazione residente", "stranieri", "italiani"])


def _contains_any(value: str, fragments: Iterable[str]) -> bool:
    return any(fragment in value for fragment in fragments)


def _clean_string(value: object) -> str:
    return str(value).strip()


def _normalize_for_matching(value: str) -> str:
    return " ".join(value.lower().replace("�", "e").split())


def _validate_year(year: int) -> int:
    if year not in SUPPORTED_CENSUS_YEARS:
        supported_years = ", ".join(
            str(supported_year) for supported_year in SUPPORTED_CENSUS_YEARS
        )
        raise ValueError(f"Unsupported census year {year}. Supported years are: {supported_years}.")
    return year


def _parse_years(years: Iterable[int]) -> list[int]:
    parsed_years = []
    for year in years:
        validated_year = _validate_year(year)
        if validated_year not in parsed_years:
            parsed_years.append(validated_year)

    if not parsed_years:
        raise ValueError("At least one census year is required.")

    return parsed_years


def _format_years(years: Iterable[int]) -> str:
    return ",".join(str(year) for year in sorted(years))


def _index_metadata(
    canonical_id: str,
    theme: str,
    note: str,
    is_population_count: bool,
) -> dict[str, object]:
    return {
        "canonical_id": canonical_id,
        "theme": theme,
        "measure_type": "additive_count",
        "is_additive": True,
        "is_population_count": is_population_count,
        "comparable_group": canonical_id,
        "comparability_note": note,
        "source": "local_trace+curated_mapping",
    }


def _same_code_population_metadata(canonical_id: str) -> dict[str, object]:
    return _index_metadata(
        canonical_id=canonical_id,
        theme="population",
        note="Same source code and stable resident-population wording in local traces.",
        is_population_count=True,
    )


def _same_code_family_metadata(canonical_id: str) -> dict[str, object]:
    return _index_metadata(
        canonical_id=canonical_id,
        theme="family",
        note="Same family source code with stable resident-family wording in local traces.",
        is_population_count=False,
    )


_TOTAL_POPULATION_CODES = {
    "P1": "resident_population_total",
    "P2": "resident_population_male_total",
    "P3": "resident_population_female_total",
}

_AGE_BUCKETS = [
    ("under_5", "age_under_5"),
    ("5_9", "age_5_9"),
    ("10_14", "age_10_14"),
    ("15_19", "age_15_19"),
    ("20_24", "age_20_24"),
    ("25_29", "age_25_29"),
    ("30_34", "age_30_34"),
    ("35_39", "age_35_39"),
    ("40_44", "age_40_44"),
    ("45_49", "age_45_49"),
    ("50_54", "age_50_54"),
    ("55_59", "age_55_59"),
    ("60_64", "age_60_64"),
    ("65_69", "age_65_69"),
    ("70_74", "age_70_74"),
    ("over_74", "age_over_74"),
]

_LABOUR_CODES = {
    "P60": "labour_force_total",
    "P61": "labour_force_employed",
    "P62": "labour_force_unemployed",
    "P64": "labour_force_male_total",
    "P65": "labour_force_male_employed",
    "P66": "labour_force_male_unemployed",
}

_FAMILY_CODES = {
    "PF1": "resident_families_total",
    "PF3": "resident_families_one_member",
    "PF4": "resident_families_two_members",
    "PF5": "resident_families_three_members",
    "PF6": "resident_families_four_members",
    "PF7": "resident_families_five_members",
    "PF8": "resident_families_six_or_more_members",
}

_CURATED_INDEXES: dict[tuple[int, str], dict[str, object]] = {}

for census_year in SUPPORTED_CENSUS_YEARS:
    for source_code, canonical_id in _TOTAL_POPULATION_CODES.items():
        _CURATED_INDEXES[(census_year, source_code)] = _same_code_population_metadata(canonical_id)

    for code_number, (_, age_suffix) in zip(range(14, 30), _AGE_BUCKETS):
        _CURATED_INDEXES[(census_year, f"P{code_number}")] = _same_code_population_metadata(
            f"resident_population_{age_suffix}"
        )

    for code_number, (_, age_suffix) in zip(range(30, 46), _AGE_BUCKETS):
        _CURATED_INDEXES[(census_year, f"P{code_number}")] = _same_code_population_metadata(
            f"resident_population_male_{age_suffix}"
        )

    for source_code, canonical_id in _FAMILY_CODES.items():
        _CURATED_INDEXES[(census_year, source_code)] = _same_code_family_metadata(canonical_id)

    _CURATED_INDEXES[(census_year, "A2")] = _index_metadata(
        canonical_id="occupied_dwellings",
        theme="dwelling",
        note=(
            "Comparable occupied-dwelling count with wording differences: 1991 is generic, "
            "later years specify dwellings occupied by resident people."
        ),
        is_population_count=False,
    )

for census_year in (1991, 2001, 2011):
    for source_code, canonical_id in _LABOUR_CODES.items():
        _CURATED_INDEXES[(census_year, source_code)] = _index_metadata(
            canonical_id=canonical_id,
            theme="labour",
            note=(
                "Comparable labour-force count for 1991, 2001, and 2011 local traces; "
                "the local 2021 trace does not contain this field."
            ),
            is_population_count=True,
        )

for code_number, (_, age_suffix) in zip(range(67, 83), _AGE_BUCKETS):
    _CURATED_INDEXES[(2021, f"P{code_number}")] = _index_metadata(
        canonical_id=f"resident_population_female_{age_suffix}",
        theme="population",
        note=(
            "2021-only female age-group field. The same source code represented labour or "
            "occupational fields in older local traces, so code-only matching is unsafe."
        ),
        is_population_count=True,
    )


__all__ = [
    "CATALOG_COLUMNS",
    "SUPPORTED_CENSUS_YEARS",
    "get_census_index_catalog",
    "get_comparable_indexes",
    "list_census_indexes",
]

"""End-to-end workflow for census download, preparation, and H3 estimation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd

from istat_census_data.catalog import SUPPORTED_CENSUS_YEARS
from istat_census_data.config import PREPROCESSING_FOLDER
from istat_census_data.executor.download import download_census
from istat_census_data.executor.preprocess import preprocess_census
from istat_census_data.executor.process import finalize_census_data
from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    DEFAULT_H3_CHUNK_SIZE,
    DEFAULT_H3_WORKERS,
    DEFAULT_PARALLEL_BACKEND,
    DEFAULT_SPECIAL_SECTION_POLICY,
    REQUIRED_H3_RESOLUTION,
    GeoInput,
    estimate_h3_census_indexes,
)


@dataclass(frozen=True)
class H3CensusWorkflowResult:
    """Result metadata for an end-to-end H3 census workflow run."""

    data_folder: Path
    census_data_path: Path
    output_path: Path
    years: tuple[int, ...]
    layers: dict[int, str]
    results: dict[int, gpd.GeoDataFrame]


def run_h3_census_workflow(
    years: Iterable[int],
    data_folder: str | Path,
    aoi: GeoInput,
    *,
    indexes: str | Iterable[str] | None = "all_additive",
    output_path: str | Path | None = None,
    output_layer_prefix: str = "h3_census",
    region_list: Iterable[int] | None = None,
    municipality_codes: Iterable[int | str] | None = None,
    special_section_policy: str = DEFAULT_SPECIAL_SECTION_POLICY,
    area_crs: str | int = DEFAULT_AREA_CRS,
    aoi_crs: str | int | None = None,
    clip_output: bool = False,
    workers: int = DEFAULT_H3_WORKERS,
    chunk_size: int = DEFAULT_H3_CHUNK_SIZE,
    parallel_backend: str = DEFAULT_PARALLEL_BACKEND,
    run_download: bool = True,
    run_preprocess: bool = True,
    run_finalize: bool = True,
    delete_download_folder: bool = False,
    delete_preprocessed_data: bool = False,
) -> H3CensusWorkflowResult:
    """Run the full selected-year census pipeline before H3 estimation.

    This workflow downloads and prepares only the selected census years, finalizes
    them into `census_data.gpkg`, and writes one fixed level-11 H3 output layer
    per year.

    Args:
        years: One or more supported census years to download, process, finalize,
            and estimate.
        data_folder: Root folder used for downloaded, preprocessed, finalized, and
            H3 output data.
        aoi: Area of interest for H3 estimation.
        indexes: Source index codes or canonical catalogue IDs to estimate. The
            default `"all_additive"` estimates every additive index present in each
            finalized source layer. An empty iterable has the same all-additive
            behavior.
        output_path: Optional H3 output GeoPackage. Defaults to
            `<data_folder>/h3_census_data.gpkg`.
        output_layer_prefix: Prefix for output layers. Layer names are
            `<prefix><year>_r11`.
        region_list: Optional region codes passed to the download stage.
        municipality_codes: Optional municipality codes passed to preprocessing
            and H3 estimation.
        special_section_policy: Special/fictitious section policy. Defaults to
            `exclude` for H3 workflows.
        area_crs: Projected CRS used for area calculations.
        aoi_crs: CRS assigned to plain Shapely AOIs or AOIs without CRS.
        clip_output: If True, output geometries are clipped to the AOI.
        workers: Number of parallel H3 chunk workers. The default `1` keeps the
            serial path.
        chunk_size: Maximum number of H3 cells per parallel chunk.
        parallel_backend: Backend used for `workers > 1`. Supported values are
            `thread`, `process`, and `dask`. The `dask` backend requires the
            optional `istat-census-data[dask]` package extra.
        run_download: If True, run the selected-year download stage.
        run_preprocess: If True, run the selected-year preprocessing stage.
        run_finalize: If True, run the selected-year finalization stage.
        delete_download_folder: Passed to `preprocess_census()`.
        delete_preprocessed_data: Passed to `finalize_census_data()`.

    Returns:
        Workflow metadata and one result GeoDataFrame per selected year.

    Raises:
        ValueError: If no year is supplied or an unsupported year is requested.
        FileNotFoundError: If H3 estimation is requested before `census_data.gpkg`
            exists.
    """
    selected_years = _normalize_years(years)
    root_folder = Path(data_folder)
    root_folder.mkdir(parents=True, exist_ok=True)

    h3_output_path = (
        Path(output_path) if output_path is not None else root_folder / "h3_census_data.gpkg"
    )
    h3_output_path.parent.mkdir(parents=True, exist_ok=True)

    selected_regions = list(region_list) if region_list is not None else None
    selected_municipalities = _normalize_municipality_codes(municipality_codes)

    if run_download:
        download_census(
            years=list(selected_years),
            output_data_folder=root_folder,
            region_list=selected_regions,
        )

    if run_preprocess:
        preprocess_census(
            processed_data_folder=root_folder / PREPROCESSING_FOLDER,
            years=list(selected_years),
            output_data_folder=root_folder,
            delete_download_folder=delete_download_folder,
            municipalities_code=selected_municipalities,
        )

    if run_finalize:
        finalize_census_data(
            census_data_path=root_folder,
            years=list(selected_years),
            output_data_folder=root_folder,
            delete_preprocessed_data=delete_preprocessed_data,
        )

    census_data_path = root_folder / "census_data.gpkg"
    if not census_data_path.exists():
        raise FileNotFoundError(
            f"Finalized census GeoPackage was not found: {census_data_path}. "
            "Run the download/preprocess/finalize stages or provide an existing data folder."
        )

    layers: dict[int, str] = {}
    results: dict[int, gpd.GeoDataFrame] = {}
    for year in selected_years:
        output_layer = f"{output_layer_prefix}{year}_r{REQUIRED_H3_RESOLUTION}"
        results[year] = estimate_h3_census_indexes(
            census_data_path=census_data_path,
            year=year,
            aoi=aoi,
            h3_resolution=REQUIRED_H3_RESOLUTION,
            indexes=indexes,
            aoi_crs=aoi_crs,
            area_crs=area_crs,
            municipality_codes=selected_municipalities,
            special_section_policy=special_section_policy,
            clip_output=clip_output,
            workers=workers,
            chunk_size=chunk_size,
            parallel_backend=parallel_backend,
            output_path=h3_output_path,
            output_layer=output_layer,
        )
        layers[year] = output_layer

    return H3CensusWorkflowResult(
        data_folder=root_folder,
        census_data_path=census_data_path,
        output_path=h3_output_path,
        years=selected_years,
        layers=layers,
        results=results,
    )


def _normalize_years(years: Iterable[int]) -> tuple[int, ...]:
    selected_years = tuple(dict.fromkeys(int(year) for year in years))
    if not selected_years:
        raise ValueError("At least one census year is required.")

    unsupported_years = [year for year in selected_years if year not in SUPPORTED_CENSUS_YEARS]
    if unsupported_years:
        supported_years = ", ".join(str(year) for year in SUPPORTED_CENSUS_YEARS)
        requested_years = ", ".join(str(year) for year in unsupported_years)
        raise ValueError(
            f"Unsupported census year(s): {requested_years}. "
            f"Supported years are: {supported_years}."
        )

    return selected_years


def _normalize_municipality_codes(
    municipality_codes: Iterable[int | str] | None,
) -> list[int] | None:
    if municipality_codes is None:
        return None
    return [int(code) for code in municipality_codes]

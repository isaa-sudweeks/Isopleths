# Improved Isopleths

This repository contains the code, notebooks, intermediate datasets, and plotting outputs used to build and analyze ozone isopleth surfaces for the Utah case study described in the associated paper. The project centers on representing ozone as a function of aggregated VOC and NOx measurements, then testing how the resulting surfaces change after filtering by meteorology and smoke-related conditions.

At a high level, the workflow is:

1. Start from raw hourly AQS measurements.
2. Aggregate species into `VOC`, `NOx`, and `Ozone`.
3. Filter the data by solar radiation and, in the final workflow, by clearing index.
4. Optionally split the dataset into weekday/weekend or smoke/non-smoke subsets.
5. Fit interpolation surfaces with spline, RBF, and Gaussian process methods.
6. Export contour plots, 3D surfaces, and summary statistics used for interpretation.

## Quickstart

Create an environment and install the notebook dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

To work with the notebooks:

```bash
jupyter lab
```

Environment variables:

- Copy [`.env.example`](.env.example) to `.env` if you plan to use the archived EPA AQS downloader.
- Copy [`Synoptic/.env.example`](Synoptic/.env.example) to `Synoptic/.env` if you plan to use the Synoptic utilities.
- Required variables:
  - `AQS_EMAIL`
  - `AQS_KEY`
  - `MESOWEST_TOKEN`

## What Is In This Repository

This repo is notebook-driven. The current analysis workflow lives mainly in `Notebooks/` and `data_processing/process_data.py`. Older EPA AQS download utilities are preserved separately in `archived_aqs_download/`.

### Main directories

- `Notebooks/`
  - Current analysis notebooks for filtering, splitting, modeling, and plotting.
- `data_processing/`
  - Small, reusable script for aggregating raw air quality measurements into `VOC`, `NOx`, and `Ozone`.
- `documentation/`
  - Short method notes for the clearing-index workflow and spatial K-fold motivation.
- `Synoptic/`
  - Utilities related to Synoptic/MesoWest station lookup and dust-event work.
- `archived_aqs_download/`
  - Archived utilities for downloading raw EPA AQS data.
- [`.env.example`](.env.example)
  - Example environment variables for the archived EPA AQS downloader.
- [`Synoptic/.env.example`](Synoptic/.env.example)
  - Example environment variables for the Synoptic utilities.

## Repository Map

### Current workflow files

- [`data_processing/process_data.py`](data_processing/process_data.py)
  - Aggregates raw hourly measurements into `VOC`, `NOx`, and `Ozone`, then writes all-data and seasonal CSVs.
- [`Notebooks/Filter_Isopleth_By_SR.ipynb`](Notebooks/Filter_Isopleth_By_SR.ipynb)
  - Joins the ozone/VOC/NOx dataset with solar-radiation observations and filters rows below an `SR_THRESHOLD`.
- [`Notebooks/Filter_By_Clearing_Index.ipynb`](Notebooks/Filter_By_Clearing_Index.ipynb)
  - Pulls Salt Lake Smoke Management Forecast archives from IEM/AFOS, parses clearing index values, merges them into the dataset, and filters by threshold.
- [`Notebooks/weekend_weekday_split.ipynb`](Notebooks/weekend_weekday_split.ipynb)
  - Splits a filtered dataset into weekday and weekend subsets.
- [`Notebooks/Smoke Code/SmokeFilters.ipynb`](Notebooks/Smoke%20Code/SmokeFilters.ipynb)
  - Splits days into smoke and non-smoke categories using HMS smoke shapefiles and local county geometry.
- [`Notebooks/Spline_Isopleth_Surface.ipynb`](Notebooks/Spline_Isopleth_Surface.ipynb)
  - Fits a `scipy.interpolate.LSQBivariateSpline` surface, optionally performs K-fold/grid-search tuning, and renders 2D/3D surfaces.
- [`Notebooks/RBF_Isopleth_Surface.ipynb`](Notebooks/RBF_Isopleth_Surface.ipynb)
  - Fits an `RBFInterpolator` surface with masking logic to limit unsupported extrapolation.
- [`Notebooks/GPR_Isopleth_Surface.ipynb`](Notebooks/GPR_Isopleth_Surface.ipynb)
  - Fits a Gaussian process regression surface and reports cross-validated metrics.
- [`Notebooks/Mean_VOC_Analysis.ipynb`](Notebooks/Mean_VOC_Analysis.ipynb)
  - Computes mean VOC and mean NOx across groups of CSV datasets.
- [`Notebooks/No_Smoke_Max_Fall.ipynb`](Notebooks/No_Smoke_Max_Fall.ipynb)
  - Special-case notebook combining a no-smoke fall dataset with Synoptic radiation data and UV data for a radiation-focused analysis.

### Supporting method notes

- [`documentation/clearingIndex.md`](documentation/clearingIndex.md)
  - Documents how clearing index data are fetched, parsed, merged, and filtered.
- [`documentation/Spatial_KFold.md`](documentation/Spatial_KFold.md)
  - Explains the rationale for spatially aware model validation, although the current notebooks mostly use standard K-fold settings rather than a fully spatial blocking implementation.

### Archived data acquisition scripts

- [`archived_aqs_download/get_data.py`](archived_aqs_download/get_data.py)
  - Interactive downloader for hourly EPA AQS data by parameter and site.
- [`archived_aqs_download/helpers.py`](archived_aqs_download/helpers.py)
  - Helper functions used by the archived downloader.
- [`archived_aqs_download/README.md`](archived_aqs_download/README.md)
  - Notes on how to use the archived AQS downloader.

## Recommended Reproduction Path

If you want to reproduce the workflow used in the paper, use the current notebook path rather than the legacy CLI scripts.

### Step 1: Aggregate raw air quality data

Input:

- A raw AQS-style CSV with at least:
  - `dt`
  - `parameter`
  - `sample_measurement`

Use:

```bash
python -m data_processing.process_data path/to/raw.csv --output-dir path/to/output_dir
```

What it does:

- Pivots the raw hourly measurements into wide format by timestamp.
- Sums VOC species while excluding ozone, NOx, and related aggregate species to avoid double counting.
- Carries through `NOx` and converts `Ozone` from ppm to ppb.
- Writes:
  - `*_all.csv`
  - `*_winter.csv`
  - `*_spring.csv`
  - `*_summer.csv`
  - `*_fall.csv`

### Step 2: Filter by solar radiation

Use [`Notebooks/Filter_Isopleth_By_SR.ipynb`](Notebooks/Filter_Isopleth_By_SR.ipynb).

What it does:

- Loads an isopleth dataset and a solar-radiation CSV.
- Merges them on timestamp.
- Retains only rows where `solar_radiation_w_m2 >= SR_THRESHOLD`.

In the checked-in notebook, the default threshold is:

- `SR_THRESHOLD = 710`

### Step 3: Filter by clearing index

Use [`Notebooks/Filter_By_Clearing_Index.ipynb`](Notebooks/Filter_By_Clearing_Index.ipynb).

What it does:

- Downloads historical Salt Lake Smoke Management Forecast text products from the IEM AFOS archive.
- Parses daily clearing index values by air shed.
- Merges those values into the filtered ozone/VOC/NOx dataset.
- Drops rows based on a configurable clearing-index threshold.

In the checked-in notebook, the default configuration is:

- `TARGET_AIRSHED = "Northern Wasatch Front"`
- `CLEARING_INDEX_THRESHOLD = 1000`

The method note in [`documentation/clearingIndex.md`](documentation/clearingIndex.md) explains the parsing and date-handling assumptions in more detail.

### Step 4: Split the filtered datasets if needed

Use one or both of:

- [`Notebooks/weekend_weekday_split.ipynb`](Notebooks/weekend_weekday_split.ipynb)
- [`Notebooks/Smoke Code/SmokeFilters.ipynb`](Notebooks/Smoke%20Code/SmokeFilters.ipynb)

These produce:

- Weekday vs weekend subsets.
- Smoke vs non-smoke subsets based on smoke-shapefile intersection tests.

### Step 5: Fit the isopleth surface

Choose the notebook that matches the modeling approach discussed in the paper section you are reading:

- [`Notebooks/Spline_Isopleth_Surface.ipynb`](Notebooks/Spline_Isopleth_Surface.ipynb)
  - Bivariate spline surfaces with optional CV/grid search.
- [`Notebooks/RBF_Isopleth_Surface.ipynb`](Notebooks/RBF_Isopleth_Surface.ipynb)
  - RBF interpolation with configurable kernel, epsilon, smoothing, and a convex-hull-style mask.
- [`Notebooks/GPR_Isopleth_Surface.ipynb`](Notebooks/GPR_Isopleth_Surface.ipynb)
  - Gaussian process surface fitting with configurable kernel and K-fold evaluation.

All three notebooks assume the core predictors/response are:

- `VOC`
- `NOx`
- `Ozone`

Outputs generally include:

- A gridded surface over VOC-NOx space.
- 2D contour plots.
- Static 3D surface plots.
- Interactive Plotly 3D surfaces.
- Optional saved artifacts and parameter summaries in a selected `output_dir`.

### Step 6: Summarize group means

Use [`Notebooks/Mean_VOC_Analysis.ipynb`](Notebooks/Mean_VOC_Analysis.ipynb) to compute the mean VOC and NOx values across a directory of subsetted CSVs.

Example output:

- [`data/utah/filtered_by_clearing_index/mean_values_summary.csv`](data/utah/filtered_by_clearing_index/mean_values_summary.csv)

## Model Notes

### Spline notebook

The spline notebook is the closest descendant of the original workflow. It:

- Uses `LSQBivariateSpline`.
- Supports a configurable knot-count grid.
- Supports a progressive epsilon search.
- Uses standard K-fold CV to compare candidate settings.

### RBF notebook

The RBF notebook:

- Uses `scipy.interpolate.RBFInterpolator`.
- Lets you specify `kernel`, `epsilon`, and `smoothing`.
- Includes masking logic to avoid rendering unsupported regions far from the data cloud.

### GPR notebook

The GPR notebook:

- Uses `GaussianProcessRegressor`.
- Supports `RBF`, `Matern`, and `RationalQuadratic` kernels.
- Reports K-fold diagnostics such as RMSE, MAE, and `R²`.

## Archived AQS Download Workflow

The only retained pre-notebook scripts are the old EPA AQS download utilities in [`archived_aqs_download/`](archived_aqs_download). They are archival and useful only if you want to pull raw AQS data in the style of the original project.

Use:

```bash
python archived_aqs_download/get_data.py
```

Before running it, set:

- `AQS_EMAIL`
- `AQS_KEY`

The repository ships example environment files:

- [`.env.example`](.env.example)
- [`Synoptic/.env.example`](Synoptic/.env.example)

The old legacy surface-building and reformatting scripts were removed to keep the repository focused on the current notebook-based workflow.

## Environment And Dependencies

There is no modern lockfile or packaged environment in the repository root, so the easiest way to run the notebooks is to create a Python environment manually and install the libraries implied by the notebooks and scripts.

At minimum, expect to need:

- `jupyter`
- `pandas`
- `numpy`
- `scipy`
- `scikit-learn`
- `matplotlib`
- `seaborn`
- `plotly`
- `requests`
- `joblib`
- `python-dotenv`
- `openpyxl`

Additional notebooks/utilities may also require:

- `geopandas`
- `geopy`
- `windrose`

The root [`requirements.txt`](requirements.txt) is intended to cover the current notebook-based workflow.

## Citation And License

- License: [`LICENSE`](LICENSE)
- Citation metadata: [`CITATION.cff`](CITATION.cff)

## External Data And API Dependencies

Several parts of the workflow rely on external data or services:

- EPA AQS
  - Raw air quality measurements.
- Synoptic/MesoWest
  - Solar radiation and station metadata.
- Iowa Environmental Mesonet AFOS archive
  - Historical smoke-management forecast text products used to derive clearing index.
- HMS smoke shapefiles
  - Smoke vs non-smoke day classification in the smoke notebook.

Before rerunning notebooks, expect to update local file paths and, where required, provide valid credentials or tokens through environment variables.

## Configuration Caveats

This repository was used as an active research workspace, so older runs may still assume a specific local layout. Before rerunning anything, update the notebook configuration cells for:

- input data paths
- output directories
- threshold values
- station IDs
- local shapefile directories
- credentials or API tokens

Two practical notes:

- The notebooks are designed to be run top-to-bottom, not as imported modules.
- The `data/` and `plots/` directories are ignored by `.gitignore`, so the checked-in contents are examples, not guaranteed to be exhaustive.

## Reproducibility Caveats

Anyone reading the paper should be aware of a few limitations of the current codebase:

- The workflow is spread across notebooks rather than a single automated pipeline.
- Some files still contain hardcoded local paths.
- The active environment is not pinned with a complete dependency file.
- External API availability can affect reruns.
- The `documentation/Spatial_KFold.md` note describes spatial validation motivation, but the current modeling notebooks mostly use ordinary K-fold settings unless you modify them further.

Despite those caveats, the repo is still useful as a faithful research artifact because it preserves:

- the raw-to-processed data transformations,
- the filtering logic used to define the paper’s subsets,
- the model variants compared in the paper,
- and representative intermediate datasets and output directories.

## Suggested Reading Order

If you are reading the paper and want to map a figure or result back to the code, the most efficient order is:

1. Start with [`data_processing/process_data.py`](data_processing/process_data.py).
2. Read [`Notebooks/Filter_Isopleth_By_SR.ipynb`](Notebooks/Filter_Isopleth_By_SR.ipynb).
3. Read [`Notebooks/Filter_By_Clearing_Index.ipynb`](Notebooks/Filter_By_Clearing_Index.ipynb) together with [`documentation/clearingIndex.md`](documentation/clearingIndex.md).
4. Read the subset notebook relevant to the comparison in question:
   - [`Notebooks/weekend_weekday_split.ipynb`](Notebooks/weekend_weekday_split.ipynb)
   - [`Notebooks/Smoke Code/SmokeFilters.ipynb`](Notebooks/Smoke%20Code/SmokeFilters.ipynb)
5. Read the surface notebook that generated the figure family you care about:
   - [`Notebooks/Spline_Isopleth_Surface.ipynb`](Notebooks/Spline_Isopleth_Surface.ipynb)
   - [`Notebooks/RBF_Isopleth_Surface.ipynb`](Notebooks/RBF_Isopleth_Surface.ipynb)
   - [`Notebooks/GPR_Isopleth_Surface.ipynb`](Notebooks/GPR_Isopleth_Surface.ipynb)

## Contact Between Code And Paper

The paper should be interpreted against this repo as follows:

- The scientific signal of interest is the ozone response surface over VOC-NOx space.
- The main methodological variation is how the data are filtered and how the interpolation surface is fit.
- The newer notebooks are the primary source of truth for paper-related interpretation.

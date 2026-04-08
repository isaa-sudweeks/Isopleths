# Archived AQS Download Scripts

This folder preserves the older EPA AQS download utilities that were part of the original workflow before the repository became notebook-driven.

Files kept here:

- `get_data.py`
  - Interactive downloader for raw AQS hourly data.
- `helpers.py`
  - Helper functions used by `get_data.py` for parameter and class lookup.

These scripts are archival. They are useful if you need to pull raw AQS data in the same style as the original project, but they are not part of the current surface-building workflow.

Before running `get_data.py`, set:

- `AQS_EMAIL`
- `AQS_KEY`

Example:

```bash
export AQS_EMAIL=your_aqs_account_email
export AQS_KEY=your_aqs_api_key
python archived_aqs_download/get_data.py
```

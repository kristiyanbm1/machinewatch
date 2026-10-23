# Verification

Checked locally with Python 3.13.7.

- A fresh Python HTTPS download completed with certificate validation and file checksums.
- Full preparation completed using the NASA archive; all three models fitted.
- The 100 complete histories were split into 60/20/20 separate engines.
- The separate official test set contains another 100 engines.
- All 25 unit/API tests passed.
- `pip check` reported no broken requirements.
- Live HTTP predictions at cycles 1, 5, 10, 100 and 200 matched the saved offline
  predictions to the API's two-decimal rounding.
- Example SQL queries executed successfully.
- Browser checks covered engine selection, play/pause, reset, cycle selection,
  actual-life display and sensor switching. No browser console errors appeared.
- Narrow and wide layouts were inspected. The table scrolls on small screens.

The source ZIP excludes downloaded data, model artifacts, virtual environments
and caches. The local working folder retains the prepared dataset and model.
GitHub Actions is configured, but has not run remotely because nothing was published.

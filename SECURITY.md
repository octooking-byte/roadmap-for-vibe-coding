# Security policy

## Supported versions

Only the latest release gets fixes. Update with `claude plugin update roadmap-for-vibe-coding`.

## Reporting a vulnerability

Please do not open a public issue. Use the private report form instead:
https://github.com/octooking-byte/roadmap-for-vibe-coding/security/advisories/new

Include what you ran, what happened, and your version. Expect a first reply within 7 days.

## What the project runs

Four Python scripts that read and write your roadmap JSON and one HTML file: `엔진/궤적만들기.py`, `엔진/궤적점검.py`, `엔진/궤적접기.py`, `엔진/키별칭.py`. They use only the Python standard library and send nothing over the network. The built page loads one font from Google Fonts.

# GDELT

- **slug**: `gdelt`
- **category**: eventos / contexto geopolítico
- **utility_for_revmax**: Señales de eventos para event-pressure y shocks de demanda.
- **status**: `api-based`

## Source Links
- https://www.gdeltproject.org/
- https://www.gdeltproject.org/data.html
- https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf

## Files in this folder
- `data/public_datasets/gdelt/lastupdate.txt` (321 B)

## Format
- Mostly CSV/JSON/ZIP depending on source.

## Next Recommended Steps
- Validate schema and row counts.
- Add data dictionary for model features.
- Build ingestion/normalization notebook or script before training.

## Notes
- Downloaded GDELT reference/sample files.
- https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf -> <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'data.gdeltproject.org'. (_ssl.c:1129)>

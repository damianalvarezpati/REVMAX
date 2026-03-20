# Inside Airbnb Official (Priority Cities)

- **slug**: `inside_airbnb_official`
- **category**: pricing/listings/compset proxy
- **utility_for_revmax**: Listing-level supply and price context by city for compset pressure analysis.
- **status**: `downloaded`

## Source Links
- https://insideairbnb.com/get-the-data/
- https://insideairbnb.com/explore/

## Files in this folder
- `data/public_datasets/inside_airbnb_official/barcelona/calendar.csv.gz` (15.83 MB)
- `data/public_datasets/inside_airbnb_official/barcelona/listings.csv.gz` (9.26 MB)
- `data/public_datasets/inside_airbnb_official/barcelona/reviews.csv.gz` (125.72 MB)
- `data/public_datasets/inside_airbnb_official/berlin/calendar.csv.gz` (11.53 MB)
- `data/public_datasets/inside_airbnb_official/berlin/listings.csv.gz` (6.93 MB)
- `data/public_datasets/inside_airbnb_official/berlin/reviews.csv.gz` (69.25 MB)
- `data/public_datasets/inside_airbnb_official/lisbon/calendar.csv.gz` (20.71 MB)
- `data/public_datasets/inside_airbnb_official/lisbon/listings.csv.gz` (13.59 MB)
- `data/public_datasets/inside_airbnb_official/lisbon/reviews.csv.gz` (225.01 MB)
- `data/public_datasets/inside_airbnb_official/madrid/calendar.csv.gz` (20.63 MB)
- `data/public_datasets/inside_airbnb_official/madrid/listings.csv.gz` (11.75 MB)
- `data/public_datasets/inside_airbnb_official/madrid/reviews.csv.gz` (137.77 MB)
- `data/public_datasets/inside_airbnb_official/prague/calendar.csv.gz` (9.08 MB)
- `data/public_datasets/inside_airbnb_official/prague/listings.csv.gz` (5.32 MB)
- `data/public_datasets/inside_airbnb_official/prague/reviews.csv.gz` (96.38 MB)

## Format
- Mostly CSV/JSON/ZIP depending on source.

## Next Recommended Steps
- Validate schema and row counts.
- Add data dictionary for model features.
- Build ingestion/normalization notebook or script before training.

## Notes
- Priority cities: Berlin, Barcelona, Madrid, Lisbon, Prague.
- Existing files found in folder; skipped re-download to avoid duplication.

# RevMax Dataset-to-Canonical Mapping

This document maps key datasets to the RevMax canonical schema and highlights gaps.

## `inside_airbnb_official/*/listings.csv.gz`
- domain: `airbnb`
- mapping:
  - id -> source_dataset_record_id
  - last_scraped -> date
  - neighbourhood_cleansed -> neighbourhood
  - latitude/longitude -> latitude/longitude
  - property_type -> property_type
  - room_type -> room_type
  - price -> price
  - review_scores_rating -> review_score
- gaps / not-applicable:
  - currency often implicit
  - booking_channel missing
  - lead_time missing

## `inside_airbnb_official/*/calendar.csv.gz`
- domain: `airbnb`
- mapping:
  - date -> date
  - price -> price
  - available -> availability
  - listing_id -> source_dataset
- gaps / not-applicable:
  - city from folder
  - country from folder
  - channel missing

## `desktop_ingest_2026_03_20/travel.csv`
- domain: `ota`
- mapping:
  - date_time -> date
  - price_usd -> price
  - srch_destination_id -> neighbourhood/market proxy
  - orig_destination_distance -> demand/compset context proxy
  - is_mobile -> booking_channel context
- gaps / not-applicable:
  - currency for all rows may vary
  - review fields sparse

## `kaggle_vijeetnigam26_expedia_hotel/train.csv`
- domain: `ota`
- mapping:
  - date_time -> date
  - site_name/posa_continent -> booking_channel/source geo
  - orig_destination_distance -> demand/compset proxy
  - price_usd -> price
  - srch_booking_window -> lead_time
- gaps / not-applicable:
  - no direct neighbourhood
  - no direct review text

## `public_datasets/hotel_booking_demand/hotel_bookings.csv`
- domain: `hotel_core`
- mapping:
  - arrival_date_* -> date
  - adr -> price
  - lead_time -> lead_time
  - distribution_channel -> booking_channel
  - market_segment -> demand_proxy segment
- gaps / not-applicable:
  - no lat/long
  - no explicit compset

## `public_datasets/hotel_reviews_europe_515k/Hotel_Reviews.csv`
- domain: `reviews`
- mapping:
  - Review_Date -> date
  - Average_Score -> rating
  - Reviewer_Score -> review_score
  - lat/lng -> latitude/longitude
  - Hotel_Address -> neighbourhood/city parsing candidate
- gaps / not-applicable:
  - price missing
  - booking_channel missing

## `desktop_ingest_2026_03_20/Airbnb_Data.csv`
- domain: `airbnb`
- mapping:
  - log_price -> price (exp transform needed)
  - city -> city
  - property_type -> property_type
  - room_type -> room_type
  - review_scores_rating -> review_score
  - latitude/longitude -> latitude/longitude
- gaps / not-applicable:
  - currency implicit
  - availability not explicit

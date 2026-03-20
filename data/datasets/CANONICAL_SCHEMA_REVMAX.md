# RevMax Canonical Dataset Schema

This canonical schema is the target contract for normalized feature views across all dataset domains.

| field | description |
|---|---|
| `source_dataset` | Original dataset id or filename. |
| `source_type` | Kaggle / Inside Airbnb / Zenodo / API / local import. |
| `domain` | hotel_core / airbnb / ota / airline / reviews / other. |
| `city` | City identifier when available. |
| `country` | Country identifier when available. |
| `neighbourhood` | Neighborhood/zone label when available. |
| `date` | Observation date (booking/search/review/calendar). |
| `price` | Comparable price/rate measure. |
| `currency` | Currency code or symbol source. |
| `rating` | Rating value (property/experience). |
| `review_score` | Review-specific score when separate from rating. |
| `room_type` | Room/accommodation class. |
| `property_type` | Property category (hotel/apartment/etc). |
| `availability` | Availability indicator/count/proxy. |
| `demand_proxy` | Demand-related proxy metric. |
| `lead_time` | Days between booking and stay when available. |
| `booking_channel` | OTA/channel/distribution source. |
| `latitude` | Geo latitude. |
| `longitude` | Geo longitude. |

# Demand patterns (extracted)

## Hotel bookings (H1)
- Source: `data/datasets/kaggle_hotel_booking_demand/hotel_bookings.csv`
- Rows: 119390
### Correlations
- lead_time vs is_canceled: **0.29312335576042875**
- lead_time vs ADR: **-0.08696393202292418**
### Lead-time buckets → cancellation rate
See JSON for full table; highest-risk buckets inform hold/raise guardrails.

## Hotel reservations (INN)
- Rows: 36275
- lead_time vs avg_price: **-0.0625964654693634**

## Travel / OTA sample
- Booking rate by channel: see `demand_patterns.json` → `travel_ota.booking_rate_by_channel`

## Airline wide booking/revenue CSVs
- See `demand_patterns.json` → `airline_booking_revenue_wide` (explicitly not aggregated in this run).

# RevMax Pipeline Feed Map

| pipeline | primary datasets | notes |
|---|---|---|
| demand pipeline | `hotel_bookings.csv`, `Hotel Reservations.csv`, `travel.csv`, `12month_flight_booking.csv` | Lead-time, booking intensity, channel/context demand proxies. |
| reputation pipeline | `Hotel_Reviews.csv`, `tripadvisor_hotel_reviews.csv`, `booking_hotel.csv`, `tripadvisor_room.csv` | Sentiment/review-score features and confidence guardrails. |
| compset/proxy pipeline | `inside_airbnb_official/*`, `Airbnb_Data.csv`, `Airbnb_Open_Data.csv`, `travel.csv`, `expedia train/test` | Competitive price/availability proxy in city/time windows. |
| pricing context | `inside_airbnb_official/calendar.csv.gz`, `hotel_bookings*.csv`, `hotels_netherlands`, `hotel_rates_reviews_amenities` | Relative price posture and local market pressure. |
| dojo case generation | `travel.csv`, `inside_airbnb_official/*`, `hotel_bookings.csv`, `Hotel_Reviews.csv`, airline prediction sets | Build realistic multi-signal scenarios for deterministic engine validation. |

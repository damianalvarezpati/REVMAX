# Candidate rules (RevMax)

## HB-001 — **strong**
Longer lead_time is associated with higher cancellation probability (hotel booking demand dataset).
- Evidence: `{"pearson_r": 0.2931, "n": 119390}`
- Applies to: demand_pipeline, confidence, dojo

## AB-001 — **partial**
Higher review_scores_rating tends to associate with higher log_price (Airbnb listings sample).
- Evidence: `{"pearson_r": 0.0912, "n": 74111}`
- Applies to: pricing_context, reputation_guardrail, dojo

## CT-001 — **strong**
Weekend nightly proxy (realSum) is typically above weekday in multi-city Airbnb-style city files.
- Evidence: `{"median_weekend_premium_ratio": 1.0373, "n_cities": 10}`
- Applies to: pricing_context, forecasting_features, dojo

## OTA-001 — **partial**
Search distance proxy correlates weakly with booking outcome in Expedia-style travel sample; use as context feature, not standalone pricing driver.
- Evidence: `{"pearson_r": -0.0335, "n": 63915}`
- Applies to: compset_proxy, confidence_penalty, dojo

## RV-001 — **strong**
Reviewer score tracks hotel average score; use divergence as data-quality / outlier flag for reputation signals.
- Evidence: `{"pearson_r": 0.4014, "n": 120000}`
- Applies to: reputation_pipeline, confidence, dojo

## EVT-001 — **hypothetical**
Event pressure proxy from airline schedule or GDELT is not validated in this extraction; keep hypothetical until joined to hotel markets.
- Evidence: `{}`
- Applies to: event_pressure, future_enrichment

## Bucket proposals (summary)
See `candidate_rules.json` → `proposed_buckets_summary`.

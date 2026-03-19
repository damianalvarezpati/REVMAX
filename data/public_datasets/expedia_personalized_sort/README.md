# Expedia Personalized Sort

- **slug**: `expedia_personalized_sort`
- **category**: ranking / personalización / pricing relativo
- **utility_for_revmax**: Modelado de ordenación y sensibilidad a señales de precio/atributos.
- **status**: `login-required`

## Source Links
- https://www.kaggle.com/c/expedia-personalized-sort/data

## Files in this folder
- No files downloaded in this run.

## Format
- Mostly CSV/JSON/ZIP depending on source.

## Next Recommended Steps
- Validate schema and row counts.
- Add data dictionary for model features.
- Build ingestion/normalization notebook or script before training.

## Notes
- kaggle CLI NOT detected. Install with: python3 -m pip install kaggle
- Kaggle credentials detected.
- Competition requires login and rule acceptance.
- Open and accept rules: https://www.kaggle.com/competitions/expedia-personalized-sort/rules
- Error: 401 Client Error.

You don't have permission to access resource at URL: https://www.kaggle.com/competitions/expedia-personalized-sort
Please make sure you are authenticated and have accepted the competition rules which can be found at this location: https://www.kaggle.com/competitions/expedia-personalized-sort/rules

## Manual Commands (if Kaggle CLI is not configured)

```bash
# 1) Install Kaggle CLI and kagglehub
python3 -m pip install --upgrade kaggle kagglehub

# 2) Create Kaggle credentials folder/file
mkdir -p ~/.kaggle
cat > ~/.kaggle/kaggle.json <<'EOF'
{
  "username": "YOUR_KAGGLE_USERNAME",
  "key": "YOUR_KAGGLE_KEY"
}
EOF
chmod 600 ~/.kaggle/kaggle.json

# 3) Verify authentication
kaggle datasets list -s hotel-booking-demand | head

# 4) Download dataset examples
kaggle datasets download -d jessemostipak/hotel-booking-demand -p "./data/public_datasets/hotel_booking_demand" --unzip
kaggle datasets download -d jiashenliu/515k-hotel-reviews-data-in-europe -p "./data/public_datasets/hotel_reviews_europe_515k" --unzip
kaggle datasets download -d andrewmvd/trip-advisor-hotel-reviews -p "./data/public_datasets/tripadvisor_hotel_reviews" --unzip

# 5) Competition datasets (requires accepting rules in browser first)
open "https://www.kaggle.com/competitions/expedia-hotel-recommendations/rules"
open "https://www.kaggle.com/competitions/expedia-personalized-sort/rules"
kaggle competitions download -c expedia-hotel-recommendations -p "./data/public_datasets/expedia_hotel_recommendations"
kaggle competitions download -c expedia-personalized-sort -p "./data/public_datasets/expedia_personalized_sort"
```


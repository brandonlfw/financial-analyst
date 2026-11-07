import pandas as pd

ODBus_csv = "data/raw/CA_businesses.csv"

# Everyday consumer categories
NAICS_TO_CATEGORY = {
    "22": "Utilities",
    "44": "Retail and Groceries",
    "45": "Retail and Groceries",
    "62": "Healthcare and Social Assistance",
    "71": "Entertainment and Recreation",
    "72": "Accommodation and Food Services",
    "81": "Personal, Repair and Other Services",
}


odbus = pd.read_csv(
    ODBus_csv,
    dtype=str,
    keep_default_na=False,
    na_values=["", ".."],
)

target_cats_mask = odbus["derived_NAICS"].isin(NAICS_TO_CATEGORY)
training_data = odbus.loc[target_cats_mask].copy()


# Map each businesses' NAICS code to respective merchant category
training_data["category"] = training_data["derived_NAICS"].map(NAICS_TO_CATEGORY)

print(
    training_data[
        ["business_name", "derived_NAICS", "category", "business_description", "city"]
    ]
    .groupby("derived_NAICS")
    .head(5)
    .sort_values("derived_NAICS")
)

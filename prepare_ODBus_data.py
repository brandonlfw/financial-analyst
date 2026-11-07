import pandas as pd

ODBus_csv = "data/raw/CA_businesses.csv"


odbus = pd.read_csv(
    ODBus_csv,
    dtype=str,
    keep_default_na=False,
    na_values=["", ".."],
)

inspection_columns = ["business_name", "alt_business_name", "derived_NAICS"]

for column in inspection_columns:
    odbus[column] = odbus[column].str.strip()
    odbus[column] = odbus[column].replace("", pd.NA)

print(f"\nTotal rows: {len(odbus):,}")

print("\nMissing values:")
print(odbus[inspection_columns].isna().sum())

print("\nNAICS code lengths:")
print(odbus["derived_NAICS"].str.len().value_counts(dropna=False))

print("\nRows per NAICS code:")
print(odbus["derived_NAICS"].value_counts(dropna=False))


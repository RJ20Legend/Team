import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

file_path = os.path.join(DATA_DIR, "0000_train.parquet")

print("Trying to load:", file_path)

df = pd.read_parquet(file_path)

print("Loaded successfully!")
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
print(df.head())

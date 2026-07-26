from pathlib import Path
import re

import numpy as np
import pandas as pd
from sqlalchemy import exc
from sqlalchemy import exc


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
INPUT_FILE = DATA_DIR / "Nigerian Career Survey (Responses).xlsx"
EXCEL_SYNTHETIC_OUTPUT_FILE = DATA_DIR / "synthetic_career_dataset.xlsx"
EXCEL_COMBINED_OUTPUT_FILE = DATA_DIR / "combined_career_dataset.xlsx"

MIN_ROWS_PER_LABEL = 20
TARGET_COLUMN_CANDIDATES = ["career_path", "target", "career"]


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [
        re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")
        for col in normalized.columns
    ]
    normalized = normalized.rename(columns={"current_career_path": "career_path"})
    normalized = normalized.rename(columns={"who_influenced_your_current_career_path": "career_influence"})
    normalized = normalized.rename(columns={"igbo_/_hausa": "igbo_hausa"})
    return normalized


def infer_target_column(df: pd.DataFrame) -> str:
    for candidate in TARGET_COLUMN_CANDIDATES:
        if candidate in df.columns:
            return candidate

    for column in df.columns:
        if "career" in str(column).lower() or "label" in str(column).lower():
            return column

    raise ValueError("Could not find a target column for augmentation. Expected one of: career_path, target, career")


def sample_values(series: pd.Series, size: int, rng: np.random.Generator):
    clean = series.dropna()
    if clean.empty:
        return pd.Series(["Unknown"] * size, dtype="object")

    numeric = pd.to_numeric(clean, errors="coerce")
    if numeric.notna().any() and numeric.nunique() > 1:
        sampled = numeric.dropna().sample(n=size, replace=True, random_state=int(rng.integers(0, 2**32 - 1)))
        if sampled.std() > 0:
            jitter = rng.normal(0, sampled.std() / 6, size=size)
            sampled = sampled + jitter
        return sampled.astype(float)

    values = clean.astype(str)
    return values.sample(n=size, replace=True, random_state=int(rng.integers(0, 2**32 - 1)))


def build_synthetic_dataset(df: pd.DataFrame, target_column: str, min_rows_per_label: int = MIN_ROWS_PER_LABEL) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    synthetic_frames = []

    labels = sorted(df[target_column].dropna().astype(str).unique().tolist())
    for label in labels:
        label_rows = df[df[target_column].astype(str) == label]
        if label_rows.empty:
            continue

        synthetic_rows = []
        for _ in range(min_rows_per_label):
            row = {}
            for column in df.columns:
                if column == target_column:
                    row[column] = label
                    continue

                source_values = label_rows[column]
                row[column] = sample_values(source_values, size=1, rng=rng).iloc[0]

            synthetic_rows.append(row)

        synthetic_frames.append(pd.DataFrame(synthetic_rows))

    if not synthetic_frames:
        raise ValueError("No target labels were found to build a synthetic dataset")

    synthetic_df = pd.concat(synthetic_frames, ignore_index=True)
    synthetic_df[target_column] = synthetic_df[target_column].astype(str)
    return synthetic_df


def save_outputs(original_df: pd.DataFrame, synthetic_df: pd.DataFrame, combined_df: pd.DataFrame) -> None:
    synthetic_df.to_excel(EXCEL_SYNTHETIC_OUTPUT_FILE, index=False)
    combined_df.to_excel(EXCEL_COMBINED_OUTPUT_FILE, index=False)
    print(f"Excel export skipped: {exc}")


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    raw_df = pd.read_excel(INPUT_FILE)
    df = normalize_column_names(raw_df)
    target_column = infer_target_column(df)

    synthetic_df = build_synthetic_dataset(df, target_column=target_column, min_rows_per_label=MIN_ROWS_PER_LABEL)
    combined_df = pd.concat([df, synthetic_df], ignore_index=True)

    save_outputs(df, synthetic_df, combined_df)

    label_counts = combined_df[target_column].astype(str).value_counts()
    print(f"Loaded original dataset with {len(df)} rows")
    print(f"Created synthetic dataset with {len(synthetic_df)} rows")
    print(f"Combined dataset has {len(combined_df)} rows")
    print("Minimum rows per label in the synthetic set:")
    print(label_counts.head().to_string())
    print("\nSynthetic file written to:")
    print(f"- {EXCEL_SYNTHETIC_OUTPUT_FILE}")
    print("\nCombined file written to:")
    print(f"- {EXCEL_COMBINED_OUTPUT_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

from pathlib import Path

from datasets import load_dataset


def main() -> None:
    out_dir = Path("data/musiccaps_csv")
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("google/MusicCaps", split="train", cache_dir="data/hf_cache")
    df = ds.to_pandas()

    n_rows, n_cols = df.shape
    print(f"Загружено из HF: {n_rows} строк, {n_cols} столбцов")

    output_path = out_dir / "musiccaps_train.csv"
    df.to_csv(output_path, index=False)
    print(f"Сохранено: {output_path} ({n_rows} строк, {n_cols} столбцов)")


if __name__ == "__main__":
    main()
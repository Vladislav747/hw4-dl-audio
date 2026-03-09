#!/usr/bin/env python3
import argparse
from pathlib import Path

from datasets import load_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Предзагрузить датасет google/MusicCaps в локальный cache_dir"
    )
    parser.add_argument(
        "--cache-dir",
        default="data/hf_cache",
        help="Локальная папка кэша Hugging Face datasets",
    )
    parser.add_argument(
        "--split",
        default="train",
        help="Какую часть датасета предзагрузить (обычно train)",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(
        "google/MusicCaps",
        split=args.split,
        cache_dir=str(cache_dir),
    )

    print(f"Кэш готов. split={args.split}, rows={len(dataset)}, cache_dir={cache_dir}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import gzip
import json
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

DEFAULT_SAMPLE_RATE = 44100
# Доля valid при fallback-логике, если ключ (ytid, start_s) не найден в CSV.
DEFAULT_FALLBACK_VALID_RATIO = 0.1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Собрать train/valid манифесты .jsonl.gz для AudioCraft"
    )
    parser.add_argument("--metadata-dir", default="data/musiccaps_from_csv")
    parser.add_argument("--musiccaps-csv", default="data/musiccaps_csv/musiccaps_train.csv")
    parser.add_argument("--output-dir", default="data/manifests")
    parser.add_argument("--train-name", default="musiccaps_train.jsonl.gz", help="Имя train манифеста")
    parser.add_argument("--valid-name", default="musiccaps_valid.jsonl.gz", help="Имя valid манифеста")
    return parser.parse_args()


def build_split_map(csv_path: Path) -> Dict[Tuple[str, int], bool]:
    df = pd.read_csv(csv_path)
    # Проверяем, что CSV содержит обязательные колонки.
    required_cols = {"ytid", "start_s", "is_audioset_eval"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(
            f"CSV должен содержать колонки {sorted(required_cols)}, получено: {list(df.columns)}"
        )

    split_map: Dict[Tuple[str, int], bool] = {}
    # Создаем словарь для хранения ключей и их принадлежности к train или valid.
    for _, row in df.iterrows():
        ytid = str(row["ytid"]).strip()
        # Пропускаем строки без ytid - наличие ytid обязательно для построения ключа.
        if not ytid:
            continue
        start_sec = int(float(row["start_s"]))
        # Преобразуем значение is_audioset_eval в булево значение. - то что существует в датасете MusicCaps
        is_eval = bool(row["is_audioset_eval"])
        # Сохраняем ключ (ytid, start_sec) и его принадлежность к train или valid.
        split_map[(ytid, start_sec)] = is_eval
    return split_map


def make_manifest_record(meta_path: Path, meta: dict, sample_rate: int) -> dict:
    wav_path = Path(str(meta.get("wav_path", "")).strip())
    if not wav_path.is_absolute():
        wav_path = (Path.cwd() / wav_path).resolve()

    duration = float(meta.get("duration_sec", 10.0))
    caption = str(meta.get("caption", "")).strip()

    # Минимально-необходимые поля для AudioCraft + путь к расширенному metadata json.
    return {
        "path": str(wav_path),
        "duration": duration,
        "sample_rate": sample_rate,
        "description": caption,
    }



def write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    """Записывает список словарей в gzip-сжатый JSONL (по одной записи в строке)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    # читаем аргументы
    args = parse_args()
    metadata_dir = Path(args.metadata_dir)
    csv_path = Path(args.musiccaps_csv)
    output_dir = Path(args.output_dir)

    # проверяем, что папки откуда берем аудиофрагменты и метаданные существуют
    if not metadata_dir.exists():
        raise FileNotFoundError(f"Не найдена папка metadata: {metadata_dir}")
    # проверяем, что csv файл существует
    if not csv_path.exists():
        raise FileNotFoundError(f"Не найден CSV MusicCaps: {csv_path}")

    split_map = build_split_map(csv_path)
    # Все json-файлы с метаданными, отсортированные для детерминированности.
    json_files = sorted(metadata_dir.glob("*.json"))
    # инициализируем списки для train и valid манифестов
    train_rows: list[dict] = []
    valid_rows: list[dict] = []
    fallback_count = 0
    skipped_count = 0

    for idx, meta_path in enumerate(json_files):
        try:
            # Читаем JSON метаданные одного примера.
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            # если метаданные не являются словарем, пропускаем строку - не смогли прочитать метаданные
            if not isinstance(meta, dict):
                skipped_count += 1
                continue

            ytid = str(meta.get("ytid", "")).strip()
            start_sec = int(float(meta.get("start_sec", 0)))
             # Собираем запись манифеста.
            record = make_manifest_record(meta_path, meta, DEFAULT_SAMPLE_RATE)

            key = (ytid, start_sec)
            # Если ключ найден в CSV, используем его принадлежность к train или valid.
            if key in split_map:
                is_valid = split_map[key]
            else:
                # Fallback, если ключ не найден в CSV.
                # примерно каждый N-й элемент уходит в valid.
                period = max(int(round(1.0 / max(DEFAULT_FALLBACK_VALID_RATIO, 1e-6))), 1)
                is_valid = (idx % period) == 0
                fallback_count += 1

            if is_valid:
                valid_rows.append(record)
            else:
                train_rows.append(record)
        except Exception:
            # Любая ошибка при чтении/парсинге конкретного JSON
            # не прерывает весь процесс.
            skipped_count += 1

    # Финальные пути выходных файлов.
    train_path = output_dir / args.train_name
    valid_path = output_dir / args.valid_name
    # Сохраняем оба манифеста.
    write_jsonl_gz(train_path, train_rows)
    write_jsonl_gz(valid_path, valid_rows)

    print(
        f"Готово. train={len(train_rows)}, valid={len(valid_rows)}, "
        f"fallback_split={fallback_count}, skipped={skipped_count}"
    )
    print(f"train manifest: {train_path}")
    print(f"valid manifest: {valid_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from datasets import DownloadConfig, load_dataset


def get_stream_url(video_url: str) -> str:
    """Возвращает прямую ссылку на аудиопоток без скачивания видео."""
    raw_output = subprocess.check_output(
        ["yt-dlp", "-f", "bestaudio/best", "-g", "--no-playlist", video_url],
        text=True,
    )
    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"yt-dlp не вернул URL для {video_url}")
    return lines[0]


def download_wav_fragment(
    stream_url: str,
    output_path: Path,
    start_sec: float,
    duration_sec: float,
    sample_rate: int,
    channels: int,
) -> None:
    """Скачивает только нужный фрагмент потока напрямую в WAV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(start_sec),
            "-i",
            stream_url,
            "-t",
            str(duration_sec),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-y",
            str(output_path),
        ],
        check=True,
    )


def get_first_available(record: Dict[str, Any], keys: Iterable[str]) -> Optional[Any]:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return None


def build_record_id(record: Dict[str, Any], fallback_index: int) -> str:
    candidate = get_first_available(record, ("id", "track_id", "idx"))
    return str(candidate) if candidate is not None else str(fallback_index)


def process_single_url(args: argparse.Namespace) -> None:
    stream_url = get_stream_url(args.url)
    output = Path(args.output)
    download_wav_fragment(
        stream_url=stream_url,
        output_path=output,
        start_sec=args.start,
        duration_sec=args.duration,
        sample_rate=args.sample_rate,
        channels=args.channels,
    )
    print(f"Готово: {output}")


def process_musiccaps(args: argparse.Namespace) -> None:
    download_config = DownloadConfig(local_files_only=args.local_files_only)
    dataset = load_dataset(
        "google/MusicCaps",
        split=args.split,
        cache_dir=args.cache_dir,
        download_config=download_config,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    max_items = args.limit if args.limit is not None else len(dataset)
    skipped = 0
    saved = 0

    for idx, row in enumerate(dataset):
        if idx < args.offset:
            continue
        if saved >= max_items:
            break

        ytid = get_first_available(row, ("ytid", "youtube_id", "video_id"))
        if ytid is None:
            skipped += 1
            continue

        start_from_dataset = get_first_available(row, ("start_s", "start_sec"))
        start_sec = float(start_from_dataset) if start_from_dataset is not None else 0.0
        start_sec += float(args.start_shift)

        record_id = build_record_id(row, fallback_index=idx)
        file_stem = f"{idx:06d}_{record_id}"
        wav_path = output_dir / f"{file_stem}.wav"
        meta_path = output_dir / f"{file_stem}.json"

        if wav_path.exists() and not args.overwrite:
            skipped += 1
            continue

        video_url = f"https://www.youtube.com/watch?v={ytid}"

        try:
            stream_url = get_stream_url(video_url)
            download_wav_fragment(
                stream_url=stream_url,
                output_path=wav_path,
                start_sec=start_sec,
                duration_sec=args.duration,
                sample_rate=args.sample_rate,
                channels=args.channels,
            )

            metadata = {
                "source": "google/MusicCaps",
                "split": args.split,
                "index": idx,
                "id": record_id,
                "ytid": ytid,
                "video_url": video_url,
                "start_sec": start_sec,
                "duration_sec": args.duration,
                "caption": row.get("caption"),
                "wav_path": str(wav_path),
            }
            meta_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            saved += 1
            print(f"[OK] {saved:04d}: {wav_path.name}")
        except Exception as err:  # noqa: BLE001
            skipped += 1
            print(f"[SKIP] index={idx}, ytid={ytid}: {err}")

    print(f"Завершено. Сохранено: {saved}, пропущено: {skipped}, папка: {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Скачать аудиофрагменты без загрузки полного видео: "
            "yt-dlp (-g) + ffmpeg (10 секунд в WAV)"
        )
    )
    parser.add_argument(
        "--musiccaps",
        action="store_true",
        help="Режим пакетной загрузки из датасета google/MusicCaps",
    )

    parser.add_argument("--duration", type=float, default=10.0, help="Длительность фрагмента, сек")
    parser.add_argument("--sample-rate", type=int, default=44100, help="Частота дискретизации")
    parser.add_argument("--channels", type=int, default=2, help="Количество каналов")

    # Аргументы для single-url режима.
    parser.add_argument("url", nargs="?", help="Ссылка на YouTube видео (single-url режим)")
    parser.add_argument(
        "-o",
        "--output",
        default="fragment.wav",
        help="Выходной .wav файл (single-url режим)",
    )
    parser.add_argument("--start", type=float, default=0.0, help="С какой секунды начать")

    # Аргументы для MusicCaps режима.
    parser.add_argument("--split", default="train", help="Split датасета (например train)")
    parser.add_argument(
        "--cache-dir",
        default="data/hf_cache",
        help="Локальная папка кэша Hugging Face datasets",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Использовать только локальный кэш HF (без сетевых запросов)",
    )
    parser.add_argument("--output-dir", default="data/musiccaps", help="Куда сохранять .wav/.json")
    parser.add_argument("--offset", type=int, default=0, help="С какого индекса датасета начать")
    parser.add_argument("--limit", type=int, default=None, help="Сколько записей скачать")
    parser.add_argument(
        "--start-shift",
        type=float,
        default=0.0,
        help="Дополнительный сдвиг к start_s из датасета",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Перезаписывать уже существующие .wav",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.musiccaps:
        process_musiccaps(args)
        return

    if not args.url:
        parser.error("В single-url режиме нужно передать URL или включить --musiccaps.")
    process_single_url(args)


if __name__ == "__main__":
    main()

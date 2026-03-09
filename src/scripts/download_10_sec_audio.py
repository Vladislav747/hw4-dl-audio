#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

import ffmpeg
import pandas as pd

default_csv_path = "data/musiccaps_csv/musiccaps_train.csv"
default_output_dir = "data/musiccaps_from_csv"
default_duration = 10.0
default_sample_rate = 44100


# Скачиваем mp4 файл и возвращаем URL потока
def get_stream_url(
    video_url: str
) -> str:
    # Важно: используем -g, чтобы получить прямой URL потока, а не скачивать файл в cwd.
    command = ["yt-dlp", "-f", "b[ext=mp4]", "-g", "--no-playlist"]
    command.extend(["--cookies-from-browser", "chrome:Default"])
    command.append(video_url)

    raw_output = subprocess.check_output(command, text=True)
    lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"yt-dlp не вернул URL для {video_url}")
    return lines[0]


# Скачиваем фрагмент потока и сохраняем в WAV файл
def download_wav_fragment(
    stream_url: str,
    output_path: Path,
    start_sec: float,
    duration_sec: float,
    sample_rate: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg.input(stream_url, ss=start_sec, t=duration_sec)
        .output(
            str(output_path),
            acodec="pcm_s16le",
            ar=sample_rate,
            vn=None,
        )
        .overwrite_output()
        .global_args("-hide_banner", "-loglevel", "error")
        .run()
    )





def main() -> None:

    csv_path = Path(default_csv_path)
    output_dir = Path(default_output_dir)
    # создать папку если не существует
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    if df is None:
        raise ValueError("Не найден файл CSV")

    total_rows = len(df)

    saved = 0

    for idx, row in df.iterrows():
        if saved >= total_rows:
            break

        ytid = str(row["ytid"]).strip()
        if not ytid or ytid.lower() == "nan":
            saved += 1
            continue

        start_sec = float(row["start_s"])
        file_stem = f"{idx:06d}_{ytid}"
        wav_path = output_dir / f"{file_stem}.wav"
        meta_path = output_dir / f"{file_stem}.json"

        if wav_path.exists():
            saved += 1
            continue

        video_url = f"https://www.youtube.com/watch?v={ytid}"
        try:
            stream_url = get_stream_url(video_url)
            download_wav_fragment(
                stream_url=stream_url,
                output_path=wav_path,
                start_sec=start_sec,
                duration_sec=default_duration,
                sample_rate=default_sample_rate,
            )

            metadata = {
                "index": int(idx),
                "ytid": ytid,
                "video_url": video_url,
                "start_sec": start_sec,
                "duration_sec": default_duration,
                "caption": row.get("caption", ""),
                "wav_path": str(wav_path),
            }
            meta_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            saved += 1
            print(f"[OK] {saved:04d}: {wav_path.name}")
        except Exception as err:  # noqa: BLE001
            saved += 1
            print(f"[SKIP] index={idx}, ytid={ytid}: {err}")

    print(
        f"Завершено. Сохранено: {saved}, "
        f"CSV строк: {total_rows}, папка: {output_dir}"
    )


if __name__ == "__main__":
    main()

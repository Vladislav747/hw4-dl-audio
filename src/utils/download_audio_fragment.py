#!/usr/bin/env python3
import argparse
import subprocess

# Описываем аргументы командной строки:
# URL видео, имя выходного WAV, старт фрагмента и длительность.
parser = argparse.ArgumentParser(description="Скачать 10 секунд аудио в WAV без скачивания видео целиком")
parser.add_argument("url", help="Ссылка на видео")
parser.add_argument("-o", "--output", default="fragment.wav", help="Выходной .wav файл")
parser.add_argument("--start", default="0", help="С какой секунды начать")
parser.add_argument("--duration", default="10", help="Длительность фрагмента в секундах")
args = parser.parse_args()

# Получаем прямую ссылку именно на аудиопоток (не скачивая видео целиком).
# yt-dlp может вывести несколько строк, берем первую непустую.
stream_url = subprocess.check_output(
    ["yt-dlp", "-f", "bestaudio/best", "-g", "--no-playlist", args.url],
    text=True,
).splitlines()[0]

# ffmpeg скачивает только нужный фрагмент:
# -ss задает старт, -t задает длительность, -vn отключает видео.
# Выход кодируем в WAV (PCM 16-bit, 44.1 kHz, stereo).
subprocess.run(
    [
        "ffmpeg",
        "-ss",
        args.start,
        "-i",
        stream_url,
        "-t",
        args.duration,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-y",
        args.output,
    ],
    check=True,
)

print(f"Готово: {args.output}")

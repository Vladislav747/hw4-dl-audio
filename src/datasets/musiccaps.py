import json
import wave
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.datasets.base_dataset import BaseDataset
from src.utils.io_utils import ROOT_PATH, read_json


class MusicCapsDataset(BaseDataset):
    """
    Dataset for local MusicCaps clips indexed by json/jsonl file.
    """

    def __init__(
        self,
        index_path: str,
        sample_rate: int = 44100,
        mono: bool = True,
        name: str | None = None,
        *args,
        **kwargs,
    ):
        self.sample_rate = sample_rate
        self.mono = mono
        self.name = name or "musiccaps"

        index = self._load_index(index_path)
        super().__init__(index=index, *args, **kwargs)

    @staticmethod
    def _load_index(index_path: str) -> list[dict[str, Any]]:
        path = Path(index_path)
        if not path.is_absolute():
            path = ROOT_PATH / path

        if not path.exists():
            raise FileNotFoundError(f"Index not found: {path}")

        if path.suffix == ".json":
            data = read_json(str(path))
            if not isinstance(data, list):
                raise ValueError("Expected JSON list with dataset items")
            return data

        if path.suffix == ".jsonl":
            rows: list[dict[str, Any]] = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    rows.append(json.loads(line))
            return rows

        raise ValueError(f"Unsupported index format: {path.suffix}")

    @staticmethod
    def _assert_index_is_valid(index):
        for entry in index:
            if "path" not in entry:
                raise AssertionError("Each item must include 'path' to a wav file")
            # Keep compatibility with current training code.
            if "label" not in entry:
                entry["label"] = 0

    def load_object(self, path):
        wav_path = Path(path)
        if not wav_path.is_absolute():
            wav_path = ROOT_PATH / wav_path

        with wave.open(str(wav_path), "rb") as wav_file:
            src_sr = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            n_frames = wav_file.getnframes()
            raw_bytes = wav_file.readframes(n_frames)

        if sample_width != 2:
            raise ValueError(
                f"Only 16-bit PCM WAV is supported, got sample width: {sample_width}"
            )

        audio = np.frombuffer(raw_bytes, dtype=np.int16)
        if channels > 1:
            audio = audio.reshape(-1, channels).astype(np.float32)
            if self.mono:
                audio = audio.mean(axis=1)
            else:
                audio = audio.T
        else:
            audio = audio.astype(np.float32)

        audio = torch.from_numpy(audio / 32768.0)
        if audio.ndim == 1:
            audio = audio.unsqueeze(0)

        if src_sr != self.sample_rate:
            audio = torch.nn.functional.interpolate(
                audio.unsqueeze(0),
                size=int(audio.shape[-1] * self.sample_rate / src_sr),
                mode="linear",
                align_corners=False,
            ).squeeze(0)

        return audio

    def __getitem__(self, ind):
        data_dict = self._index[ind]
        audio = self.load_object(data_dict["path"])

        instance_data = {
            "data_object": audio.flatten(),
            "labels": int(data_dict.get("label", 0)),
            "caption": data_dict.get("caption", ""),
            "ytid": data_dict.get("ytid", ""),
            "audio_path": data_dict["path"],
        }
        instance_data = self.preprocess_data(instance_data)
        return instance_data

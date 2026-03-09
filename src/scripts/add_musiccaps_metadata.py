#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

REQUIRED_FIELDS = [
    "description",
    "general_mood",
    "genre_tags",
    "lead_instrument",
    "accompaniment",
    "tempo_and_rhythm",
    "vocal_presence",
    "production_quality",
]

SYSTEM_PROMPT = """Ты ассистент по музыкальной разметке.
Преобразуй входной caption в JSON СТРОГО по схеме:
{
  "description": "string",
  "general_mood": "string",
  "genre_tags": ["string"],
  "lead_instrument": "string",
  "accompaniment": "string",
  "tempo_and_rhythm": "string",
  "vocal_presence": "string",
  "production_quality": "string"
}
Требования:
- Верни только валидный JSON, без markdown и без пояснений.
- Все ключи обязательны.
- genre_tags должен быть массивом строк (минимум 1 тег).
- Если в caption чего-то нет, заполни наиболее вероятным кратким нейтральным значением."""

default_temperature = 0.2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Добавить metadata в json wav файла по caption через LLM"
    )
    parser.add_argument("--input-dir", default="data/musiccaps_from_csv")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0, help="С какого индекса в csv начинать обогащение")
    return parser.parse_args()


def apply_provider_defaults(args: argparse.Namespace) -> argparse.Namespace:
    if args.model is None:
        args.model = "qwen/qwen3.5-9b"
    if args.api_key_env is None:
        args.api_key_env = "OPENAI_API_KEY"
    return args


def build_client(args: argparse.Namespace) -> OpenAI:
    print("Building client...")
    api_key = args.api_key_env
    if not api_key:
        raise RuntimeError(
            f"Не найден ключ API в переменной окружения {args.api_key_env}"
        )
    return OpenAI(api_key=api_key)

# Приводим ответ модели к фиксированной схеме REQUIRED_FIELDS: - без этого в json файле будут некорректные значения
def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        # данные в genre_tags приходят в виде массива строк их надо разбить
        if field == "genre_tags":
            # если данные в genre_tags пришли в виде массива строк то надо разбить их на отдельные строки
            if isinstance(value, list):
                tags = [str(v).strip() for v in value if str(v).strip()]
                normalized[field] = tags if tags else [""]
            # если данные в genre_tags пришли в виде строки то добавляем ее в массив
            elif isinstance(value, str) and value.strip():
                normalized[field] = [value.strip()]
            else:
                normalized[field] = [""]
        # если данные пустые то добавляем пустую строку
        else:
            normalized[field] = str(value).strip() if value is not None else ""
    return normalized

# Парсим текст ответа модели в JSON
def parse_json_from_text(text: str) -> Dict[str, Any]:
    text = text.strip()
    # если текст начинается с ``` то удаляем его
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_]*\n?", "", text, count=1)
        text = re.sub(r"\n?```", "", text)

    decoder = json.JSONDecoder()
    try:
        data, _end_idx = decoder.raw_decode(text)
    except json.JSONDecodeError:
        # Ищем первый объект в тексте и парсим только его.
        match = re.search(r"\{", text)
        if not match:
            raise
        data, _end_idx = decoder.raw_decode(text[match.start() :])
    if not isinstance(data, dict):
        raise ValueError("LLM вернул не JSON-объект")
    return data


# Отправляем запрос к модели и получаем ответ в виде JSON
def llm_structured_caption(client: OpenAI, model: str, caption: str) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": caption},
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=default_temperature,
            response_format={"type": "json_object"},
            messages=messages,
        )
    except Exception:
        response = client.chat.completions.create(
            model=model,
            temperature=default_temperature,
            messages=messages,
        )
    content = response.choices[0].message.content or "{}"
    print(content, "content")
    return normalize_payload(parse_json_from_text(content))


def enrich_file(path: Path, client: OpenAI, model: str) -> str:
    raw = json.loads(path.read_text(encoding="utf-8"))
    print(raw, "raw")
    if not isinstance(raw, dict):
        return "skip: неправильный формат json"

    caption = str(raw.get("caption", "")).strip()
    if not caption:
        return "skip: no caption"

    required_keys_exists = all(key in raw for key in REQUIRED_FIELDS)

    if required_keys_exists:
        return "skip: уже обогащено"
    

    structured = llm_structured_caption(client, model, caption)
    raw.update(structured)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return "ok"


def main() -> None:
    args = apply_provider_defaults(parse_args())
    # создаем клиент для работы с LLM
    client = build_client(args)

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Папка не найдена: {input_dir}")

    # получить все json файлы в папке
    files = sorted(input_dir.glob("*.json"))
    # берем только с start_with_index по limit
    if args.offset:
        files = files[args.offset :]
    if args.limit is not None:
        files = files[: args.limit]

    ok_count = 0
    skip_count = 0
    err_count = 0

    for file_path in files:
        try:
            status = enrich_file(file_path, client, args.model)
            if status == "ok":
                ok_count += 1
            else:
                skip_count += 1
            print(f"[{status.upper()}] {file_path.name}")
        except Exception as err:  # noqa: BLE001
            err_count += 1
            print(f"[ERROR] {file_path.name}: {err}")

    print(
        f"Готово. Enriched={ok_count}, skipped={skip_count}, errors={err_count}, "
        f"dir={input_dir}"
    )


if __name__ == "__main__":
    main()

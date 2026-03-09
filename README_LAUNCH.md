```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

Запускаем из корня проекта
Загрузка кеша датасета google/MusicCaps
```bash
make download-musiccaps-local
```

Запускаем из корня проекта
Загрузка csv датасета google/MusicCaps в файл data/musiccaps_csv/musiccaps_train.csv
```bash
make download-musiccaps-csv-local
```

```bash
# 1) Скачать 10 секундные фрагменты wav по URL из csv
# Wav и json метаданные скачиваются в папку "data/musiccaps_from_csv"
# длительность 10 сек по умолчанию
make download-10-sec-audio

```
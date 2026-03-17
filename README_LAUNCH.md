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

Запуск обогащения данных через локальную модель
Должно быть включено LM Studio
Пример запуска:
```bash
python3 src/scripts/add_musiccaps_metadata.py \
  --input-dir data/musiccaps_from_csv \
  --limit 200
```

Запуск создания манифестов для audiocraft
```bash
make build-audiocraft-manifests
```


Создал форк audiocraft https://github.com/Vladislav747/audiocraft-fork

Импортируем форка в директорию выше директории запуска репы hw4-dl-audio
```bash
git clone git@github.com:Vladislav747/audiocraft-fork.git
```

Загрузка форка audiocraft

вместо пути /Users/vlad/Documents/Web/audiocraft-for - ваш путь до форкнутого репозитория локально в системе
```bash
source .venv/bin/activate
pip install dora-search
pip uninstall -y audiocraft
pip install -U pip setuptools wheel cython
pip install -e /Users/vlad/Documents/Web/audiocraft-fork --no-deps

```

На MacOs не запускается audiocraft на gpu
Generate | Epoch 1 | 20/50 - как уменьшить?
дообогатить данные
Перенести как то в пайп?
сгенерить первые по propmt

```bash
AUDIOCRAFT_DORA_DIR=/Users/vlad/Documents/Web/audiocraft-fork/outputs \
dora --package audiocraft --main_module train run --clear \
  solver=musicgen/musicgen_base_32khz \
  dset=audio/musiccaps_32khz \
  conditioner=text2music \
  datasource.train=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_train.jsonl.gz \
  datasource.valid=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_valid.jsonl.gz \
  datasource.evaluate=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_valid.jsonl.gz \
  datasource.generate=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_valid.jsonl.gz \
  datasource.max_sample_rate=44100 datasource.max_channels=2 \
  +dataset.info_fields_required=false \
  dataset.segment_duration=10 dataset.batch_size=1 dataset.num_workers=0 \
  dataset.train.num_samples=200 dataset.valid.num_samples=20 \
  optim.updates_per_epoch=5 optim.epochs=1 \
  evaluate.every=0 generate.every=0 evaluate.num_workers=0 generate.num_workers=0 \
  device=cpu autocast=false transformer_lm.memory_efficient=false \
  +conditioners.description.t5.autocast_dtype=null \
  optim.ema.device=cpu
```


```python
cd /Users/vlad/Documents/Web/audiocraft-fork
source venv-ac/bin/activate
python3 inference.py --device cpu --duration 12 --save-prompts-json
```
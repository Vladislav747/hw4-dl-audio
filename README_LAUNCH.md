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
Загрузка csv датасета google/MusicCaps
```bash
make download-musiccaps-csv-local
```
PYTHON ?= python3

ifneq (,$(wildcard .env))
include .env
export HF_TOKEN
export OPENAI_BASE_URL=http://localhost:1234/v1
export OPENAI_API_KEY=lm-studio
export AUDIOCRAFT_TEAM=default
export AUDIOCRAFT_DORA_DIR=/Users/vlad/Documents/Web/hw4-dl-audio/data/outputs
endif

MUSICCAPS_SPLIT ?= train
MUSICCAPS_OFFSET ?= 0
MUSICCAPS_LIMIT ?= 200
MUSICCAPS_DURATION ?= 10
MUSICCAPS_OUTPUT_DIR ?= data/musiccaps
MUSICCAPS_START_SHIFT ?= 0
MUSICCAPS_CACHE_DIR ?= data/hf_cache

.PHONY: download-musiccaps

download-musiccaps:
	$(PYTHON) src/scripts/download_audio_fragment.py --musiccaps \
		--split $(MUSICCAPS_SPLIT) \
		--offset $(MUSICCAPS_OFFSET) \
		--limit $(MUSICCAPS_LIMIT) \
		--duration $(MUSICCAPS_DURATION) \
		--start-shift $(MUSICCAPS_START_SHIFT) \
		--cache-dir $(MUSICCAPS_CACHE_DIR) \
		--output-dir $(MUSICCAPS_OUTPUT_DIR)

.PHONY: download-musiccaps-local
download-musiccaps-local:
	$(PYTHON) src/scripts/load_musiccaps_dataset.py \
		--split $(MUSICCAPS_SPLIT) \
		--cache-dir $(MUSICCAPS_CACHE_DIR)


.PHONY: download-musiccaps-csv-local
download-musiccaps-csv-local:
	$(PYTHON) src/scripts/load_musiccaps_dataset_csv.py

.PHONY: download-10-sec-audio
download-10-sec-audio:
	$(PYTHON) src/scripts/download_10_sec_audio.py

.PHONY: add-musiccaps-metadata
add-musiccaps-metadata:
	$(PYTHON)  src/scripts/add_musiccaps_metadata.py \
	--model qwen/qwen3.5-9b \
	--input-dir data/musiccaps_from_csv \
	--limit 4


.PHONY: build-audiocraft-manifests
build-audiocraft-manifests:
	$(PYTHON)  src/scripts/build_audiocraft_manifests.py


.PHONY: train-audiocraft
train-audiocraft:
	dora run solver=musicgen/musicgen_base_32khz \
		conditioner=text2music \
		datasource.train=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_train.jsonl.gz \
		datasource.valid=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_valid.jsonl.gz \
		datasource.evaluate=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_valid.jsonl.gz \
		datasource.generate=/Users/vlad/Documents/Web/hw4-dl-audio/data/manifests/musiccaps_valid.jsonl.gz \
		datasource.max_sample_rate=44100 \
		datasource.max_channels=2 \
		dataset.segment_duration=10 \
		dataset.batch_size=8 \
		dataset.num_workers=2 \
		dataset.train.num_samples=2000 \
		dataset.valid.num_samples=200 \
		optim.updates_per_epoch=100 \
		optim.epochs=2 \
		generate.every=0 \
		evaluate.every=0 \
		dataset.train.merge_text_p=0.6 \
		dataset.train.drop_desc_p=0.15 \
		dataset.train.drop_other_p=0.2


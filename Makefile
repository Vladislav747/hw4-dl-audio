PYTHON ?= python3

ifneq (,$(wildcard .env))
include .env
export HF_TOKEN
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
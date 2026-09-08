.PHONY: test
test:
	$(MAKE) -C lightly_studio test-ci
	$(MAKE) -C lightly_studio_embed test
	$(MAKE) -C lightly_studio_view test

.PHONY: lint
lint:
	$(MAKE) -C lightly_studio lint
	$(MAKE) -C lightly_studio_embed lint
	$(MAKE) -C lightly_studio_view lint

.PHONY: format
format:
	$(MAKE) -C lightly_studio format
	$(MAKE) -C lightly_studio_embed format
	$(MAKE) -C lightly_studio_view format

# The Python members are checked together, so that one command covers every Python package no
# matter how many siblings there are.
PYTHON_MEMBERS := lightly_studio lightly_studio_embed

.PHONY: static-checks
static-checks:
	for member in $(PYTHON_MEMBERS); do $(MAKE) -C $$member static-checks || exit 1; done

.PHONY: type-check
type-check:
	for member in $(PYTHON_MEMBERS); do $(MAKE) -C $$member type-check || exit 1; done

.PHONY: build
build:
	$(MAKE) -C lightly_studio build
	$(MAKE) -C lightly_studio_embed build

.PHONY: download-example-dataset
download-example-dataset:
ifeq ($(OS),Windows_NT)
	@powershell -Command "if (-not (Test-Path lightly_studio\datasets)) { New-Item -ItemType Directory -Path lightly_studio\datasets | Out-Null }"
	git clone --depth=1 https://github.com/lightly-ai/dataset_examples_studio.git tmp_dataset_repo
	@powershell -Command "Copy-Item -Path tmp_dataset_repo\* -Destination lightly_studio\datasets\ -Recurse -Force"
	@powershell -Command "Remove-Item -Path tmp_dataset_repo -Recurse -Force"
else
	mkdir -p lightly_studio/datasets
	git clone --depth=1 https://github.com/lightly-ai/dataset_examples_studio.git tmp_dataset_repo
	cp -r tmp_dataset_repo/* lightly_studio/datasets
	rm -rf tmp_dataset_repo
endif

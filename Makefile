.PHONY: test
test:
	$(MAKE) -C lightly_studio test-ci
	$(MAKE) -C lightly_studio_view test

.PHONY: lint
lint:
	$(MAKE) -C lightly_studio lint
	$(MAKE) -C lightly_studio_view lint

.PHONY: format
format:
	$(MAKE) -C lightly_studio format
	$(MAKE) -C lightly_studio_view format

.PHONY: build
build:
	$(MAKE) -C lightly_studio build

.PHONY: download-example-dataset
download-example-dataset:
	mkdir -p lightly_studio/datasets
	git clone --depth=1 https://github.com/lightly-ai/dataset_examples_studio.git lightly_studio/datasets

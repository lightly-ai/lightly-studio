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
	mkdir -p lightly_studio/datasets/coco-128
	git clone --depth=1 https://github.com/lightly-ai/dataset_examples_studio.git tmp_dataset_repo
	cp -r tmp_dataset_repo/coco_subset_128_images/* lightly_studio/datasets/coco-128/
	rm -rf tmp_dataset_repo
	
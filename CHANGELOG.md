# Changelog

All notable changes to Lightly**Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add “View Video” button in the frame details view to open video details for the selected frame.
- Added `Escape` shortcut support in the embedding plot to clear the current selection.
- Loading videos with annotations from youtube-vis format via `dataset.add_videos_from_youtube_vis`.
- Added Shift+click range selection in grid views.
- Display semantic segmentation within the GUI.
- Allow creating and editing semantic segmentation within the GUI.

### Changed

- Selection now resets when switching between grid views, while filters persist.

### Deprecated

### Removed

- Removed Python 3.8 support.
- Removed the redundant `Hide Embeddings` button from the toolbar when the embedding plot is open (the `✕` close control remains in the plot panel).

### Fixed

- Fixed right-click `Copy image` in grid and detail views to copy images from the GUI.
- Fixed annotation details mask editing to keep focus stable without annoying recentering after every edit and always select the shown annotation.
- Fixed embedding plot UI stability and improved legend/control layout for narrow windows.
- Fixed instance-segmentation brush/eraser edits occasionally being applied to the wrong sample after navigating between samples.
- Fixed sample-details navigation so keyboard and button navigation keep active tool behavior deterministic across samples.
- Fixed embedding plot selection UX so rectangle/lasso overlays disappear after selection while selected samples remain highlighted.
- Fixed embedding plot so old selections are cleared when you change other filters, keeping the grid and plot in sync.
- Fixed outdated `VideoDataset` import path in README and docs quickstart examples.
- Fixed caption creation UX in edit mode: clicking `+` now opens a focused input draft, captions are created only on explicit save/Enter, and spaces in the draft input are handled correctly.

### Security

## \[0.4.8\] - 2026-02-11

### Added

- Editing of segmentation masks and deletion of annotations in the details view.
- Customizable toolbar shortcuts.
- GUI (Video):
    - Visualize video embeddings in the embedding plot.
    - Auto Selection for videos.
    - Video can be played/paused by space bar.
- Python Interface:
    - Group samples can be loaded in Python UI.
    - Semantic segmentation annotations can be loaded in Python UI (e.g. with `add_samples_from_pascal_voc_segmentations`).
    - Annotation Python UI: add/delete an annotation (`Sample.add_annotation()`, `Sample.delete_annotation()`), create `CreateInstanceSegmentation` and `CreateSemanticSegmentation` using `from_binary_mask()` or `from_rle_mask()`


### Changed

- Embedding plot doesn't require a license key anymore.
- Improved segmentation mask drawing performance.
- Improved caption support for videos:
    - Preview video when hover-over in caption grid view,
    - Caption preview in video grid view.

### Fixed

- Fixed Brush and eraser tools for segmentation masks to draw smooth strokes and stop reliably on mouse release.
- Fixed tag removal bug in sample detail views.
- Fixed interrupted checkpoint download that yielded a corrupted file.

## \[0.4.7\] - 2026-01-19

### Added
- Added `VideoDataset` class.
- Added Captions support for videos.
- Allow creating tags from all samples matching the current filters when no samples are explicitly selected.
- Added notebook/Colab support and usage snippet to the docs.
- Added image similarity search via drag-and-drop, file upload, or clipboard paste.
- Added similarity score display for images and videos when using embedding-based search.
- Added `VideoSampleField` for querying video datasets. `VideoDataset.query()` now works.
- Added helper functions and a tutorial on running Python and the GUI in parallel.
- Added image sample loader from Lightly prediction format.
- Added image classification editing: users can now add, remove, and modify image classification.
- Added support for creating and editing instance segmentation via GUI.
- Users can read annotations via Python using the new `annotations` property on all sample classes: `ImageSample` and `VideoSample`.
- Added a toolbar for creating and editing annotations.
- Added video hover playback in the captions view.
- Enabled spacebar to play/pause video in the video details view.
- Updated video grid view to display the first caption when available.

### Changed

- Renamed `Dataset` to `Collection` in the internal code.
- Migrated `DatasetQuery.export()` to `Dataset.export()`.
- Reduced the package size by using `opencv-python-headless`.
- `AnnotationLabelTable` is now linked to a dataset.
- `lightly_studio.Dataset` class has been renamed to `lightly_studio.ImageDataset`.
- Renamed `SampleField` to `ImageSampleField`.
- Allow resizing and adjusting a bbox immediately after it is drawn instead of starting a new bbox.
- Improved erase mode by making masks more transparent while erasing to simplify mask corrections.

### Fixed
- Fixed a startup problem when IPv6 is not enabled.

## \[0.4.6\] - 2025-12-16

### Added

- Added metadata section to video and video frame details.
- Added tag support for videos and video frames in the GUI.
- Introduced navigation between video details.
- Enabled video and video frames filtering.
- Added text search for videos.
- Added plugins: This is the initial version for plugins. It supports the execution of operators.
- Added cloud storage support for video frames.
- Added export for image captions.
- Added semantic search by adding perception encoder core as embeddings model.
- Added `VideoSample` class.

### Changed

- Renamed `lightly_studio.core.sample.Sample` to `ImageSample`.

## \[0.4.5\] - 2025-12-02

### Added

- Added reading and updating of captions to the `Sample` class.
- Added export functionality for image datasets with captions to the python `Dataset` class interface.
- Added keyboard shortcut support for toggling annotation edit mode.
- Added sliders to adjust brightness and contrast for more accurate labeling.
- Added version info to the footer.

### Changed

- Improved the undo functionality. Works now in more views and one can undo the creation and deletion of annotations.
- Reduced the minimum size of bounding box creation from 10px side length to 4px.
- Print server errors to the console.
- Header actions (classifier, selection, export, settings) are grouped into a menu.

### Fixed

- Fixed an issue with wrongly displayed annotations grid view in the presence of classification annotation type.
- Fixed video sample type in examples in readme and docs.
- Fixed a problem with listing all items on scroll in samples and annotations grid views.
- Fixed an image size reading issue for some JPEG formats.

## \[0.4.4\] - 2025-11-26

### Added

- Added video support. A video dataset can be loaded from a local folder and inspected in the GUI.
- Added video annotation support to the GUI. Video annotations can be currently loaded and exported only manually.
- Renamed `Dataset.add_samples_from_path` to `Dataset.add_images_from_path`.
- Added class balancing with a uniform or the input distribution as target. These options can be set for the `AnnotationClassBalancingStrategy`.
- Added download_example_dataset utility function to simplify the quickstart experience by removing the need for git clone.
- Added `tag_depth` parameter to `Dataset.add_samples_from_path` to automatically create tags from subdirectory names.
- Added labeling support for captions: Add/delete/edit captions from the GUI
- Added similarity metadata calculation to `Dataset`.

### Changed

- Renamed the `distribution` field of `AnnotationClassBalancingStrategy` to `target_distribution`.
- Display multiple captions per image in the Captions view.

### Fixed

- Support pyav >= v14 by removing the deprecated `av.AVError` import.

## \[0.4.3\] - 2025-11-13

### Added

- Added class balancing with a uniform or the input distribution as target. These options can be set for the `AnnotationClassBalancingStrategy`.
- Added `annotation_balancing` convenience method to the `Selection` interface to simplify class balancing selections.

### Fixed

- Fixed installation issue with Python 3.13: Properly declare package compatibility in pyproject.toml.

## \[0.4.2\] - 2025-11-11

### Added

- Added new selection strategy: `AnnotationClassBalancingStrategy`.
- Support for Python 3.13.
- Display captions within Sample Details.
- Added more detailed setup instructions to CONTRIBUTION.md
- Added a detailed section about cloud support to the docs.

### Changed

- Changed the grid slider to define how many items will appear per row.
- Auto-scroll to the selected annotation in the sample details side panel.

### Fixed

- Fixed issue when embedding plot wasn't updating after changing filters.
- Prevent duplicated annotation labels: Fixed an issue that occurred when adding samples from yolo using multiple splits.
- Added `requests` as an explicit dependency to prevent potential errors during embedding model download.
- Embedding generation RAM usage fixed by using `np.ndarray`.

## \[0.4.1\] - 2025-10-27

### Added

- Added a footer with useful links and information about filtered and total annotations or samples.
- Improved class docstrings for the most important user-facing classes.
- Added `Annotation` tags section within the Annotation Details.
- Added undoable action for editing annotations on the sample details.
- Allowed users to remove `Annotation` tags from the Annotation Details.

### Changed
- Updated button text to "View sample" in annotation details panel for better clarity.
- Pressing Escape while adding an annotation now cancels add-annotation mode.
- Improved the navbar to display button titles on hover and removed button text on small screens.
- Samples are now ordered by their filenames in the GUI.
- Introduce button to reset viewport changes for embedding plot.
- Improve UX for label picker when adding labels.

### Removed

- Branding link from the `Embedding View`s status bar

## \[0.4.0\] - 2025-10-21

### Added
- Public LightlyStudio release

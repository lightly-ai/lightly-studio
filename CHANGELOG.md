# Changelog

All notable changes to Lightly**Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Python SDK: Allow embedding video frames by adding the `embed_frames` parameter to `VideoDataset.add_videos_from_path` and `VideoDataset.add_videos_from_youtube_vis`.

### Changed

- The left filter panel can now be collapsed entirely to reclaim space for the grid; a "Filters" button in the grid header restores it.

### Deprecated

### Removed

### Fixed

### Security

## \[1.0.3\] - 2026-07-10

### Added

- Python SDK: `limit` parameter on `ImageDataset.add_samples_from*` methods to index only the first N samples of a dataset.
- Python dataset queries now support model evaluation queries on the annotation level.
- View class distribution for image classification.
- Custom embedding models can be registered.

### Changed

- Embedding plot legend is now compact and scrollable, and the WebGPU fallback message is no longer shown.

## \[1.0.2\] - 2026-07-02

### Added

- Annotation classes can now be shown or hidden individually in the grid views using an eye icon toggle in the Annotation Classes sidebar.
- Python SDK: `target_fps` parameter on `VideoDataset.add_videos_from_path` to subsample frames to a
  lower frame rate. Retained frames keep their original frame numbers.
- Sampling in Browser now supports combining multiple strategies (diversity, typicality, similarity, metadata weighting, class balancing) in a single selection.
- Sampling dialog now accepts a percentage input alongside the absolute sample count. Editing either field updates the other based on the current    
filtered sample count.
- Deduplication strategy is available in the Sampling Dialog in the GUI
- Improve confusion matrix usability for large numbers of classes
- Python dataset queries now support classifications, object detections, and segmentation mask annotations.
- Python dataset queries now model evaluation queries on the sample level.
- Improved performance when tagging all samples in the GUI for large datasets.
- Annotation source selection for exports: when multiple annotation collections exist, the export dialog shows a dropdown to choose which collection to export from. The annotation source can also be specified via the Python API using the `annotation_collection_id` parameter.
- All embedding plot legend entries (especially e.g. `Excluded by filters`, `No category`, etc.) can be hidden by clicking on them.
- YOLO object detection export: object detection annotations can now be exported in YOLO format from the GUI export dialog, via the Python API (`dataset.export().to_yolo_object_detections(...)`), and via the export API (`export_format=object_detection_yolo`).
- Object-level (annotation) embeddings: annotations can now be embedded and searched by text or image similarity and visualized in the embedding plot.

## \[1.0.1\] - 2026-06-17

### Added

- Show plugin description and a link to documentation when no plugins are available.
- When sorting the image grid by a numeric field, the field value is now shown as an overlay on each sample.
- Query editor now supports annotation `source` and `confidence` fields in queries.
- Panel toggles (Embeddings, Query, Evaluation) moved to a right-rail icon menu beside the collection grid.
- Python SDK: `annotation_source` parameter on `ImageDataset.add_samples_from*` methods and
  `Sample.add_annotation` / `add_annotations` to import or add annotations to a named source.
- Python SDK: `Annotation.annotation_source` property to read the annotation source name.
- Python SDK: `Sampling.deduplicate` method to select a deduplicated subset based on embedding distance.

### Changed

- The embedding plot legend now reflects the active filter: categories with no
  matching samples are hidden. When there are more values than fit in the
  legend, the least frequent values are merged into a single "Other" category.

### Fixed

- Fixed embedding rendering for users without WebGPU by updating `embedding-atlas` from `0.10.0` to `0.21.0`.
- The query filter is now applied consistently across features that use the image filter, such as the embedding plot, sampling, and select-all.
- Brush tool's `Finish` button gives better visual feedback when an annotation can be finished.

## \[1.0.0\] - 2026-06-05

### Added

- Show confusion matrix in evaluation results for classification.
- Enable picker for annotation source menu
- Embedding plot: added a "No coloring" option to the "Color by" dropdown to disable coloring.
- Show ground truth and prediction annotation sources in run details panel
- Image details view: annotations are now grouped by annotation source.
- Image details view: annotation source visibility can be toggled.
- Image details view: pick the target annotation source for new annotations from an on-canvas selector.

### Changed

- Header menu: show collection name in Annotations entries
- Embedding plot coloring now supports multiple categories per sample, resolving issues with toggling visibility of categories in the legend.
- Made annotation and plot colors more distinguishable.
- General UI improvements.

### Fixed

- Embedding plot: when a coloring has more categories than the legend can display, the extra
  categories are now grouped into an "Other" entry instead of exceeding the available legend slots.
- Grid top bar no longer overflows its container or covers the grid when a side panel is open;
  it now shrinks with the available width and wraps onto a second line when too narrow.
- Fixed operations on large datasets (more than ~65,535 samples) failing on PostgreSQL with
  `number of parameters must be between 0 and 65535`.
- Fixed cascaded delete for annotations linked by calculated metrics.
- Grid annotation source selection now persists when navigating to image details and back.

## \[1.0.0rc1\] - 2026-05-28

### Added

- Sample selection respects the current image or video filters.
- Added sort-by support via GUI.
- Added similarity selection option.
- Show confusion matrix in evaluation results for object detection.
- Added option to select annotation source for class balancing.
- Added query editor for advanced filtering with custom queries.
- Added Model Evaluation:
    - Users can manage annotations from different sources, e.g. ground truth and predictions.
    - Users can evaluate per sample metrics for object detection, classification and semantic segmentation
    - Users can sort the image grid by the sample metrics: finding errors quickly.
    - Users can display confusion matrix to find error patterns.

### Changed

- Renamed the annotation class field `label` to `class_name` across the Python SDK and query language. Breaking change.
- Renamed the `collection_name` and `name` arguments to `annotation_source`. Breaking change.
- Renamed selection to sampling. Breaking change.

### Fixed

- Fixed hovering over breadcrumb links on detail pages (annotations, video frames) triggering unwanted navigation.

## \[0.4.14\] - 2026-05-18

### Added

- Added `ImageDataset.add_annotations_from_coco`, `add_annotations_from_yolo`, and `add_annotations_from_labelformat` methods to attach annotations to images already in the dataset. Re-using the same `annotation_source` appends; a new `annotation_source` creates a new annotation source. Enables ingesting ground truth and predictions from multiple sources side-by-side.
- Added `lt_train_script` to the Python API (`lightly_studio.lt_train_script`) to generate a LightlyTrain object detection script from split tags. The helper exports train/val COCO annotation files via `dataset.export(...).to_coco_object_detections(...)` and writes `train_object_detection.py` with the exported paths.
- Image samples can be sorted in the grid using image attributes and metadata.
- Added drag-and-drop from the image grid into the image search area.
- Added a select-all button to select all grid items matching the active filters.
- Added `Cmd+A` / `Ctrl+A` keyboard shortcut to select all samples matching the current filters in grid views (images, videos, video frames, annotations).
- Added API endpoints to fetch only sample IDs with optional filters for images, video frames, and annotations (used by the select-all keyboard shortcut).


### Changed

- Refactored annotation mask rendering to use a shared web worker pool instead of spawning one worker per canvas.
- Few-shot classifier predictions now land in an annotation collection named after the classifier instead of the generic `annotation` collection, so multi-prediction views can distinguish classifiers. Rerunning a classifier reuses the same collection.
- Removed the license key requirement for sampling.


## \[0.4.13\] - 2026-04-21

### Added

- Added a floating selection panel to grid pages.
- Tags can be created and assigned directly from the sample and annotation detail view.
- Tags can be created and assigned directly from the side panel in the grid view.
- Tags can be renamed directly from the side panel in the grid view.
- Tags can be deleted from the side panel in the grid view.
- Show Embedding Plot selection as a filter item in the left panel.
- Added thumbnail quality setting in the Settings dialog. Enable "High Quality Thumbnails" to load compressed JPEG thumbnails in grid views, reducing bandwidth for large datasets.
- Added `Dataset.update_metadata` method to update metadata of multiple samples at once.
- Exposed Pascal VOC segmentation export from the Python interface.
- Added cloud storage support for Pascal VOC semantic segmentation annotations.

### Changed

 - Embedding plot shows only 2 categories `Filtered` and `Not Filtered`.

### Fixed

- Fixed annotation editing UX in sample details by showing a Saving indicator while changes are persisted.


## \[0.4.12\] - 2026-04-01

### Added

- Added tooltips to features in annotation items in the right panel to improve usability.
- Added keyboard navigation (Space + W/A/S/D) for moving within the zoomable image container.
- Added instance segmentation export to COCO in the GUI.
- Added semantic segmentation export to PASCAL VOC in the GUI.
- Added instance segmentation export to YouTube-VIS in the GUI.
- Added scopes to operators: now operators are tied to certain scopes and also retrieve filters. This enables to execute operators on specific collections, with specific filters, or even on individual samples.
- Added `ImageSample.add_annotations` method, as well as `VideoSample.add_annotations`.
- Added `ImageSample.add_captions` method, as well as `VideoSample.add_captions`.
- Added `SampleMetadata.update` method, allowing batch metadata updates of samples.
- Added support for Python 3.14.
- Added `lightly-studio` command line command. Use `lightly-studio gui` to start the GUI.

### Changed

- Smarter font loading reduces initial download from 500kB to 150kB
- Reduced grid page size to 32 items to improve grid view performance.
- Added DatasetTable to the database model, databases from previous versions are incompatible with this one.
- Improved the documentation structure.

### Fixed

- Speedup frontend by eliminating two redundant initial video list requests.
- Fixed semantic text search in image and video grids so editing an active query no longer resets or clears the search unexpectedly.
- Fixed tag creation dialog layout so long tag lists stay scrollable instead of expanding the modal.
- Improved video details playback so annotation overlays update more smoothly under higher browser latency.
- Fixed video details playback stopping one frame before the end.

## \[0.4.11\] - 2026-03-10

### Added

- Added option to customize the semantic segmentation keyboard shortcut in the settings dialog.
- Operators lifecycle management: operators now have `startup` and `shutdown` methods, which be default pass. The new methods can be used for example to start and stop inference server.

### Changed

- Improved semantic segmentation loading performance in the GUI.

### Fixed

- Navigation menu immediately updates to display the Captions page when the first caption is added.

## \[0.4.10\] - 2026-03-09

### Added

- `Dataset.export()` now supports instance segmentation export to COCO using `to_coco_instance_segmentations()`.
- Added keyboard shortcuts: to switch between the brush and eraser; to adjust the brush size.

### Changed

- Replaced grid size slider icons with clickable `+` / `−` buttons for zooming in and out.
- Restructured the navigation menu to follow the dataset structure. This makes the menu work with group datasets.
- Disable annotation class text rendering in the detail view by default (can be changed in settings).

### Fixed

- Fixed crosshair helper lines in annotation draw mode so vertical and horizontal lines remain the same thickness when zooming.
- Settings dialog is now scrollable on small screens.
- Added `✕` button to clear an active text search, matching the existing image search behavior.
- Fixed "Annotation updated successfully" toast appearing when clicking a bounding box without moving or resizing it.
- Improved deletion UX in sample details and captions list views: replaced confirmation popups with immediate deletion and Ctrl+Z undo support.
- Fixed grid not scrolling to the top when text search results are returned from cache.
- Fixed performance issues where annotations lagged behind the video.
- Fixed concurrency issue on video datasets.

## \[0.4.9\] - 2026-02-27

### Added

- Semantic segmentation labeling support:
    - Load semantic segmentation from Pascal VOC format
    - Visualize and label semantic segmentation in the GUI
- Object tracking support:
    - Loading videos with object track annotations from youtube-vis format via `dataset.add_videos_from_youtube_vis`.
    - Visualize object track-IDs in the GUI (available for object detection and instance segmentation).
- Hotkeys: 
    - Added `Escape` shortcut support in the embedding plot to clear the current selection.
    - Added Shift+click range selection in grid views.
- Added cloud storage support for COCO object detection and instance segmentation annotations.
- Add “View Video” button in the frame details view to open video details for the selected frame.
- Example script for LightlyTrain training and inference plugins.

### Changed

- Selection now resets when switching between grid views, while filters persist.
- Embedding model weights are now saved to the user cache by default. The cache dir can be changed via `LIGHTLY_STUDIO_MODEL_CACHE_DIR`.

### Removed

- Removed Python 3.8 support.
- Removed the redundant `Hide Embeddings` button from the toolbar when the embedding plot is open (the `✕` close control remains in the plot panel).
- Removed unused `MetadataFilters` component in favor of `CombinedMetadataDimensionsFilters`.

### Fixed

- Fixed right-click `Copy image` in grid and detail views to copy images from the GUI.
- Improved image sample listing performance (up to 3x faster) by optimizing ORM loading.
- Fixed annotation details mask editing to keep focus stable.
- Fixed embedding plot UI stability and improved legend/control layout for narrow windows.
- Fixed instance-segmentation brush/eraser edits occasionally being applied to the wrong sample after navigating between samples.
- Fixed sample-details navigation so keyboard and button navigation keep active tool behavior deterministic across samples.
- Fixed embedding plot selection UX so rectangle/lasso overlays disappear after selection while selected samples remain highlighted.
- Fixed embedding plot so old selections are cleared when you change other filters, keeping the grid and plot in sync.
- Fixed outdated `VideoDataset` import path in README and docs quickstart examples.
- Fixed caption creation UX in edit mode: clicking `+` now opens a focused input draft, captions are created only on explicit save/Enter, and spaces in the draft input are handled correctly.
- Fixed metadata float filter sliders to avoid max-value truncation and reduced UI slowdowns for large numeric ranges by capping slider tick density.
- Fixed auto-refresh side panel after annotation changes.
- Fixed video frame slider not updating current frame when dragging.

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

# Changelog

All notable changes to Lightly**Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Auto-scroll to the selected annotation in the sample details side panel when selecting an annotation on a sample.

### Changed

- Database changes to support multimodal samples.

### Deprecated

### Removed

### Fixed

- Preventing adding of duplicated annotation labels: Fixed an issue that occurred when adding samples from yolo using multiple splits. 

### Security

## \[0.4.1\] - 2025-10-27

### Added

- Added a footer with useful links and information about filtered and total annotations or samples.
- Improved class docstrings for the most important user-facing classes.
- Added `Annotation` tags section within the Annotation Details.
- Added undoable action for editing annotations on the sample details.
- Allowed users to remove `Annotation` tags from the Annotation Details.
- Added `AnnotationClassBalancingStrategy` class, usable in selection.
- Display captions within Sample Details.

### Changed
- Updated button text to "View sample" in annotation details panel for better clarity.
- Pressing Escape while adding an annotation now cancels add-annotation mode.
- Improved the navbar to display button titles on hover and removed button text on small screens.
- Samples are now ordered by their filenames in the GUI.
- Introduce button to reset viewport changes for embedding plot.
- Improve UX for label picker when adding labels.
- Changed the grid slider to define how many items will appear per row.
- Updated the panel slider style.
- Fixed issue when embedding plot wasn't updating after changing filters.

### Removed

- Branding link from the `Embedding View`s status bar

## \[0.4.0\] - 2025-10-21

### Added
- Public LightlyStudio release

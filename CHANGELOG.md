# Changelog

All notable changes to Lightly**Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added class balancing with a uniform or the input distribution as target. These options can be set for the `AnnotationClassBalancingStrategy`.
- Added download_example_dataset utility function to simplify the quickstart experience by removing the need for git clone.

### Changed
- Renamed the `distribution` field of `AnnotationClassBalancingStrategy` to `target_distribution`.

### Deprecated

### Removed

### Fixed

### Security

## \[0.4.3\] - 2025-11-13

### Added

- Added class balancing with a uniform or the input distribution as target. These options can be set for the `AnnotationClassBalancingStrategy`.

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

# Changelog

All notable changes to Lightly**Studio** Serve will be documented in this file. The package
releases on its own cadence, so it keeps its own changelog; the root `CHANGELOG.md` is
LightlyStudio's.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add `serve`, which runs an embedder over HTTP or HTTPS with an optional bearer token and a
  ceiling on the request body size.
- Add the conformance kit, `python -m lightly_studio_serve.conformance <url>`. It checks any
  server that claims to speak the protocol, reports one outcome per capability, and needs no
  dataset.

### Changed

### Deprecated

### Removed

### Fixed

### Security

## \[0.1.0\] - 2026-09-11

### Added

- Add the embedder base classes and the embedding types LightlyStudio uses to talk to your
  model. The HTTP server is not implemented yet, so this release cannot serve a model.


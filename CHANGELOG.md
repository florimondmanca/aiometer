# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 0.3.0 - 2021-07-06

### Changed

- Update `anyio` dependency to v3 (previously v1). (Pull #25)
  - _NB: no API change, but dependency mismatches may occur. Be sure to port your codebase to anyio v3 before upgrading `aiometer`._

### Added

- Add support for Python 3.6 (installs the `contextlib2` backport library there). (Pull #26)
- Officialize support for Python 3.9. (Pull #26)

## 0.2.1 - 2020-03-26

### Fixed

- Improve robustness of the `max_per_second` implementation by using the generic cell rate algorithm (GCRA) instead of leaky bucket. (Pull #5)

## 0.2.0 - 2020-03-22

### Added

- Add support for Python 3.7. (Pull #3)

## 0.1.0 - 2020-03-21

### Added

- Add `run_on_each()`, `run_all()`, `amap()` and `run_any()`, with `max_at_once` and `max_per_second` options. (Pull #1)

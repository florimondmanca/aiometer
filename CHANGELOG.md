# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 1.0.0 - 2025-04-04

_This release contains no code changes._

### Changed

- Package is now marked as Production/Stable. (Pull #49)

### Added

- Test on Python 3.13. (Pull #49)

## 0.5.0 - 2023-12-11

### Removed

- Drop support for Python 3.7, as it has reached EOL. (Pull #44)

### Added

- Add official support for Python 3.12. (Pull #44)
- Add support for anyio 4. This allows catching exception groups using the native ExceptionGroup. On anyio 3.2+, anyio would throw its own ExceptionGroup type. Compatibility with anyio 3.2+ is retained. (Pull #43)

## 0.4.0 - 2023-01-18

### Removed

- Drop support for Python 3.6, which has reached EOL. (Pull #38)

### Added

- Add official support for Python 3.10 and 3.11. (Pull #38)

### Fixed

- Relax version requirements for `typing_extensions` and address `mypy>=0.981` strict optional changes. (Pull #38)

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

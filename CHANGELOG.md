# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [dev]
### Added
### Changed
### Removed

## [1.0.0] - 2021-04-26
### Changed
- Changed message format to ASN(x) single message format that allows to transmit all sensor data in one message augmented with self-diagnostic data.
- Transmit 16-bit integer and float as 16-bit fixed-point values.

## [0.3.1] - 2020-08-31
### Changed
- Changed message format (structure) to transmit all sensor values as float.

## [0.3.0] - 2020-08-31
### Changed
- Changed message format (structure) to allow the transmission of either float, uint or sint values depending on the type.

## [0.2.0] - 2020-08-24
### Changed
- Reduced message overhead for shorted messages

## [0.1.1] - 2020-08-05
### Added
- Added logging functionality for debug and documentation purposes

## [0.1.0] - 2020-08-04
### Added
- Initial cluster head application able to receive messages and stores the information in a remote database

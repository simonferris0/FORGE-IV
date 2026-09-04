# FORGE-IV

## Overview

FORGE-IV is a software project for controlling and monitoring a Tactical Microgrid System (TMS).

The repository contains multiple Python implementations of a microgrid controller, supporting test scripts, an RTI Connext DDS Connector XML configuration, and text files containing collected generator/power data.

The project is structured as an iterative development repository: several controller implementations are present, including Type V interface, feeder-driven, single-feeder, patched, and test versions.

## What the Repository Contains

At a high level, the project contains:

- Python-based TMS controller implementations.
- DDS readers and writers for communicating with the TMS.
- Device discovery and state tracking.
- Generator/source management.
- Feeder and power-port control logic.
- Diagnostic and heartbeat monitoring.
- Electrical measurement handling.
- Test/development scripts.
- A DDS XML configuration.
- Collected generator, fuel, and power-delivery data.

## Repository Structure

The project contains the following major components:

```text
Capstone/
├── tms/
│   ├── controller.py
│   ├── controller-test.py
│   ├── controller_typev_feeder_driven.py
│   ├── controller_typev_interface_patched.py
│   ├── controller_typev_single_feeder_patched.py
│   ├── test_script.py
│   ├── tms_reader.py
│   ├── Generator_Information_24_Hours.txt
│   ├── Generator_fuel_ups.txt
│   └── Total_Real_Delivered_Combined.txt
│
└── xml/
    └── tmg_xml_24_mar.xml

Additional controller versions are located at the repository's top level.
```

Because this repository contains multiple iterations of the controller, the filenames should be treated as development versions rather than assuming that every file represents the current production implementation.

---

## Technology

### Python

The controller implementations are written in Python.

### RTI Connext DDS Connector

The Python controller files import:

```python
import rticonnextdds_connector as rti
```

and use the Connector API to create DDS connections, readers, and writers.

Therefore, the project depends on the **RTI Connext DDS Connector for Python**.

The repository also includes the XML configuration used by the DDS Connector.

> This README intentionally does not specify an RTI Connext version because the repository itself does not provide enough evidence to establish a required version.

---

## DDS Configuration

The repository contains:

```text
Capstone/xml/tmg_xml_24_mar.xml
```

The controller implementations reference a TMS DDS participant/configuration through the Connector API.

Where a controller specifies the participant name, the repository uses:

```text
TmsParticipantLibrary::TmsParticipant
```

The exact DDS domain, transport, and other runtime settings should be taken from the XML configuration and the environment in which the TMS is being operated.

---

## TMS Communication

The controller code communicates with TMS devices through DDS topics/readers/writers.

Topics referenced by the controller implementations include:

### Monitoring / State

- `Heartbeat`
- `DeviceInfo`
- `ActiveDiagnosticState`
- `EnergyStartStopState`
- `ControlParameterState`
- `GroundingCircuitState`
- `PowerPortState`
- `AcMeasurementUpdate`
- `Reply`
- `MetricParameterState`

### Controller Requests / Commands

- `EnergyStartStopRequest`
- `PowerSwitchRequest`

The exact set of topics used varies between controller implementations.

---

## Controller Functionality

The controller implementations contain functionality for monitoring and controlling the microgrid.

### Device Discovery

The controller processes device information and maintains information about discovered devices.

The code distinguishes between different device roles, including sources/generators, feeders/distribution devices, loads, storage, and controllers.

### Heartbeat Monitoring

Heartbeat messages are used to monitor whether devices are communicating with the controller.

The controller implementations maintain timestamps/state associated with received heartbeat information.

### Electrical Measurements

The controllers process AC measurement updates and use electrical measurements as part of system monitoring and decision-making.

### Diagnostics

The controller reads diagnostic information and uses diagnostic state when determining the condition of the system.

### Generator Management

The controller code contains logic for identifying and managing generation sources.

This includes sending energy start/stop requests and monitoring generator state.

### Feeder / Power-Port Management

The Type V controller implementations contain logic for determining and changing power-port states.

Depending on the implementation, the controller can issue power-switch requests and monitor the resulting state/reply.

### Command Confirmation and Retry

Several implementations contain logic for tracking requests, waiting for replies, and retrying or timing out commands.

---

## Type V Controller Implementations

Several files specifically implement or modify a Type V controller.

### `controller_typev_interface.py`

A Type V controller interface implementation.

### `controller_typev_interface_patched.py`

A patched Type V interface implementation containing source, load, and feeder state models along with DDS communication and controller logic.

### `controller_typev_interface_patched_v2.py`

A later patched version of the Type V interface.

### `controller_typev_interface_phase_display.py`

A Type V interface variant containing additional phase-related display/monitoring behavior.

### `controller_typev_feeder_driven.py`

A Type V implementation organized around feeder state and feeder-driven control behavior.

### `controller_typev_single_feeder_patched.py`

A Type V implementation containing single-feeder-oriented control logic.

Because several versions coexist, the project should identify one controller as the authoritative version before deployment or submission.

---

## Supporting Tools

### `tms_reader.py`

A DDS/TMS reader utility used to receive and display TMS messages for inspection and debugging.

### `test_script.py`

A small development/test script used by the project.

The repository does not contain a conventional automated test framework such as a `pytest` test suite.

---

## Data Files

The `Capstone/tms/` directory contains several text data files:

### `Generator_Information_24_Hours.txt`

Contains recorded generator information.

### `Generator_fuel_ups.txt`

Contains recorded generator fuel-related information.

### `Total_Real_Delivered_Combined.txt`

Contains recorded real-power delivery data.

These files appear to be project-generated data used for analysis/testing rather than application configuration.

---

## Installation / Environment

The repository does not include a `requirements.txt`, `pyproject.toml`, or equivalent dependency lock/configuration file.

The Python code explicitly requires:

```python
rticonnextdds_connector
```

Therefore, a machine running the controller needs an appropriate RTI Connext DDS Connector for Python installation and a Python environment capable of importing that module.

The DDS XML configuration also needs to be available at the location expected by the selected controller.

### Before Running

Verify:

1. Python is installed.
2. `rticonnextdds_connector` can be imported.
3. The DDS XML configuration is present.
4. The selected controller is using the correct XML path.
5. The required TMS/DDS environment is running.
6. The DDS participant/configuration matches the environment being used for testing.

---

## Running the Software

The exact command depends on which controller implementation is being tested.

For example, from the `Capstone/tms/` directory:

```bash
python controller_typev_feeder_driven.py
```

or:

```bash
python controller_typev_single_feeder_patched.py
```

or:

```bash
python controller_typev_interface_patched.py
```

The feeder-driven controller also contains command-line handling for an XML configuration path and DDS participant selection.

Because the repository contains multiple controller variants, **select the intended controller before running the project**.

---

## Controller Workflow

The controller implementations generally follow a repeated monitoring/control cycle:

```text
        ┌─────────────────────┐
        │ Connect to DDS/TMS  │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Receive TMS State   │
        │ & Device Messages   │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Update Internal     │
        │ Device State        │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Evaluate Diagnostics│
        │ & Electrical State  │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Determine Required  │
        │ Control Action      │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Publish DDS Request │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Process Reply /     │
        │ Updated Device State│
        └─────────────────────┘
```

The precise sequence and decision logic varies between controller versions.

---

## Development History

The repository contains several versions of controller code, including:

```text
controller.py
controller-test.py
controller-test-patched (1).py
controller-test-patched-v2.py
controller_typev_interface.py
controller_typev_interface_patched.py
controller_typev_interface_patched_v2.py
controller_typev_interface_phase_display.py
```

This naming indicates an iterative development process in which the controller was repeatedly modified and patched.

For maintainability, the project would benefit from designating a single current implementation and moving obsolete versions into a clearly labeled archive/history directory.

---

## Testing

The repository contains test/development scripts, but it does not currently provide a conventional automated test suite.

Testing should be performed against the appropriate TMS/DDS test environment.

Recommended test cases include:

- DDS connection and initialization.
- Device discovery.
- Heartbeat reception.
- Generator/source discovery.
- Generator start/stop requests.
- Feeder state detection.
- Power-port commands.
- Reply/command confirmation.
- Command timeout/retry behavior.
- Diagnostic/fault handling.
- Electrical measurement reception.
- Communication-loss behavior.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'rticonnextdds_connector'`

The required RTI Connector Python module is not available to the Python interpreter.

Verify the RTI Connext DDS installation and Python environment.

### DDS connection problems

Check:

- The XML configuration path.
- The participant name.
- DDS environment/domain settings.
- Whether the TMS/DDS publisher is running.
- Whether the controller and TMS are communicating over the expected network.

### No devices appear

Verify that the TMS is publishing the expected `DeviceInfo` and `Heartbeat` messages and that the controller is connected to the same DDS environment.

### Commands do not complete

Inspect the controller's reply handling and verify that the corresponding TMS device is publishing the expected `Reply`/state information.

---

## Safety

The controller code contains functionality for sending generator and power-switch requests.

**Do not connect experimental software to physical energized equipment without appropriate authorization, engineering review, testing, and safety procedures.**

Use a simulator or controlled test environment whenever possible during software development.

---

## Current Limitations

Based directly on the repository contents:

- Multiple controller implementations coexist.
- No dependency manifest such as `requirements.txt` is included.
- No conventional automated test suite is included.
- Configuration is partly dependent on the DDS XML environment.
- Some scripts are clearly development/test variants.
- The repository does not clearly identify a single authoritative controller implementation.
- Some behavior depends on messages supplied by the external TMS/DDS environment.

---

## Recommended Improvements

For future development, the repository could be improved by:

1. Designating one controller as the official/current implementation.
2. Moving obsolete controller versions into an archive directory.
3. Adding `requirements.txt` or `pyproject.toml`.
4. Adding automated unit tests.
5. Adding integration tests against a TMS simulator.
6. Separating DDS communication from controller decision logic.
7. Centralizing configuration.
8. Adding formal documentation for the DDS topics and data structures.
9. Adding architecture and state-machine diagrams.
10. Adding structured logging.
11. Documenting the exact software/environment versions required to run the controller.

---

## Project Context

**Course:** XE401 – Integrative System Design I  
**Institution:** United States Military Academy  
**Project:** FORGE-IV  
**Team Repository:** AY27 Team Repository 6

This repository represents an iterative software/system-development effort involving microgrid monitoring and control, distributed communication, and integration with a Tactical Microgrid System.

---

## Contributors

Add project contributors here:

```text
- Name — Role / Responsibility
- Name — Role / Responsibility
- Name — Role / Responsibility
```

---

## License

No explicit open-source license was identified in the repository.

Unless the project owners add a license, the code should not be assumed to be freely reusable or redistributable.

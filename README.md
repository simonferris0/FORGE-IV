# FORGE-IV

## Overview

FORGE-IV is a microgrid control-system project developed for the U.S. Military Academy's XE401 Integrative System Design I course. The repository contains Python-based controller implementations and supporting tools for communicating with and controlling a Tactical Microgrid System (TMS) through RTI Connext DDS.

The project focuses on implementing and refining a **Type V microgrid controller interface** capable of discovering connected devices, monitoring microgrid state, managing generation, diagnosing feeder conditions, and issuing power-switch and generator-control requests.

> **Note:** This repository contains multiple iterations of the controller. Some files are experimental, legacy, patched, or test versions. The `Capstone/tms/` directory contains the more recent Type V controller implementations and associated TMS tooling.

---

## Project Goals

The primary goals of FORGE-IV are to:

- Interface with a Tactical Microgrid System using RTI Connext DDS.
- Discover generators, feeders, loads, and other microgrid devices.
- Monitor device heartbeats and electrical measurements.
- Detect feeder faults and communication failures.
- Start and manage available generation sources.
- Open or close feeder power ports based on system conditions.
- Publish controller identity, heartbeat, and diagnostic information.
- Provide tools for inspecting and analyzing TMS DDS messages.
- Record selected electrical measurements for later analysis.

---

## Repository Structure

```text
FORGE-IV-main/
├── Capstone/
│   ├── tms/
│   │   ├── controller.py
│   │   ├── controller-test.py
│   │   ├── controller_typev_feeder_driven.py
│   │   ├── controller_typev_interface_patched.py
│   │   ├── controller_typev_single_feeder_patched.py
│   │   ├── test_script.py
│   │   ├── tms_reader.py
│   │   ├── Generator_Information_24_Hours.txt
│   │   ├── Generator_fuel_ups.txt
│   │   └── Total_Real_Delivered_Combined.txt
│   │
│   └── xml/
│       └── tmg_xml_24_mar.xml
│
├── controller.py
├── controller-test.py
├── controller-test-patched (1).py
├── controller-test-patched-v2.py
├── controller_typev_interface.py
├── controller_typev_interface_patched.py
├── controller_typev_interface_patched_v2.py
└── controller_typev_interface_phase_display.py
```

### `Capstone/tms/`

This directory contains the primary TMS-oriented implementations.

#### `controller.py`

Earlier controller implementation containing models for:

- Sources/generators
- Loads
- Feeders
- Controller state

It uses RTI Connext DDS readers and writers to communicate with the TMS and includes generator-control and microgrid-management logic.

#### `controller-test.py`

A test/development version of the original controller. It contains similar functionality while being used to experiment with controller behavior and data collection.

#### `controller_typev_feeder_driven.py`

A Type V controller implementation centered around feeder state.

Major capabilities include:

- Device discovery
- Heartbeat monitoring
- Source/generator discovery
- Feeder discovery
- AC measurement processing
- Grounding-circuit monitoring
- Power-port state monitoring
- Reply/command confirmation
- Fault and advisory generation
- Automatic feeder open/close decisions
- Generator startup
- Command retry and timeout handling

The script supports command-line configuration of the XML file and DDS participant.

#### `controller_typev_single_feeder_patched.py`

A Type V controller implementation designed around a single primary feeder.

It includes:

- Feeder discovery
- Source discovery
- Heartbeat monitoring
- Electrical measurement monitoring
- Fault diagnosis
- Power-port state determination
- Generator startup
- Feeder open/close decisions
- Command confirmation and retry behavior

#### `controller_typev_interface_patched.py`

A Type V controller interface that maintains explicit state models for sources, loads, and feeders.

The controller periodically:

1. Publishes its heartbeat.
2. Reads TMS DDS topics.
3. Diagnoses the microgrid.
4. Manages generation.
5. Manages the feeder.
6. Publishes controller diagnostics.
7. Prints a status summary.

#### `controller_typev_interface_phase_display.py`

A variation of the Type V interface that includes additional phase-oriented electrical state and display/diagnostic behavior.

#### `tms_reader.py`

A TMS message inspection utility. It connects to the DDS participant and reads TMS topics, printing received dictionaries for debugging and system analysis.

#### `test_script.py`

A simple file-writing test script used during development.

---

## DDS Communication

The controller communicates with the TMS using **RTI Connext DDS Connector for Python**.

The XML configuration defines the DDS participant, data types, topics, readers, and writers required by the TMS environment.

The included configuration is:

```text
Capstone/xml/tmg_xml_24_mar.xml
```

The controller implementations use the participant:

```text
TmsParticipantLibrary::TmsParticipant
```

### Topics Used

Depending on the controller implementation, the software subscribes to topics including:

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

The controller publishes topics including:

- `Heartbeat`
- `DeviceInfo`
- `ActiveDiagnosticState`
- `EnergyStartStopRequest`
- `PowerSwitchRequest`

The XML configuration contains the broader TMS topic model, including additional topics not necessarily used by every controller implementation.

---

## Requirements

### Software

- Python 3
- RTI Connext DDS
- RTI Connext DDS Connector for Python
- Access to the appropriate TMS/DDS environment
- The included XML DDS configuration

Most of the Python code uses only the standard library in addition to:

```text
rticonnextdds_connector
```

No `requirements.txt` is currently included in the repository.

### RTI Connext DDS

The Python controllers import:

```python
import rticonnextdds_connector as rti
```

The RTI Connext DDS Python Connector must therefore be installed and configured on the system running the controller.

The XML configuration included in this repository was authored for an RTI Connext DDS environment using the 6.1.1 XML schema.

---

## Configuration

The controller determines the default XML configuration relative to the Python file.

For the controller implementations under `Capstone/tms/`, the expected configuration is:

```text
../xml/tmg_xml_24_mar.xml
```

from the `Capstone/tms/` directory.

The feeder-driven implementation also supports explicitly specifying an XML configuration and DDS participant:

```bash
python controller_typev_feeder_driven.py [xml_path] [--participant PARTICIPANT]
```

For example:

```bash
python controller_typev_feeder_driven.py
```

or:

```bash
python controller_typev_feeder_driven.py ../xml/tmg_xml_24_mar.xml
```

---

## Running the Controller

Navigate to the TMS controller directory:

```bash
cd Capstone/tms
```

Then run the desired controller implementation.

### Feeder-driven Type V controller

```bash
python controller_typev_feeder_driven.py
```

### Single-feeder Type V controller

```bash
python controller_typev_single_feeder_patched.py
```

### Type V interface

```bash
python controller_typev_interface_patched.py
```

> **Important:** These controllers are designed to communicate with a live DDS/TMS environment and may run continuously. Do not execute them against a production or physical microgrid unless the appropriate test procedures and safety controls are in place.

---

## Controller Operation

The Type V controller generally follows this control loop:

```text
┌──────────────────────────┐
│ Publish Controller       │
│ Heartbeat / Identity     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Read DDS/TMS State       │
│ - Device Info            │
│ - Heartbeats             │
│ - Measurements           │
│ - Diagnostics            │
│ - Power Ports            │
│ - Replies                │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Discover / Update Device │
│ State                    │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Diagnose Microgrid       │
│ - Faults                 │
│ - Communication Loss     │
│ - Grounding Conditions   │
│ - Port State             │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Manage Generation        │
│ Start/maintain sources   │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Determine Feeder Action  │
│ OPEN / CLOSE / HOLD      │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Execute DDS Commands     │
│ and monitor responses    │
└──────────────────────────┘
```

The loop typically executes approximately once per second.

---

## Fault and Safety Logic

The Type V implementations contain logic intended to prevent unsafe feeder operation.

Examples of monitored conditions include:

- Grounding faults
- Diagnostic faults
- Communication loss
- Stale heartbeats
- Command timeouts
- Power-port state mismatches
- Unexpected feeder conditions

Depending on the implementation, these conditions can result in actions such as:

```text
OPEN_PORT
RETRY_OPEN_PORT
CLOSE_PORT
HOLD_AND_ALERT
```

A feeder may be restored when an operational generation source is available and the feeder is otherwise considered healthy.

---

## Device Discovery

The controller discovers devices through TMS `DeviceInfo` and heartbeat messages.

Recognized roles include:

| Role | Purpose |
|---|---|
| Controller | Microgrid controller |
| Distribution | Feeder/distribution device |
| Source | Generator/power source |
| Load | Electrical load |
| Storage | Energy storage device |

The controller maintains internal state for discovered sources and feeders and updates that state as DDS messages arrive.

---

## Generator Management

The controller can identify generation sources and obtain information such as:

- Device ID
- Rated power
- Fuel capacity
- Low-fuel cutoff
- Current real power delivery
- Generator operating state

Some implementations automatically request generators to enter:

```text
ESSL_OPERATIONAL
```

when they are not already operational.

Generator information and fuel-related data can also be recorded in the included text files for analysis.

---

## Data Collection

The repository contains several text files used for development and analysis:

### `Generator_Information_24_Hours.txt`

Contains generator-related information collected during testing/operation.

### `Generator_fuel_ups.txt`

Contains fuel-related data collected during testing.

### `Total_Real_Delivered_Combined.txt`

Contains recorded total real power delivered by the monitored sources.

These files can be used for post-run analysis of generator performance and system behavior.

---

## Development / Version History

There are multiple controller implementations in the repository because the project evolved through several iterations.

The filenames indicate several development stages:

- `controller.py`
- `controller-test.py`
- `controller-test-patched (1).py`
- `controller-test-patched-v2.py`
- `controller_typev_interface.py`
- `controller_typev_interface_patched.py`
- `controller_typev_interface_patched_v2.py`
- `controller_typev_interface_phase_display.py`

When modifying the project, identify the controller implementation currently used by the TMS/test environment before making changes. The similarly named files are not necessarily interchangeable.

---

## Troubleshooting

### `ModuleNotFoundError: rticonnextdds_connector`

The RTI Connext DDS Python Connector is not available to the Python interpreter.

Verify that RTI Connext DDS is installed and that the Python environment can locate the connector package.

---

### DDS connection/configuration errors

Verify:

1. The XML configuration exists.
2. The path supplied to the controller is correct.
3. The configured DDS participant exists.
4. The RTI Connext DDS environment is initialized correctly.
5. The controller and TMS devices are on the same DDS domain/environment as expected.

---

### No devices are discovered

Check that the TMS simulator/devices are running and publishing `DeviceInfo` and `Heartbeat` messages.

The controller depends heavily on these messages to build its internal representation of the microgrid.

---

### Feeder remains in a hold/alert state

Inspect the controller's printed status for:

```text
faults=
advisories=
desired_action=
reason=
```

Common causes include:

- Missing feeder heartbeat
- Grounding fault
- Diagnostic fault
- Command timeout
- Power-port state mismatch
- No operational generation source

---

## Testing

The repository contains development/test scripts, but there is currently no conventional automated test suite or `pytest` configuration included.

`test_script.py` is a basic development test and is not a full unit-test framework.

For controller testing, use the appropriate TMS/DDS simulation environment and validate:

- Device discovery
- Heartbeat behavior
- Generator startup
- Feeder fault detection
- Feeder opening
- Feeder restoration
- Power-switch command confirmation
- Command timeout/retry behavior
- Communication-loss handling
- Measurement collection

---

## Safety Considerations

This software interacts with a microgrid control interface and includes functionality capable of issuing generator and power-switch requests.

**Do not connect experimental controller software to energized physical equipment without appropriate authorization, testing, engineering review, and safety procedures.**

Testing should preferentially use a simulator or controlled test environment.

---

## Known Limitations

- Multiple controller versions are present and their intended deployment status is not explicitly documented in the repository.
- No dependency lockfile or `requirements.txt` is currently included.
- There is no comprehensive automated test suite.
- Some scripts contain legacy/development code.
- Several implementations assume a particular DDS/TMS topic configuration.
- Controller behavior depends on the structure and availability of messages published by the TMS environment.
- Some data collection paths use hard-coded or environment-specific file locations.

---

## Future Improvements

Potential improvements include:

- Consolidating the controller implementations into a single maintained version.
- Adding a formal `requirements.txt` or `pyproject.toml`.
- Creating automated unit and integration tests.
- Adding structured logging instead of relying primarily on console output.
- Moving configuration values into a dedicated configuration file.
- Improving documentation of TMS message schemas.
- Adding a formal state-machine diagram for feeder and generator control.
- Adding simulation-based regression tests.
- Separating DDS communication, device state management, diagnostics, and control logic into independent modules.
- Adding automated analysis/visualization of collected generator and power-delivery data.
- Documenting the final operational controller and its intended deployment environment.

---

## Academic Context

**Course:** XE401 – Integrative System Design I  
**Institution:** United States Military Academy  
**Project:** FORGE-IV  
**Repository:** USMA EECS AY27 Team Repository – Team 6

This repository represents an iterative engineering project involving software development, distributed systems, microgrid control, electrical-system monitoring, and DDS-based device communication.

---

## Contributors

Project contributors should be listed here with their appropriate names, roles, and/or GitHub handles.

Suggested format:

```text
- Name — Role / Area of Responsibility
- Name — Role / Area of Responsibility
- Name — Role / Area of Responsibility
```

---

## License

No explicit open-source license is included in the repository at the time of writing.

Unless a license is added by the project owners, the source code should be treated as project-owned and should not be assumed to be freely reusable or redistributable.

---

## Quick Reference

| Item | Value |
|---|---|
| Primary language | Python |
| Communication | RTI Connext DDS |
| System | Tactical Microgrid System (TMS) |
| Primary controller | Type V controller implementations |
| DDS configuration | `Capstone/xml/tmg_xml_24_mar.xml` |
| DDS participant | `TmsParticipantLibrary::TmsParticipant` |
| Main interface | TMS DDS topics |
| Loop frequency | Approximately 1 Hz |
| Automated test framework | Not currently included |

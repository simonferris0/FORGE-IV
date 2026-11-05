# Controller architecture and development families

The active [controller](../controller_typev_interface_patched_v2.py) is a standalone `TypeVControllerInterface`, with dataclasses for source, feeder, generic device, and sequence state. It does not import the other controller scripts. Static import inspection found standard-library imports plus `rticonnextdds_connector`; no repository-local module imports or shell launch scripts/test framework configuration were found.

`run()` opens `TmsParticipantLibrary::TmsParticipant`, binds DDS readers and writers, publishes controller identity, and repeats:

1. Publish controller heartbeat.
2. Read discovery, heartbeat, state, electrical measurements, diagnostics, grounding, ports, replies, and control parameters.
3. Diagnose the feeder.
4. Manage generation and feeder switching.
5. Publish controller diagnostics and print status, then sleep one second.

Controller identity is `controller`. Sources enter `self.sources` from numeric role 2 or string `ROLE_SOURCE` in `DeviceInfo`. Loads, storage, and other devices have separate discovery dictionaries. State/measurement samples for undiscovered source IDs are ignored. Source ratings are read from `powerDevice.source.loadSharing.maxRealPower` with the existing 0.8 factor; measured real/reactive power is converted to kW/kVAR. Measurements use only the first `externalMeasurement` port. Feeder measurements retain phase A/B/C voltage, current, frequency, and power.

`_manage_generation()` automatically requests OPERATIONAL for OFF/UNKNOWN sources on its cooldown, plus additional capacity under load. `_manage_feeder()` can request isolation/restoration. The label `HOLD_MONITORING` in a feeder action does not provide a controller-wide monitoring-only mode. `_safe_take()` returns an empty list on reader or sample conversion exceptions, making failures look like absent data. None of these behaviors changed in cleanup.

## Separate historical lines

| Family | Contents and useful differences |
| --- | --- |
| Procedural | Root `controller.py`, `controller-test.py`, `controller-test-patched (1).py`, `controller-test-patched-v2.py`, plus two exact baseline copies in `Capstone/tms/`. Global source/load state, two-generator decisions, fuel and power logging. `controller-test.py` adds feeders and has live iteration-50/100 switch requests; both later patched files have those test requests commented out. The first patched variant adds role normalization and feeder registration helpers; v2 adds feeder ID filtering. |
| `TypeVControllerInterface` | Base OO rewrite, numeric-source-role patch, active patched_v2, and phase_display sibling. This is a separate development line from the procedural controllers. Inactive variants are in [archive/typev-interface](../archive/typev-interface/). |
| Feeder command experiments | [archive/feeder-command](../archive/feeder-command/) contains `MicrogridController` and `TypeVController` experiments with `PendingCommand`, sequence tracking and timeouts. The single-feeder variant adds `first_present()` and feeder ID locking. They are references for future work, not replacements or proven fixes for the active controller. |

The base interface accepts string source roles; patched adds numeric role 2. Patched_v2 adds load/storage/other discovery, expands feeder ID matching while excluding `hps-`, and reduces diagnostic publication to the device ID rather than the earlier freeform payload.

The **phase_display variant is a sibling, not a strict upgrade** of patched_v2. It adds phase telemetry display and early feeder-candidate logging. For OPEN confirmation it checks both significant phase current (0.50 A threshold) and aggregate real power (0.10 kW threshold), replacing patched_v2's power-or-voltage condition. CLOSE confirmation remains voltage-based. It removes patched_v2's load/storage/other tracking and reverts its broader feeder ID matching. Preserve these differences for deliberate future comparison.

## Path constraints

Procedural files and `Capstone/tms/tms_reader.py` use `__file__` plus `/../xml/tmg_xml_24_mar.xml` with no effective XML override. The `Capstone/tms/` copies currently resolve correctly; the root procedural copies already point outside this checkout's XML location. Moving these scripts would require changing code or restoring layout, so they remain in place. Procedural scripts also open three logs relative to the working directory, with initial truncation.

Archived OO controllers accept an explicit XML argument and have no repository callers/importers found. Their original fallback XML and `sys.path` adjustments remain untouched; archive location changes those calculations. An explicit XML path bypasses the fallback, but any reliance on external modules supplied by the original layout remains unverified. Restore their original layout if needed; do not treat an archive move as runtime compatibility validation.

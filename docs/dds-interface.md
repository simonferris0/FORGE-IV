# DDS interface notes

Source of truth: [Capstone/xml/tmg_xml_24_mar.xml](../Capstone/xml/tmg_xml_24_mar.xml), compared statically with the [active controller](../controller_typev_interface_patched_v2.py). The baseline XML is unchanged; the controller now defaults to monitoring with improved Python reader diagnostics.

The controller opens `TmsParticipantLibrary::TmsParticipant`. Its domain reference is `TmsDomainLibrary::TmsDomain`, domain ID **0**. Inputs are under `TmsSubscriber`, outputs under `TmsPublisher`. XML topic names are case-sensitive; “ACMeasurementUpdate” below describes the message family, while the actual XML topic is `AcMeasurementUpdate`.

| Exchange | XML topic / bound endpoint | Current Type V handling |
| --- | --- | --- |
| Identity/discovery | `DeviceInfo` / `DeviceInfoReader`, `DeviceInfoWriter` | Publishes controller identity; registers source role 2 or `ROLE_SOURCE`; also feeder/load/storage/other devices. |
| Heartbeat | `Heartbeat` / `HeartbeatReader`, `HeartbeatWriter` | Publishes `deviceId=controller`, loop `sequenceNumber`. Incoming `deviceId` and `sequenceNumber` update feeder state only; no source heartbeat timestamp/sequence tracking. |
| Source state | `EnergyStartStopState` / `EnergyStartStopStateReader` | Maps numeric `presentLevel` 1–7 to UNKNOWN, OFF, WARM, IDLE, READY, READY_SYNCED, OPERATIONAL for known sources. |
| AC measurements | `AcMeasurementUpdate` / `ACMeasurementUpdateTypeReader` | Uses `deviceId`, first `externalMeasurement`, `portNumber`, `line`; sums real/reactive watts/vars into kW/kVAR for known sources, loads, storage; stores feeder phases. |
| Source command | `EnergyStartStopRequest` / `EnergyStartStopRequestWriter` | Sends nested `requestId` with requester/target/config, plus `sequenceId`, `fromLevel`, `toLevel`, `switchConditions`. Automatic requests require `--enable-control`. |
| Feeder command | `PowerSwitchRequest` / `PowerSwitchRequestWriter` | Sends nested request ID including port, `sequenceId`, and OPEN/CLOSED continuity. Automatic switching requires `--enable-control`. |
| Reply | `Reply` / `ReplyReader` | Parser mismatch described below; no validated source command/reply lifecycle. |

Other bound inputs are `ActiveDiagnosticStateReader`, `ControlParameterStateReader`, `GroundingCircuitStateReader`, `PowerPortStateReader`, and `MetricParameterStateReader`. The additional output is `ActiveDiagnosticStateWriter`; the current controller writes its device ID and does not send its printed fault list as a freeform message.

## Reply contract comparison — future work

The XML `tms::Reply` has **top-level** `requestingDeviceId`, `targetDeviceId`, `config`, `portNumber`, `requestSequenceId`, and `status`. `status` is a `ReplyStatus` containing `code` and `reason`.

Current `_read_reply()` instead reads `msg.get("requestId", {})`, extracts a nested `targetDeviceId`, and looks for top-level `sequenceId`. It only updates a feeder-like device's `last_switch_seq`; it does not correlate source replies or inspect reply status. Request messages' nested `requestId`/`sequenceId` shape must not be assumed to be the reply shape. Compare captured dictionaries and XML before a separate parser change; no correction is included here.

## Network evidence and limits

The checked-in XML contains no explicit IPv6 transport selection, transport mask, interface binding, or discovery-peer configuration demonstrating IPv6-only DDS operation. Runtime defaults and external RTI/network configuration are not established by this checkout. Host IPv6 reachability alone does not demonstrate discovery, matching DDS types/QoS, or sample delivery. Trevor and SS6 should record host addressing/interface scope, reachability, RTI transport configuration, domain/type/QoS agreement, and observed samples as separate evidence during integration.

The reader helper reports unexpected Python exceptions with context and repeat limiting; native RTI errors need stderr capture. An empty status display alone cannot establish that Type I is not publishing. See [confirmed findings and diagnosis](dds-diagnostics.md) and the [IPv6 migration prerequisites](ipv6-migration.md).

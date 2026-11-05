# Sprint 2 — Type I / Type V integration plan

Monitoring mode and offline tests are now implemented; runtime acceptance and IPv6 migration remain pending. The DDS contract is unchanged.

| Owner | Integration responsibility |
| --- | --- |
| Jeffrey Sithong / SS6 | Type V monitoring/control boundaries, discovery/state/measurement presentation, later reply correlation |
| Simon Ferris | Type I source behavior and Chroma control software |
| Trevor Patton | Type I DDS publications/subscriptions and network integration |

## Next implementation, separately reviewed

1. **Validate monitoring-only mode on the simulator.** The default and `--monitor-only` block source and feeder requests at the helpers; `--enable-control` retains existing automatic decisions. Identity, heartbeat, and existing device-ID-only diagnostic publication remain enabled. Follow the [Pi and simulator acceptance procedure](monitoring-validation.md) with an independent request observer. Offline fake-endpoint tests pass; runtime evidence is pending.
2. **Source heartbeat tracking.** Associate source `Heartbeat.deviceId` with discovered sources; track sequence and local receipt time, display fresh/stale status, and agree on timeout and restart behavior. Existing feeder heartbeat handling does not cover this. Add tests for source versus feeder IDs, missing samples, and sequence resets as part of that implementation.

## Prototype sequence and evidence

| Stage | Evidence to collect later |
| --- | --- |
| IPv6 network reachability | Host/interface addresses and scope, route/interface selection, bidirectional reachability. This is separate from DDS success. |
| DDS discovery and heartbeat exchange | Agreed domain 0 or deliberately coordinated configuration, participant/type/topic/QoS agreement, RTI transport evidence, captured Type I and Type V DeviceInfo/Heartbeat samples and IDs. Claim IPv6-only DDS only after transport configuration and observed traffic establish it. |
| Source state | Known source ID, numeric/string role representation, `presentLevel` mapping checked against XML, observed state transitions without automatic control in monitoring mode. |
| AC measurements | Confirm `externalMeasurement`/port/line shapes, units, phase order, conversion, timestamp freshness, and missing fields using actual Type I samples. Current controller consumes the first external port only. |
| Manual command/reply | After deliberate enablement, one manually triggered request to an agreed target; match requester, target, request sequence, status code/reason, and timeout. First reconcile the XML Reply shape with the current parser. Coordinate source actions with Simon. |

Python reader observability is improved. The native key-hash/deserialization errors and reply parser mismatch remain unresolved; capture runtime evidence using the [diagnostic runbook](dds-diagnostics.md). Do not infer source heartbeat reception from feeder status or discovery alone. Do not adopt an archived controller wholesale: the families contain different behaviors and assumptions.

Local validation provides no runtime, IPv6, DDS interoperability, or hardware success evidence. Source heartbeat tracking is the next controller feature after monitoring acceptance.

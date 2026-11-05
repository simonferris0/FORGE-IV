# Sprint 2 — Type I / Type V integration plan

This is a future work plan. Cleanup only organizes files and documentation; it does not implement monitoring-only mode or change the DDS contract.

| Owner | Integration responsibility |
| --- | --- |
| Jeffrey Sithong / SS6 | Type V monitoring/control boundaries, discovery/state/measurement presentation, later reply correlation |
| Simon Ferris | Type I source behavior and Chroma control software |
| Trevor Patton | Type I DDS publications/subscriptions and network integration |

## Next implementation, separately reviewed

1. **Monitoring-only mode.** Add an explicit controller mode and verify that it prevents both source start/stop requests and feeder switch requests, including every automatic path. Agree whether identity, heartbeat, and diagnostic publications remain enabled. Keep the current baseline behavior available intentionally. Use isolated mocks or recorded samples to verify command suppression before equipment testing. No such mode exists yet.
2. **Source heartbeat tracking.** Associate source `Heartbeat.deviceId` with discovered sources; track sequence and local receipt time, display fresh/stale status, and agree on timeout and restart behavior. Existing feeder heartbeat handling does not cover this. Add tests for source versus feeder IDs, missing samples, and sequence resets as part of that implementation.

## Prototype sequence and evidence

| Stage | Evidence to collect later |
| --- | --- |
| IPv6 network reachability | Host/interface addresses and scope, route/interface selection, bidirectional reachability. This is separate from DDS success. |
| DDS discovery and heartbeat exchange | Agreed domain 0 or deliberately coordinated configuration, participant/type/topic/QoS agreement, RTI transport evidence, captured Type I and Type V DeviceInfo/Heartbeat samples and IDs. Claim IPv6-only DDS only after transport configuration and observed traffic establish it. |
| Source state | Known source ID, numeric/string role representation, `presentLevel` mapping checked against XML, observed state transitions without automatic control in monitoring mode. |
| AC measurements | Confirm `externalMeasurement`/port/line shapes, units, phase order, conversion, timestamp freshness, and missing fields using actual Type I samples. Current controller consumes the first external port only. |
| Manual command/reply | After deliberate enablement, one manually triggered request to an agreed target; match requester, target, request sequence, status code/reason, and timeout. First reconcile the XML Reply shape with the current parser. Coordinate source actions with Simon. |

Treat `_safe_take()` observability and the reply mismatch as separate implementation tasks; neither was fixed here. Do not infer source heartbeat reception from feeder status or discovery alone. Do not adopt an archived controller wholesale: the families contain different behaviors and assumptions.

Completion of this cleanup provides no runtime, IPv6, DDS interoperability, or hardware success evidence.

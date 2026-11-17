# FORGE-IV · SS6 Type V Controller

## Sprint 2 integration summary and follow-on requirements

| Prepared | Owner | Work item |
| --- | --- | --- |
| 17 November 2026 | Jeffrey Sithong · SS6 | PBI-11 · Trello card 39 |

## Sprint outcome

> **Breakthrough**
>
> Trevor's Type I Raspberry Pi published application heartbeats that the Type V controller decoded on the bench. This was the first practical milestone for the link: SS6 could identify Trevor's device and follow its sequence while a second heartbeat stream was present. Source registration, receipt of Type V traffic at Trevor's Pi, and command/reply operation remain open.

Three related SS6 cards are in Sprint Done: inventory the DDS interfaces and messages (35), document the discovery changes (36), and develop the initial integration plan (37). Card 39 records what the next integration run needs. The parent PBI-11 seven-function demonstration is planned for Sprint 3 or 4.

## Evidence from the saved runs

All run times below are UTC. Log files are in `outputs/`.

| Run | Observed evidence |
| --- | --- |
| Nov 10 · `trevor-link-20261110T153908Z.log`<br>Nov 12 · Simon runs at 15:08:51 and 15:24:36 | DeviceInfo decode failures. Per-device heartbeat RX lines are absent. Earlier logging did not expose all external heartbeats, so silence cannot establish packet loss. |
| Nov 12 · `trevor-link-20261112T161356Z.log` | **19 consecutive Type I heartbeats**, sequences 2–20, from `forge-type-i-01`. **27 consecutive heartbeats**, sequences 1997239–1997265, from `stamp-eio`. The display continued to show “Sources: none discovered.” |
| Nov 12 · `trevor-link-20261112T161824Z.log` | **12 consecutive heartbeats**, sequences 1997507–1997518, from `stamp-eio`. No `forge-type-i-01` sample appears. The file does not establish why that stream ended. |

Bench labels: Jeffrey identified stamp-eio as his side and forge-type-i-01 as Trevor's. The SS6 Python heartbeat writer uses a third ID, controller. Each `[HEARTBEAT RX]` is a sample decoded at Type V. The status block is a local printout. Type V also calls its heartbeat writer once per loop, independently of incoming samples. Neither the printout nor the local write confirms a matching receipt on Trevor's Pi. The strongest saved result is Type I -> V.

**What worked.** monitor-only mode let the team exercise DDS with source and feeder command requests blocked. Logging external IDs and sequences before DeviceInfo registration exposed a working heartbeat path even while identity decoding failed. Keeping separate run files made the two streams comparable.

## Joint retest checklist

- [ ] Record both launch commands, commits, effective XML/type versions, domain (SS6 baseline is 0), interface, IPv6 addresses, discovery peers and endpoint QoS. Record which physical Pi/process owns each of the three IDs. Start both readers before publishing. Repeat after reboot to verify PBI-04.

- [ ] Keep Type V in monitor-only. Trevor logs RX for controller; Jeffrey logs RX for forge-type-i-01. Save both publishers' TX and both receivers' RX with run ID, device ID, sequence and timestamp. Match the same ID/sequence across hosts in each direction. If Trevor sees no controller samples, inspect his reader's topic, type, QoS, match status and device-ID filter; compare against evidence that controller traffic left the Type V host.

- [ ] Measure from Type I startup to first recognized source at Type V (board target: within 3 s). Timestamp individual heartbeats on a monotonic clock for 10 continuous minutes; report intervals outside 0.9–1.1 s, sequence gaps and resets. Record TX cadence and RX intervals separately. The SS6 loop sleeps 1 s after doing work; counting loops cannot verify cadence. Capture DDS discovery and data traffic on the test interfaces and record the active transports to verify the board's IPv6-only requirement.

- [ ] Use `tools/observe_requests.py` as an independent reader during the run. Verify reader matching and retain evidence of zero source/feeder command requests while monitoring. Save paired logs, configuration and capture together so another team member can repeat the test.

## DeviceInfo failure and diagnostic plan

The first native RTI error decodes `ControlHardwareInfo.minTemperature` as NaN. The XML permits -273 to 10000. `DeviceInfo.controlHardware` then fails to deserialize; key-hash and reader-collator errors follow for the same sample. The hex values identify DDS endpoints. The writer after RECEIVE FROM is `0x01060A02,0x145B0000,0x0B6E0001:0x00000902` in the later runs. The prefix before RECEIVE FROM identifies the local reader. Those numbers alone cannot assign the failure to Trevor, stamp-eio or the SS6 startup writer.

Jeffrey and Trevor: first run the Type V monitor with other publishers off, then introduce stamp-eio and the Type I publisher separately. Record each writer GUID from discovery and compare it to the failing sample in that run. On the identified writer, save the effective DeviceInfo immediately before write. Compare its type definition, member layout, optional-member handling and wire representation with the receiver. Two plausible causes are an invalid value in a present controlHardware struct or a valid payload interpreted with a different layout. SS6's identity publisher omits that optional struct.

If the producer has no hardware metadata, verify it actually emits the struct as absent. If present, supply all required members and verified finite temperature limits. If the layouts differ, align the two endpoint definitions and retest the original payload. Preserve the XML bounds and native logging. Pass when Type V decodes the expected Type I identity and source role, lists forge-type-i-01 as a source, and the attributed writer produces no related range/key-hash errors on restart while heartbeat reception continues.

## Code gaps and integration dependencies

### SS6 / source health

 `_read_heartbeat()` prints external samples but stores freshness for feeder candidates only. Track receipt time and sequence by source ID, allowing heartbeat-before-DeviceInfo. Test normal operation, dropout, stale indication, restart/sequence reset and recovery. Preserve the distinction between “heartbeat heard” and “source registered.”

### SS6 + Trevor + metering / PBI-05

 depends on PBI-02 external metering and PBI-04B messaging. Agree on units, phase and port mappings; SS6 currently reads only the first external measurement port. Feed a known multi-phase sample and compare the dashboard to its payload. Capture 1 s and 0.1 s reports in Table B.82 order; verify jitter <=10 ms and no missed deadlines.

### SS6 + Trevor + Simon / PBI-06

 depends on discovery and PBI-01 Chroma control. `_read_reply()` looks for nested `requestId.targetDeviceId` and `sequenceId`. XML Reply provides top-level `requestingDeviceId`, `targetDeviceId`, `requestSequenceId` and status. Correct the reader and correlate each reply to its request. Exercise success, rejection, unrelated reply and timeout in the simulator. Verify legal/illegal transitions and replies within 0.1 s. Measure with timestamps at the request origin; a 1 s display loop cannot resolve a 0.1 s result. Simon verifies the corresponding source behavior.

### SS6 / regression

 `_read_power_port_state()` expects `requestId.portNumber`; XML supplies deviceId and powerPorts. Test the corrected reader with a multi-port feeder sample. These Python parser defects occur after decode and are separate from the native DeviceInfo error.

* PBI-08 follows PBI-06. Simon, Trevor and SS6 correlate actual source and reported states: Drop Load reaches READY SYNCED with source online; Shutdown reaches OFF. For PBI-11, retain a scripted seven-function run, dashboard-to-emulator evidence, and Type III/V regression results.

## Evidence and references

[Trello board](https://trello.com/b/cVCiWune/ay27-06-tms-iv-forge) · [WIP card 39](https://trello.com/c/0CoSUOII) · [Reviewed GitHub revision](https://github.com/simonferris0/FORGE-IV/tree/4af2bc64f8b4f8c1746c62e3a025757893e5bd2f)

**Branch** `ss6/sprint2-typei-link`

| Evidence | Location |
| --- | --- |
| Runtime logs | `outputs/` · five logs |
| Controller | `controller_typev_interface_patched_v2.py` |
| DDS schema | `Capstone/xml/tmg_xml_24_mar.xml` |
| Diagnostic notes | `docs/dds-diagnostics.md` |
| Integration plan | `docs/sprint-2-integration.md` |
| IPv6 notes | `docs/ipv6-migration.md` |

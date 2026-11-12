# DDS key-hash/deserialization diagnosis

## Evidence and scope

Jeffrey observed `ammps30` discovery and ESSL_OPERATIONAL at Type V, with simulator OPERATIONAL / RemoteControl / actor `controller`. This strongly suggests that the earlier automatic source request reached the simulator and resulting state reached Type V. It does not establish heartbeat timing, AC measurements, reliable interoperability, or IPv6 transport. A missing feeder is expected in this source-only setup.

Supplied Type V runtime (existing `/home/forge/FORGE-IV-SS6/.venv`):

| Component | Observed value |
| --- | --- |
| Python | 3.10.12 |
| Python package `rticonnextdds-connector` | 1.2.4 |
| NDDSCORE, NDDSC, RTICONNECTOR native build | 6.1.2.21, `20241009T000000Z_RTI_REL` |
| Import / `Connector.get_version()` | Completed successfully |
| OS release, kernel, CPU architecture, bitness | Still needed |
| Desktop simulator build and effective DDS config | Still needed |
| Full native key-hash/deserialization error text | Still needed |

The XML declares schema/version **6.1.1**; controller DeviceInfo advertises data-model string **1.2.3**. These labels are not the Python package version or native middleware version. The reported runtime builds do not establish the cause of errors or prove a working IPv6 transport. No RTI library is installed in the laptop inspection Python used for offline tests.

## Confirmed static findings

The baseline XML was preserved byte-for-byte. The active participant uses domain 0. All ten Python-bound reader endpoints and five bound writer endpoints resolve to existing XML topics, registered types and QoS profiles. No active endpoint's reader/writer topic binding mismatch was found. XML well-formedness is not full type compatibility validation against the desktop.

| Type/topic family | Key and relevant layout |
| --- | --- |
| DeviceInfo, Heartbeat, EnergyStartStopState, ac::MeasurementUpdate | Key `deviceId`, type `tms::Identity` (string bounded to 32 characters). Heartbeat sequence is uint32. |
| EnergyStartStopRequest | Composite key `requestId`: requestingDeviceId, targetDeviceId, config. `sequenceId` is uint64 (`RequestSequence`), not part of that key. |
| PowerSwitchRequest | Composite key `requestId`: same fields plus portNumber. `sequenceId` is uint64. |
| Reply | Top-level keys requestingDeviceId and targetDeviceId; top-level config, portNumber, requestSequenceId, and status (code/reason). |
| PowerPortState | Key deviceId; payload `powerPorts`. It has no requestId member. |
| ActiveDiagnosticState | Key deviceId; payload `codes` and `overflow`, not a freeform message. |

Confirmed Python/schema differences left for separate behavior changes:

- `_read_reply()` looks for nested `requestId.targetDeviceId` and top-level `sequenceId`, rather than the XML Reply shape. It does not correlate source replies or evaluate status. This affects Python handling **after** deserialization; it does not prove the origin of a native deserialization error.
- `_read_power_port_state()` looks for `requestId.portNumber`, absent from this XML. Again this is a post-deserialization parsing issue, not established native error causation.
- The source state map treats numeric 1 as UNKNOWN. In the XML enumeration, 0 is UNKNOWN, 1 is ANY, 2 is OFF, and 7 is OPERATIONAL. The fallback also yields UNKNOWN for 0. Compare actual publisher enum representation before a separate parser change; no mapping was changed here.
- Participant and several writer user_data values identify `python-1`, while application identity is `controller`. user_data bytes are not the `deviceId` key. Coordinate naming later rather than editing serialization to chase an error.
- Unused XML endpoint `ac::LoadSharingRequestWriter` is bound to topic `AcLoadSharingState`/state type rather than the similarly named request topic. The active Python does not bind/write it. This naming/binding inconsistency warrants comparison if that endpoint is ever used; it was not changed.

QoS is internally paired in the active baseline: DeviceInfo and state readers use PublishLast (reliable, transient-local, depth 1); heartbeat and AC measurement use Medium (best-effort, volatile, depth 1); command writers use Command (reliable, volatile, depth 1, strength 1); Reply uses reliable/volatile/depth 128. These profiles use exclusive ownership. Compare simulator offered/requested QoS, ownership strength, keys, XTypes/extensibility/representation, bounds and enum values. Changing reliability or ownership broadly is not a supported deserialization fix.

Connector creates **all** entities in the selected XML participant, including readers not consumed by this Python loop. Native errors may therefore come from an unconsumed endpoint. RTI documents participant/entity creation in its [Connector reference](https://community.rti.com/static/documentation/connector/1.2.2/api/python/connector.html).

## Diagnostics implemented

Expected no-data `wait()` timeouts (Connector TimeoutError or built-in TimeoutError) and empty successful takes are quiet. Other wait/take/sample conversion failures now print reader, topic, operation, exception type and text to stderr. The topic-processing dispatch also reports malformed payload exceptions with context and proceeds to other topics. Repeated Python messages are limited to one per reader/operation/exception type every 30 seconds, with repeat totals on the next report. This preserves reception attempts without hiding the first unexpected error. See [RTI's wait/take semantics](https://community.rti.com/static/documentation/connector/1.2.2/api/python/input.html).

Native middleware errors can occur on RTI threads without a Python exception. They are **not** intercepted, redirected to silence, or disabled. Capture both stdout and stderr using the [timestamped monitoring command](monitoring-validation.md). A lack of Python errors is not a clean native-error result.

## Hypotheses, not findings

Different publisher/subscriber layouts under the same topic/type name, incompatible keys/bounds/enums, invalid serialized values, dispose/key-only sample handling, and a version/platform-specific middleware defect are investigation candidates. None is established by a screenshot description. RTI's [deserialization knowledge-base note](https://community.rti.com/kb/what-causes-prespsreaderqueuestorequeueentrydeserialize-messages) identifies differing IDL as a possible cause. Its [6.1.1 release notes](https://community.rti.com/static/documentation/connext-dds/6.1.1/doc/manuals/connext_dds_professional/release_notes/RTI_ConnextDDS_CoreLibraries_ReleaseNotes.pdf) discuss a specific mutable-derived-key issue fixed in that release; this is not evidence that a 6.1.2.21 installation has the same issue. Do not set keyhash/dispose protocol flags or upgrade packages without matching the full error, type shape, versions and reproduction to a documented case.

## Collect on the Pi, then compare the desktop

From the repository root with the existing venv activated, capture the following output (these commands query versions/files and do not create a DDS participant):

```bash
python --version
python -m pip show rticonnextdds-connector
python -c 'import rticonnextdds_connector as rti; print(rti.__file__); print(rti.Connector.get_version())'
python -c 'import sys, platform, struct; print(sys.executable); print(platform.platform()); print(platform.machine()); print(struct.calcsize("P") * 8)'
uname -a
cat /etc/os-release
git branch --show-current
git rev-parse HEAD
git status --short
sha256sum controller_typev_interface_patched_v2.py Capstone/xml/tmg_xml_24_mar.xml
printenv NDDS_DISCOVERY_PEERS NDDS_QOS_PROFILES NDDSHOME
ip -br address
ip -6 route
```

Also provide any `NDDS_DISCOVERY_PEERS` file and `USER_QOS_PROFILES.xml` in the launch directory, plus the complete monitoring log from startup through several errors. Include the lines preceding the first error, reader/topic/type names, GUIDs or instance handles, timestamps, and whether it occurs on source startup, state changes, or shutdown. Keep the full native error chain rather than only the last key-hash line. `printenv` can return a nonzero status for unset variables; record them as unset.

From the simulator desktop supply `sim_start.sh`, selected `src.json` and referenced grid/source configs, simulator repository commit or binary/container image version/digest, exact executed command/environment, DDS vendor/native/code-generator versions, effective XML/QoS/IDL or generated type definitions and hashes, domain/transport/peer/interface settings, complete stdout/stderr logs, and the corresponding capture. The files are not in this checkout. Trevor should supply the equivalent Type I DDS build/config/type information before three-party integration.

Next diagnostic steps: reproduce in monitoring mode with only the expected source; identify the offending topic/endpoint/GUID from the first native error and capture; compare both sides' actual type/key/QoS/representation definitions; separate ordinary data from dispose/unregister samples; then check native **6.1.2.21** and desktop-build documentation for a matching issue. Make only the smallest compatibility change justified by that evidence. No native-error root cause or fix is claimed here.

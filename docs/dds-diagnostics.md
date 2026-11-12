# DDS key-hash/deserialization diagnosis

## November 10/12 link logs: separate heartbeat and DeviceInfo evidence

Reviewed [Trevor-named log](../outputs/trevor-link-20261110T153908Z.log) and [Simon-named log](../outputs/simon-link-20261112T150851Z.log) at branch commit `ceae9dc3271bf2f2ac3764f27010b0f7b8fff355`. Jeffrey identifies the Simon-named run as a **solo Type V run with the simulator off**. The filenames do not establish sender identity.

Both first fail at `RTIXCdrInterpreter_checkPrimitiveRange`, decoding `tms::ControlHardwareInfo.minTemperature` as NaN outside `[-273, 10000]`, then fail decoding `DeviceInfo.controlHardware`, then report serialized-sample-to-keyhash/collator errors. Investigate the first range/deserialization failure before interpreting later key-hash lines as a separate defect. This establishes what the receiver decoded, not that a producer explicitly assigned NaN: a layout/representation mismatch could also produce an invalid interpretation.

Both identify the **same failing writer** after `RECEIVE FROM`:

```text
0x01060A02,0x145B0000,0x0B6E0001:0x00000902
```

The leading GUID before `|RECEIVE FROM` is the local reader: Trevor-named run prefix `0101F9B8:BA3EE08C:5F205CC7`, Simon-named run prefix `0101FF8D:D7D6923E:19B55E07`. These prefixes differ from the failing writer prefix. Under ordinary same-participant publication this is evidence against attributing the error to that receiver participant's own startup writer. It does not exclude another local process/participant, remote device, configured/relayed identity, or a runtime sample/layout problem. Do not decode a source IP from the GUID or infer Trevor, Simon, a DDS vendor, or IPv4 from its digits. Map the writer to discovery and captured traffic as described in [validation](monitoring-validation.md).

Neither old log displays external heartbeat IDs/sequences: the old handler only tracked feeder candidates. `Sources: none discovered` does not establish heartbeat absence. The active monitor now emits one unthrottled `[HEARTBEAT RX] deviceId=... sequenceNumber=...` line for each decoded external sample returned by its heartbeat reader, excluding `controller`, without waiting for DeviceInfo. This is separate from DeviceInfo decoding and does not register a source. It reports application heartbeat sequences, not RTPS protocol HEARTBEAT or writer sequence numbers. Sample loss in the best-effort reader remains possible.

## Audit of our startup DeviceInfo producer

`_publish_controller_identity()` sets deviceId and role, merges the following product/topic fields, then writes once. No explicit NaN or temperature assignment is present in this method; it is unchanged by the heartbeat patch.

| Field | What Type V explicitly supplies | Baseline XML / omission |
| --- | --- | --- |
| deviceId, role | `controller`, numeric role 1 | Identity string key and microgrid-controller role. No key change. |
| product.nsn | 13 character elements | Fixed 13-character NatoStockNumber array. |
| product.manufacturerName, modelName | West Point / Type V Controller Interface | Both fit String32. |
| Other product members | Not set | gtin is a required 14-character array; modelNumber, serialNumber, softwareVersion are required strings; platformId is optional. No explicit defaults on these members in XML. Their effective native values need runtime inspection. |
| topics | dataModelVersion `1.2.3`; three empty topic lists | Required fields supplied; optional extensionTopics omitted. This data-model string is not the Connector/native build version. |
| controlHardware | Entire optional struct omitted | If present, hasRealtimeClock (boolean), minTemperature/maxTemperature (float32, each bounded -273 to 10000), numNetworkPorts (uint16, min 0) are nonoptional members. No explicit `default` is defined for these fields. |
| Other optional DeviceInfo metadata | powerHardware, controlParameters, metricParameters, controlService, powerDevice omitted | Omission is not an explicit invalid numeric assignment. |

RTI documents that `set_dictionary()` preserves unspecified existing values, and that optional members can be cleared; documented `clear_members()` reset behavior sets optional members to None and ordinary numeric fields to zero. Those API rules do **not** establish this installed instance's pre-write contents or wire encoding. See [RTI Output reference](https://community.rti.com/static/documentation/connector/current/api/python/output.html) and [optional-member handling](https://community.rti.com/static/documentation/connector/current/api/python/data.html). The public pages identify themselves as 1.2.2; verify actual behavior with package 1.2.4/native 6.1.2.21 before a producer change.

There is currently no verified producer bug in our startup method. Keep its writer, XML bounds, keys and native logging unchanged. Next, attribute the failing writer, compare its effective type/layout with this XML, and obtain that producer's pre-write `output.instance.get_dictionary()` plus its setter inputs using a controlled diagnostic run (do not assume a successful setter means the on-wire sample is valid).

If the identified producer actually emits a present controlHardware struct with NaN and has no hardware metadata, the smallest valid proposed fix is to **unset that optional struct**, for example `output.instance.clear_member("controlHardware")` immediately before the identity write, after verifying optional-member interoperability on both sides. This is a conditional proposal, not applied here. If the struct must be published, all its required fields must be valid; temperature limits should come from the identified controller board/enclosure's verified operating specification and deployment configuration, with finite values, min <= max, and XML bounds enforced. hasRealtimeClock and numNetworkPorts should reflect actual configured hardware. A measured ambient temperature, arbitrary zeros, guessed Raspberry Pi limits, or relaxed bounds are not replacements for that metadata. Fix the attributed producer, rather than inserting unrelated values in Type V merely because its receiver reports the error.

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
| Native error chain | Available in the two November logs above; transport/source attribution still needed |

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

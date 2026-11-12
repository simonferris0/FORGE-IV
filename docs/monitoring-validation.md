# Pi update, launch, and simulator acceptance

Monitoring defaults to receiving and displaying data while blocking the two application command writers. Identity, heartbeat, and existing diagnostic publication remain enabled. `--enable-control` deliberately restores the existing automatic decisions and thresholds. Conflicting mode flags fail argument parsing before RTI is imported.

## Sprint 2 milestone: solo baseline and paired wired IPv4 heartbeat

The milestone is to display Trevor's Type I application heartbeat deviceId and sequenceNumber on the Pi in monitor mode over **wired IPv4**, using the unchanged baseline XML and domain **0**. No source role registration, DeviceInfo success, source control, or feeder is required for this milestone. IPv6 remains optional future work; its generator/tests are unchanged.

Use a named solo run first; repeat this exact Bash block with `run_label=paired` for the paired run. It captures startup, native stderr, metadata, and every displayed decoded heartbeat. Run from the Pi after deploying this patch using the transfer steps below:

```bash
cd ~/FORGE-IV-SS6
source ~/FORGE-IV-SS6/.venv/bin/activate
mkdir -p outputs
set -o pipefail
run_label=solo
xml_path="$(realpath Capstone/xml/tmg_xml_24_mar.xml)"
run_log="outputs/${run_label}-heartbeat-$(date -u +%Y%m%dT%H%M%SZ).log"
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  printf 'run=%s resolved_xml=%s domain=0\n' "$run_label" "$xml_path"
  git branch --show-current
  git rev-parse HEAD
  git status --short
  sha256sum "$xml_path" controller_typev_interface_patched_v2.py
  python --version
  python -c 'import rticonnextdds_connector as rti; print(rti.Connector.get_version())'
  python -u -X faulthandler controller_typev_interface_patched_v2.py "$xml_path" --monitor-only
} 2>&1 | tee "$run_log"
```

A commit ID alone does not identify a dirty deployed controller: keep the script checksum and Git status too. Trevor should record his sender Git commit/dirty state, resolved DDS configuration path/checksum, DDS build, domain, deviceId and each application sequenceNumber transmitted. Record actual values, not a guessed ID. Do not conflate the new script checksum with the unchanged XML checksum.

**Solo:** stop the simulator and Trevor's publisher, and check for other DDS services/processes still running on the Pi or LAN. Start only Type V monitor and a packet capture. Its own `controller` heartbeat is intentionally not printed. External heartbeat lines, if any, need attribution rather than an assumption that the network is empty. If the temperature failure remains, record its exact RECEIVE FROM writer, local reader GUID, and first failure. The Simon-named historic log is this kind of solo run; its filename does not imply Simon was publishing. A persistent writer in solo testing calls for discovery/process attribution, not a claim that Type V necessarily produced NaN.

**Paired:** leave the simulator off. Connect Pi and Type I via the existing wired LAN/cable and obtain their actual assigned IPv4 addresses and interface names. Inspect `ip -4 -br address` on both, and `ip -4 route get PEER_IPV4` to confirm the wired interface/source address; `ping -4 -c 4 PEER_IPV4` is only a reachability check. Do not change host networking/firewall settings during this procedure. Start capture before starting Type V and Trevor's sender. Repeat the launch block with `run_label=paired`. Both sides must use domain 0, compatible Heartbeat type/key/QoS and IPv4 DDS transport/interface settings. Baseline XML has no explicit transport/interface mask, so its filename and a successful ping alone cannot prove wired IPv4 DDS. Check effective RTI profile/peer environment and any working-directory NDDS_DISCOVERY_PEERS/USER_QOS_PROFILES.xml files. If multicast discovery is unavailable, coordinate existing IPv4 unicast peer settings on both sides and record them; do not silently substitute the generated IPv6 configuration.

Expected Pi lines, using the ID and values actually sent:

```text
[HEARTBEAT RX] deviceId='example-typei-id' sequenceNumber=501
[HEARTBEAT RX] deviceId='example-typei-id' sequenceNumber=502
```

Each decoded external sample is printed immediately in monitor mode, including before DeviceInfo. Correlate ID and successive sequence numbers with Trevor's sender log and captured Heartbeat topic writer; heartbeat alone leaves `sources` unchanged. The best-effort/depth-1 baseline reader may drop intervening samples. A changed sequence proves receipt of those samples, not a guaranteed rate, latency, freshness policy, AC measurement delivery, or DeviceInfo success. DeviceInfo NaN errors may coexist with successfully displayed heartbeat samples. A silent heartbeat display needs a separate discovery/transport/type investigation.

Preserve command suppression evidence using the independent request observer below. It must have matched/calibrated endpoints; source inactivity or a monitoring status label alone does not prove zero requests. Stop the sender and verify no further newly received heartbeat lines; do not interpret this patch as stale-source detection. Source heartbeat freshness/role integration remains separate future work.

### Match the failing writer to an IPv4 source

Start a capture on each actual wired interface before participant startup (replace `eth0` if needed), using existing tcpdump/Wireshark access:

```bash
mkdir -p outputs
capture_iface=eth0
packet_log="outputs/wired-dds-$(date -u +%Y%m%dT%H%M%SZ).pcap"
sudo tcpdump -i "$capture_iface" -s 0 -U -w "$packet_log" 'ip or ip6'
```

Capture both address families to detect an unexpected transport; domain-0 RTPS ports can vary with participant ID, so avoid assuming a single UDP port. Stop capture after the run and retain the dropped-packet count. For the historical failing writer `01060A02:145B0000:0B6E0001:00000902`, filter the source GUID prefix plus DATA writer entity ID, **not** the local reader GUID before RECEIVE FROM:

```bash
tshark -n -r "$packet_log" -Y 'ip && rtps && rtps.guidPrefix == 01:06:0a:02:14:5b:00:00:0b:6e:00:01 && rtps.sm.wrEntityId == 0x00000902' -T fields -e frame.number -e frame.time_epoch -e ip.src -e ip.dst -e rtps.guidPrefix -e rtps.sm.wrEntityId -e rtps.sm.seqNumber
```

This displays the captured network source IP for matching packets; it does not derive it from the GUID. For new runs use the newly logged RECEIVE FROM GUID, since writers may change on restart. In Wireshark inspect SPDP/SEDP announcements to map that full endpoint GUID to topic `DeviceInfo`, participant locators and process/host, then match its DATA/DATA_FRAG packets. Confirm `ip.src` against the sender's wired address and route. If INFO_SRC or a relay is involved, distinguish logical writer identity from packet forwarder; use discovery, endpoint tools and a sender-side capture to finish attribution. Check the sender process/service list before naming an owner.

With nonstandard ports use Decode As RTPS. No matching ethernet packet does not exclude local shared-memory traffic or loopback: the baseline also permits shared memory by default; supplement with `tcpdump -i any`, RTI Admin Console/local endpoint attribution and process inspection. A local Wi-Fi packet also does not satisfy the wired milestone. Capture application Heartbeat DATA, not just RTPS protocol HEARTBEAT submessages; RTPS writer sequence numbers are distinct from the application's `sequenceNumber`. See [RTI's GUID-filter instructions](https://community.rti.com/static/documentation/wireshark/2023-03/doc/debugging.html) and the [Wireshark RTPS field reference](https://www.wireshark.org/docs/dfref/r/rtps.html).

## Transfer this local change without pushing or merging

This checkout's work is uncommitted. A Pi `git pull` cannot retrieve it. After reviewing the laptop diff, create a targeted bundle from the laptop repository root:

```bash
tar -czf /tmp/forge-monitor-update.tar.gz controller_typev_interface_patched_v2.py README.md docs/architecture.md docs/dds-interface.md docs/dds-diagnostics.md docs/ipv6-migration.md docs/monitoring-validation.md docs/sprint-2-integration.md docs/tools.md docs/file-inventory.md tools/observe_requests.py tools/build_ipv6_config.py tests/test_monitoring.py tests/test_request_observer.py tests/test_ipv6_config.py
scp /tmp/forge-monitor-update.tar.gz forge@PI_HOST:/tmp/
```

Replace `PI_HOST` with the Pi's existing SSH address. This bundle does not contain `.venv`, `.git`, the baseline XML, archived code, logs, or simulator files.

On the Pi, stop any existing Type V instance using its normal terminal/service procedure. Verify the branch and review local changes before extracting; reconcile any Pi edits to bundle paths first. Do not overwrite unpreserved Pi work. From a Bash terminal:

```bash
cd ~/FORGE-IV-SS6
git branch --show-current
git status --short
test "$(git branch --show-current)" = 'ss6/sprint2-typei-link'
tar -tzf /tmp/forge-monitor-update.tar.gz
mkdir -p outputs
backup="outputs/pi-before-monitor-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
tar -czf "$backup" controller_typev_interface_patched_v2.py README.md docs
```

If `tools/` or `tests/` already exist on the Pi, include those directories in the backup before extraction. The archive is an additional backup, not conflict resolution. Once the target files are reconciled/backed up:

```bash
tar -xzf /tmp/forge-monitor-update.tar.gz
source ~/FORGE-IV-SS6/.venv/bin/activate
python -m unittest discover -s tests -v
```

No environment upgrade/reinstall is needed for this change. Supplied Pi runtime evidence: Python 3.10.12, Python Connector package 1.2.4, native NDDSCORE/NDDSC/RTICONNECTOR build 6.1.2.21 dated 2024-10-09. These are different version identifiers.

## Launch modes and full log capture

From `~/FORGE-IV-SS6`, monitoring with both stdout and stderr captured:

```bash
source ~/FORGE-IV-SS6/.venv/bin/activate
mkdir -p outputs
set -o pipefail
monitor_log="outputs/typev-monitor-$(date -u +%Y%m%dT%H%M%SZ).log"
python -u -X faulthandler controller_typev_interface_patched_v2.py Capstone/xml/tmg_xml_24_mar.xml --monitor-only 2>&1 | tee "$monitor_log"
```

The original command without flags now also monitors. Expect `[MODE] MONITOR ONLY` at startup and `Mode: MONITOR ONLY` in every status display. Suppressed requests print `[MONITOR] ... (not sent)` at most once per identical target/intention every 30 seconds; repeated attempts do not update pending/sent state or allocate command sequence IDs. Feeder `intended_action` is a decision, not proof of transmission.

Only when automatic control is intentionally wanted:

```bash
source ~/FORGE-IV-SS6/.venv/bin/activate
python -u -X faulthandler controller_typev_interface_patched_v2.py Capstone/xml/tmg_xml_24_mar.xml --enable-control
```

Diagnostic publication is unchanged: on changes to the computed diagnostic key, Type V sets only `ActiveDiagnosticState.deviceId=controller` and calls `write()`. It does not populate the XML `codes` or `overflow` fields from its printed faults. Monitoring is not a silent DDS participant; discovery, identity, heartbeat, diagnostics and protocol traffic remain.

## Independent observation and simulator test

Use the baseline transport first, independently of IPv6 migration. On a separate terminal with the Pi environment (or on another compatible Linux host), start the request observer **before Type V**:

```bash
cd ~/FORGE-IV-SS6
source ~/FORGE-IV-SS6/.venv/bin/activate
mkdir -p outputs
set -o pipefail
observer_log="outputs/request-observer-$(date -u +%Y%m%dT%H%M%SZ).log"
python -u tools/observe_requests.py Capstone/xml/tmg_xml_24_mar.xml --duration 300 2>&1 | tee "$observer_log"
```

The observer creates no application writers. Its configuration is generated from the selected XML, with compatible Command QoS and reader history depth 1024. It reports matched writer names, full samples, counts and final status. Reading errors mark the interval incomplete and exit; an empty count with no matches is **not** a pass. The baseline participant creates command endpoints even when monitoring blocks writes, so matching those endpoints should be possible.

1. Stop Type V and any other automatic controller. On the simulator desktop, use its existing `sim_start.sh`, select `src.json`, set source `ammps30` **OFF**, and verify OFF in the simulator. No feeder is expected. Record simulator version/configuration and current desktop transport; the title's IPv4 label is not a Type V transport setting.
2. Start the independent observer and a packet capture or Admin Console inspection as described below. Keep them running throughout the test. Start Type V with the monitoring capture command above.
3. Verify the observer matches `EnergyStartStopRequestWriter` and `PowerSwitchRequestWriter` as Type V starts; attribute them to this participant using start/stop correlation, endpoint GUIDs in Admin Console, or discovery packets. There should be no competing writer for the same command keys: the baseline uses exclusive ownership, which can mask weaker writers. Preserve the match records.
4. Verify Type V discovers `ammps30` and receives OFF. It may report suppressed OPERATIONAL intentions. Verify **zero `controller` source requests and zero `controller` feeder switch requests** over the recorded interval using the observer and packet/endpoint inspection, not just unchanged source state. Identity/heartbeat/diagnostic traffic is allowed. Any decode error, missing match, loss/drop indication, or observer overflow makes zero-command evidence inconclusive.
5. Manually change the simulator state, for example OFF to OPERATIONAL and back, using its UI/local simulator control. Verify Type V follows the received states and the observer remains free of Type V commands. Record timestamps, target ID, state values, and simulator transition actor/reason. This test establishes only the samples actually observed, not heartbeat timing or AC measurement delivery.
6. Stop Type V and preserve the controller log, complete observer interval, simulator log and capture. The observer should unmatch its writers. Do not mark the run successful if it ended with an exception or missed the test window.

Calibrate the independent inspection path with a **separate approved simulator-only** command exchange before relying on zero counts. A known source request and a known switch request must be visible with matching request/type/key/QoS, or use RTI Admin Console/RTPS endpoint inspection to validate each topic independently. Do not enable controller automation merely to calibrate an observer while equipment is attached. A source-only setup may not offer a switch-command calibration target; in that case record switch-topic absence as unproven until endpoint/packet inspection or an isolated fixture validates that path.

RTI Admin Console is an alternative/additional method if available: select domain 0 and the agreed transport, inspect the Type V participant's two named writers, confirm reader matches and incompatible-QoS status, subscribe to both request topics using matching type definitions and Command QoS, and record requester, target, sequence, and endpoint GUID. If Type V and observer share a host, DDS may use shared memory in the baseline: capture on the desktop/network path as well or inspect local DDS writer counters. Ethernet silence alone is insufficient. A healthy calibrated observer plus endpoint/packet evidence supports zero requests for the measured interval, not a universal absence claim.

The [observer API reference](https://community.rti.com/static/documentation/connector/1.2.2/api/python/input.html) documents matched publication reporting. Local tests validate config generation and fake-reader behavior; its real Connector 1.2.4 runtime remains to be tested on the Pi.

## Local validation result

The initial monitoring change passed 23 focused offline tests under the laptop's Python 3.10 inspection environment. Coverage includes both source-start paths, OFF/UNKNOWN, feeder OPEN/CLOSE, direct start/stop/switch helpers, failed writes, no false monitoring sent/pending state, identity/heartbeat/diagnostics, reception and state changes, CLI conflicts, contextual reader errors, observer config/count/error behavior, and IPv6 generation boundaries. CLI help and both config-generation paths were also exercised without importing a real RTI library. Static review resolved all 15 active endpoint topic/type/QoS references and 67 local Markdown links. The baseline XML matches its task-start SHA-256; unrelated original contents are unchanged. Pre-existing CRLF/whitespace differences against Git HEAD were preserved. No real controller/observer participant, equipment process, network configuration, push, merge, or dependency installation was run.

Pi/simulator acceptance, observer calibration and actual native Connector behavior, the unresolved middleware error reproduction, IPv6 participant creation and packet evidence, and Trevor's Type I integration are pending external tests. The supplied version query is evidence of successful library loading, not those runtime outcomes.

The heartbeat visibility patch adds regression coverage for two successive unregistered Type I heartbeats, self-heartbeat exclusion, continued heartbeat processing after a DeviceInfo conversion error, and unchanged feeder heartbeat tracking in both modes. These are offline fake-reader tests; the solo/paired wired IPv4 checks above still require the Pi, Trevor's live publisher and captures.

Local result for this patch: `python3 -m unittest discover -s tests -v` passes **27 tests**, including the four added heartbeat regressions and all existing IPv6 tests. No DDS participant or equipment process was launched. Baseline XML, optional IPv6 generator/tests, startup identity publication, keys, bounds, command guards and control thresholds are unchanged.

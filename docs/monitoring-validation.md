# Pi update, launch, and simulator acceptance

Monitoring defaults to receiving and displaying data while blocking the two application command writers. Identity, heartbeat, and existing diagnostic publication remain enabled. `--enable-control` deliberately restores the existing automatic decisions and thresholds. Conflicting mode flags fail argument parsing before RTI is imported.

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

All 23 focused offline tests pass under the laptop's Python 3.10 inspection environment. Coverage includes both source-start paths, OFF/UNKNOWN, feeder OPEN/CLOSE, direct start/stop/switch helpers, failed writes, no false monitoring sent/pending state, identity/heartbeat/diagnostics, reception and state changes, CLI conflicts, contextual reader errors, observer config/count/error behavior, and IPv6 generation boundaries. CLI help and both config-generation paths were also exercised without importing a real RTI library. Static review resolved all 15 active endpoint topic/type/QoS references and 67 local Markdown links. The baseline XML matches its task-start SHA-256; unrelated original contents are unchanged. Pre-existing CRLF/whitespace differences against Git HEAD were preserved. No real controller/observer participant, equipment process, network configuration, push, merge, or dependency installation was run.

Pi/simulator acceptance, observer calibration and actual native Connector behavior, the unresolved middleware error reproduction, IPv6 participant creation and packet evidence, and Trevor's Type I integration are pending external tests. The supplied version query is evidence of successful library loading, not those runtime outcomes.

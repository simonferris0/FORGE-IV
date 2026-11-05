# Existing diagnostics and test scripts

[Capstone/tms/tms_reader.py](../Capstone/tms/tms_reader.py) is the existing diagnostic DDS script. It gets reader endpoints and contains no application calls to writers. Its shared XML participant also defines writers, so this is not evidence that the participant itself creates only readers.

The script binds many inputs, but **only DeviceInfo, EnergyStartStopState, and Reply have active sample-reading blocks**. Heartbeat, AC measurement, and other receive blocks are commented out. It is not currently a complete heartbeat/measurement monitor. Broad exception handlers can label failures as missing samples.

It remains at its original path because `__file__ + /../xml/tmg_xml_24_mar.xml` resolves to the active XML there, and it appends a relative directory to `sys.path`. With the team's working environment active, its existing manual entry point from the repository root is `python Capstone/tms/tms_reader.py`. Running it joins DDS; it was not run during cleanup.

The new focused `unittest` suite runs with `python3 -m unittest discover -s tests -v` from the repository root. It imports no RTI package and uses fake endpoints. There is no package framework or shell launch script. Files called `controller-test*.py` are full procedural equipment controllers, not unit tests; `controller-test.py` includes automatic timed switch requests. They also truncate log files on startup. Do not invoke them as a validation suite.

[Archived test_script.py](../archive/environment/Capstone/tms/test_script.py) only appends text to `/home/michael/Desktop/result.txt`. It is an environment/file-I/O smoke script, with no DDS or controller checks, and has been kept unchanged as history.

Cleanup validation uses byte hashes/comparison, Python AST parsing without imports, XML parsing, local documentation link checks, and Git diff review. These do not exercise equipment, execute top-level script code, or establish runtime correctness.

## Independent request observer

[tools/observe_requests.py](../tools/observe_requests.py) builds a temporary participant containing only readers for `EnergyStartStopRequest` and `PowerSwitchRequest`. Types, domain, and QoS are taken from the selected baseline XML at each invocation; there is no committed duplicate schema. It preserves participant QoS (apart from identity user data) and has no DDS application writers. Discovery/acknowledgment metatraffic still occurs. Its reader history depth is 1024, while reliability, volatile durability, and exclusive ownership inherit the baseline Command profile. This observer-only buffering change does not modify the controller XML.

It logs compatible matched writer names, full received request dictionaries, per-topic totals and requester `controller` totals every five seconds, and a final summary. Read errors propagate and mark the interval incomplete. Names alone are not GUID attribution: correlate matches with the controller start/stop and use Admin Console or packet capture where necessary. Exclusive ownership, bounded history, loss, type mismatch, or disconnected transport can invalidate a zero count; follow the calibration/match requirements in the [acceptance procedure](monitoring-validation.md). Runtime validation of this tool remains pending.

Use `python tools/observe_requests.py Capstone/xml/tmg_xml_24_mar.xml --duration 120` only during the coordinated DDS test. To inspect its generated configuration without importing RTI or joining DDS, use `--write-config /tmp/forge-request-observer.xml`. The observer's matching APIs are documented in [RTI Connector 1.2.2 Input reference](https://community.rti.com/static/documentation/connector/1.2.2/api/python/input.html); confirm support in the installed build before interpreting results.

## Offline IPv6 configuration generator

[tools/build_ipv6_config.py](../tools/build_ipv6_config.py) composes `outputs/tmg_ipv6.xml` from the baseline without importing RTI. Native target is the reported 6.1.2.21 build; it changes only participant transport/discovery settings, and preserves all type definitions and endpoint QoS. Tests verify this boundary, input checks, and baseline-overwrite protection. See the [IPv6 runbook](ipv6-migration.md) for version-specific syntax sources, required actual addresses and runtime verification.

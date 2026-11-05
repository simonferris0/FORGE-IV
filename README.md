# FORGE-IV — SS6 Type V controller

SS6 coordinates microgrid source and feeder devices over RTI Connext DDS. The next prototype connects Type I source software to Type V for discovery and heartbeat exchange over an IPv6 network, then source state and AC measurements, and eventually a manually triggered command/reply exchange.

| Responsibility | Owner |
| --- | --- |
| SS6 / Type V controller | Jeffrey Sithong |
| Type I source / Chroma control software | Simon Ferris |
| Type I DDS communication / network integration | Trevor Patton |

## What to run and edit

- [controller_typev_interface_patched_v2.py](controller_typev_interface_patched_v2.py) is the current entry point, confirmed by [notes.txt](notes.txt). Monitoring is now the default; automatic control requires `--enable-control`.
- [Capstone/xml/tmg_xml_24_mar.xml](Capstone/xml/tmg_xml_24_mar.xml) is the current DDS type, topic, participant, and QoS contract. Coordinate future interface changes with Type I owners.
- [docs/architecture.md](docs/architecture.md) explains behavior and development families.
- [docs/dds-interface.md](docs/dds-interface.md) records the current interface and parser limitations.
- [docs/sprint-2-integration.md](docs/sprint-2-integration.md) describes the next separate implementation and integration steps.
- [docs/file-inventory.md](docs/file-inventory.md) maps every original file to its disposition, including historical code left in place for path dependencies.
- [docs/monitoring-validation.md](docs/monitoring-validation.md) gives Pi update/launch commands and the simulator acceptance test.
- [docs/dds-diagnostics.md](docs/dds-diagnostics.md) records confirmed XML findings and runtime evidence needed for the unresolved native errors.
- [docs/ipv6-migration.md](docs/ipv6-migration.md) separates host reachability, DDS transport configuration, and packet evidence.
- [docs/tools.md](docs/tools.md) describes the independent request observer, legacy reader, and offline tests.

## Setup and baseline launch

Use the existing known-working Linux environment. The existing virtual environment activation recorded in `notes.txt` is unchanged. From the repository root, launch monitoring explicitly:

```bash
source ~/FORGE-IV-SS6/.venv/bin/activate
python -u -X faulthandler controller_typev_interface_patched_v2.py Capstone/xml/tmg_xml_24_mar.xml --monitor-only
```

Omitting both mode flags also selects monitoring, so the original positional-XML launch now monitors. `--monitor-only` and `--enable-control` conflict and are rejected together. Monitoring continues discovery, all existing reception/state/measurement processing, status, controller identity/heartbeat, and the existing diagnostic publication. It blocks source start/stop and feeder switch writes, including direct command-helper calls. Suppressed intentions are reported at most once per identical intention every 30 seconds, with repeat counts on the next report. They do not consume command sequence IDs or update pending/sent switch state.

To deliberately enable the original automatic control decisions and thresholds:

```bash
source ~/FORGE-IV-SS6/.venv/bin/activate
python -u -X faulthandler controller_typev_interface_patched_v2.py Capstone/xml/tmg_xml_24_mar.xml --enable-control
```

Control mode can automatically request OPERATIONAL from OFF/UNKNOWN sources without a feeder and can switch a feeder. Neither mode was run against DDS or equipment during local validation. Diagnostic publication still sets only `ActiveDiagnosticState.deviceId=controller`, on changes of the internally computed diagnostic key; it does not publish the printed fault list as diagnostic codes.

The external Python dependency evidenced by the code is **RTI Connext DDS Connector**, imported as `rticonnextdds_connector`. Other imports use the Python standard library, including `dataclasses`. No dependency manifest, pinned Connector/Python version, or reproducible installation procedure was found. The XML's schema reference is not evidence of the installed Connector version.

For a new machine, create a local virtual environment (for example `python3 -m venv .venv` and `source .venv/bin/activate`) and provision RTI Connext DDS Connector following the team's working RTI environment and platform instructions. That environment creation is setup guidance, not a verified replacement for the recorded environment. No packages were installed during cleanup, and no requirements file was inferred from the local machine.

Always pass the XML argument shown above. The active file's fallback is `../xml/tmg_xml_24_mar.xml` relative to the script, which does not resolve to this checkout's current XML.

## Current limitations

Sources are discovered through `DeviceInfo`, with source state and AC measurements consumed for discovered IDs. Heartbeat freshness is currently tracked for the feeder only. Unexpected Python reader errors now report reader/topic/operation context on stderr with a 30-second repeat limit; normal wait timeouts and empty reads stay quiet. Native RTI errors may bypass Python exception handling and remain visible on stderr. The reply parser still differs from the XML's top-level fields. The baseline XML, archived code, and measurement logs were preserved.

IPv6 host reachability and DDS communication require separate checks. This checkout does not establish IPv6-only DDS transport configuration or successful Type I interoperability.

## Layout

```text
controller_typev_interface_patched_v2.py   active controller, monitoring by default
Capstone/xml/tmg_xml_24_mar.xml           active DDS contract, unchanged
Capstone/tms/tms_reader.py                diagnostic script, path retained
controller*.py / Capstone/tms/controller*.py
                                         historical procedural files left for fixed paths
notes.txt                                historical launch note (now defaults to monitoring)
README.md / docs/                        current guidance and historical summaries
archive/typev-interface/                 inactive TypeVControllerInterface variants
archive/feeder-command/                  separate feeder command experiments
archive/environment/                     historical file-I/O smoke script
*.txt / Capstone/tms/*.txt                preserved measurement logs
```

Archived Python files retain their bytes and original-path suffixes. They are historical references, not validated launch alternatives. See [archive/README.md](archive/README.md) before using them. Historical summaries are preserved verbatim in [docs/history](docs/history/README.md); current guidance corrects several claims in those summaries.

Run the focused offline tests from the repository root without RTI:

```bash
python3 -m unittest discover -s tests -v
```

The observed `ammps30` simulator OPERATIONAL/RemoteControl/actor-controller state is consistent with an earlier automatic request round trip. It does not establish heartbeat timing, measurements, reliable interoperability, or IPv6-only DDS. No `sim_start.sh` or `src.json` is present in this checkout. The Pi reports Connector package 1.2.4 with native middleware build 6.1.2.21. A separate offline IPv6 configuration generator is prepared for that native version; no profile was activated. Actual interface/peer addresses, OS/architecture, simulator transport configuration and runtime traffic evidence remain needed.

Prepare a separate IPv6 configuration using [tools/build_ipv6_config.py](tools/build_ipv6_config.py), after selecting actual interfaces/peers as described in the IPv6 runbook. This reads the baseline types afresh and does not modify the baseline XML or host networking.

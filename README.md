# FORGE-IV — SS6 Type V controller

SS6 coordinates microgrid source and feeder devices over RTI Connext DDS. The next prototype connects Type I source software to Type V for discovery and heartbeat exchange over an IPv6 network, then source state and AC measurements, and eventually a manually triggered command/reply exchange.

| Responsibility | Owner |
| --- | --- |
| SS6 / Type V controller | Jeffrey Sithong |
| Type I source / Chroma control software | Simon Ferris |
| Type I DDS communication / network integration | Trevor Patton |

## What to run and edit

- [controller_typev_interface_patched_v2.py](controller_typev_interface_patched_v2.py) is the current entry point, confirmed by [notes.txt](notes.txt). Future Type V implementation belongs here, under a separate change.
- [Capstone/xml/tmg_xml_24_mar.xml](Capstone/xml/tmg_xml_24_mar.xml) is the current DDS type, topic, participant, and QoS contract. Coordinate future interface changes with Type I owners.
- [docs/architecture.md](docs/architecture.md) explains behavior and development families.
- [docs/dds-interface.md](docs/dds-interface.md) records the current interface and parser limitations.
- [docs/sprint-2-integration.md](docs/sprint-2-integration.md) describes the next separate implementation and integration steps.
- [docs/file-inventory.md](docs/file-inventory.md) maps every original file to its disposition, including historical code left in place for path dependencies.
- [docs/tools.md](docs/tools.md) describes the existing DDS diagnostic reader and the limits of scripts named “test”.

## Setup and baseline launch

Use the existing known-working Linux environment. The setup and launch recorded in `notes.txt` are, from the repository root:

```bash
source ~/FORGE-IV-SS6/.venv/bin/activate
python -u -X faulthandler controller_typev_interface_patched_v2.py Capstone/xml/tmg_xml_24_mar.xml
```

This is an equipment-control launch command. The current controller can send automatic source and feeder requests; monitoring-only mode has **not** been implemented by this cleanup.

The external Python dependency evidenced by the code is **RTI Connext DDS Connector**, imported as `rticonnextdds_connector`. Other imports use the Python standard library, including `dataclasses`. No dependency manifest, pinned Connector/Python version, or reproducible installation procedure was found. The XML's schema reference is not evidence of the installed Connector version.

For a new machine, create a local virtual environment (for example `python3 -m venv .venv` and `source .venv/bin/activate`) and provision RTI Connext DDS Connector following the team's working RTI environment and platform instructions. That environment creation is setup guidance, not a verified replacement for the recorded environment. No packages were installed during cleanup, and no requirements file was inferred from the local machine.

Always pass the XML argument shown above. The active file's fallback is `../xml/tmg_xml_24_mar.xml` relative to the script, which does not resolve to this checkout's current XML.

## Current limitations

Sources are already discovered through `DeviceInfo`, with source state and AC measurements consumed for discovered IDs. Heartbeat freshness is currently tracked for the feeder only. The generation manager can request `ESSL_OPERATIONAL` for sources marked OFF or UNKNOWN even without a feeder. Feeder switching is also automatic. Reader exceptions are suppressed, and the reply parser differs from the XML's top-level reply fields. These findings are documented for future work; executable code and XML were preserved.

IPv6 host reachability and DDS communication require separate checks. This checkout does not establish IPv6-only DDS transport configuration or successful Type I interoperability.

## Layout

```text
controller_typev_interface_patched_v2.py   active controller, unchanged
Capstone/xml/tmg_xml_24_mar.xml           active DDS contract, unchanged
Capstone/tms/tms_reader.py                diagnostic script, path retained
controller*.py / Capstone/tms/controller*.py
                                         historical procedural files left for fixed paths
notes.txt                                original launch note
README.md / docs/                        current guidance and historical summaries
archive/typev-interface/                 inactive TypeVControllerInterface variants
archive/feeder-command/                  separate feeder command experiments
archive/environment/                     historical file-I/O smoke script
*.txt / Capstone/tms/*.txt                preserved measurement logs
```

Archived Python files retain their bytes and original-path suffixes. They are historical references, not validated launch alternatives. See [archive/README.md](archive/README.md) before using them. Historical summaries are preserved verbatim in [docs/history](docs/history/README.md); current guidance corrects several claims in those summaries.

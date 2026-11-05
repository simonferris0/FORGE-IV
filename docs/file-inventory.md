# File inventory and cleanup evidence

This inventory records the earlier cleanup snapshot. Its hashes and preservation claims apply to that operation. The subsequent monitoring change intentionally edits the active controller and current Markdown guides, and adds `tests/test_monitoring.py`, `tests/test_request_observer.py`, `tools/observe_requests.py`, `tools/build_ipv6_config.py`, `tests/test_ipv6_config.py`, and the monitoring, DDS diagnostic, and IPv6 runbooks. The baseline XML, historical scripts/summaries, and measurement logs remain unchanged by the monitoring work.

Cleanup was performed on `ss6/sprint2-typei-link`. The starting working tree had 21 modified tracked files, including the active controller, XML, code variants, summaries, and a measurement log. No applicable `AGENTS.md` was found in the checkout or its ancestor directories. No branch switch, dependency installation, controller execution, commit, push, or merge was performed.

All original tracked file contents were snapshotted before changes. Every original file is retained byte-for-byte, either at its original path or the destination below. There were **no Python deletions or code edits**, including duplicate copies. Git will show removals at old paths and untracked archive additions until staged; these are documented moves, not discarded code. The existing index was not staged or reset.

## Complete original-file disposition

| Original path | Current location | Purpose and disposition |
| --- | --- | --- |
| `Capstone/summary.txt` | [docs/history/capstone-summary.txt](../docs/history/capstone-summary.txt) | Verbatim cross-directory version comparison archived as documentation. |
| `Capstone/tms/Generator_Information_24_Hours.txt` | [Capstone/tms/Generator_Information_24_Hours.txt](../Capstone/tms/Generator_Information_24_Hours.txt) | Preserved historical generator state/fuel log; 0 bytes at cleanup start. Kept in original location, including empty baseline artifacts. |
| `Capstone/tms/Generator_fuel_ups.txt` | [Capstone/tms/Generator_fuel_ups.txt](../Capstone/tms/Generator_fuel_ups.txt) | Preserved historical refuel-event log; 0 bytes at cleanup start. Kept in original location, including empty baseline artifacts. |
| `Capstone/tms/Total_Real_Delivered_Combined.txt` | [Capstone/tms/Total_Real_Delivered_Combined.txt](../Capstone/tms/Total_Real_Delivered_Combined.txt) | Preserved historical combined real-power measurement log; 11,796 bytes at cleanup start. Kept in original location, including empty baseline artifacts. |
| `Capstone/tms/controller-test.py` | [Capstone/tms/controller-test.py](../Capstone/tms/controller-test.py) | Historical procedural feeder extension duplicate; fixed ../xml path currently resolves. Kept unchanged with its log layout. |
| `Capstone/tms/controller.py` | [Capstone/tms/controller.py](../Capstone/tms/controller.py) | Historical procedural baseline duplicate; fixed ../xml path currently resolves. Kept unchanged with its log layout. |
| `Capstone/tms/controller_typev_feeder_driven.py` | [archive/feeder-command/Capstone/tms/controller_typev_feeder_driven.py](../archive/feeder-command/Capstone/tms/controller_typev_feeder_driven.py) | Archived separate MicrogridController experiment; PendingCommand, command timeouts, argparse. |
| `Capstone/tms/controller_typev_interface_patched.py` | [archive/typev-interface/Capstone/tms/controller_typev_interface_patched.py](../archive/typev-interface/Capstone/tms/controller_typev_interface_patched.py) | Archived OO interface patch duplicate, original Capstone/tms provenance preserved. |
| `Capstone/tms/controller_typev_single_feeder_patched.py` | [archive/feeder-command/Capstone/tms/controller_typev_single_feeder_patched.py](../archive/feeder-command/Capstone/tms/controller_typev_single_feeder_patched.py) | Archived separate TypeVController experiment; first_present, feeder locking, pending command gating. |
| `Capstone/tms/summary.txt` | [docs/history/tms-summary.txt](../docs/history/tms-summary.txt) | Verbatim TMS controller/tool summary archived as documentation. |
| `Capstone/tms/test_script.py` | [archive/environment/Capstone/tms/test_script.py](../archive/environment/Capstone/tms/test_script.py) | Archived environment smoke script; appends to hardcoded /home/michael/Desktop/result.txt, not a controller test. |
| `Capstone/tms/tms_reader.py` | [Capstone/tms/tms_reader.py](../Capstone/tms/tms_reader.py) | Diagnostic DDS reader kept for fixed ../xml and sys.path dependencies; only three receive blocks active. See tools guide. |
| `Capstone/xml/tmg_xml_24_mar.xml` | [Capstone/xml/tmg_xml_24_mar.xml](../Capstone/xml/tmg_xml_24_mar.xml) | ACTIVE. DDS types/topics/participant/QoS; explicit launch XML. Path and bytes retained. |
| `Generator_Information_24_Hours.txt` | [Generator_Information_24_Hours.txt](../Generator_Information_24_Hours.txt) | Preserved historical generator state/fuel log; 0 bytes at cleanup start. Kept in original location, including empty baseline artifacts. |
| `Generator_fuel_ups.txt` | [Generator_fuel_ups.txt](../Generator_fuel_ups.txt) | Preserved historical refuel-event log; 0 bytes at cleanup start. Kept in original location, including empty baseline artifacts. |
| `Total_Real_Delivered_Combined.txt` | [Total_Real_Delivered_Combined.txt](../Total_Real_Delivered_Combined.txt) | Preserved historical combined real-power measurement log; 0 bytes at cleanup start. Kept in original location, including empty baseline artifacts. |
| `controller-test-patched (1).py` | [controller-test-patched (1).py](../controller-test-patched%20%281%29.py) | Historical procedural role normalization/feeder registration helpers; timed test commands commented out. Kept for fixed XML/path assumptions. |
| `controller-test-patched-v2.py` | [controller-test-patched-v2.py](../controller-test-patched-v2.py) | Historical procedural feeder ID filtering and broader read guard; timed test commands commented out. Kept for fixed XML/path assumptions. |
| `controller-test.py` | [controller-test.py](../controller-test.py) | Historical procedural feeder extension; live timed switch commands. Kept for fixed XML/path assumptions; exact duplicate of Capstone/tms copy. |
| `controller.py` | [controller.py](../controller.py) | Historical procedural baseline; two-source decisions and fuel/power logs. Kept for fixed XML/path assumptions; exact duplicate of Capstone/tms copy. |
| `controller_typev_interface.py` | [archive/typev-interface/root/controller_typev_interface.py](../archive/typev-interface/root/controller_typev_interface.py) | Archived OO interface baseline; source/feeder diagnostics, string source role. |
| `controller_typev_interface_patched.py` | [archive/typev-interface/root/controller_typev_interface_patched.py](../archive/typev-interface/root/controller_typev_interface_patched.py) | Archived OO interface numeric source role patch; duplicate of original Capstone/tms copy. |
| `controller_typev_interface_patched_v2.py` | [controller_typev_interface_patched_v2.py](../controller_typev_interface_patched_v2.py) | ACTIVE. Documented entry point; source/feeder control plus load/storage discovery. Path and bytes retained. |
| `controller_typev_interface_phase_display.py` | [archive/typev-interface/root/controller_typev_interface_phase_display.py](../archive/typev-interface/root/controller_typev_interface_phase_display.py) | Archived OO sibling; phase telemetry and OPEN confirmation differences, loses multi-device tracking. Not a strict upgrade. |
| `notes.txt` | [notes.txt](../notes.txt) | Original environment activation and active launch note; unchanged. |
| `summary.txt` | [docs/history/root-summary.txt](../docs/history/root-summary.txt) | Verbatim root family/version summary archived as documentation; historical claims corrected by current guides. |

## Move and preservation hashes

SHA-256 below describes the **starting working-tree bytes**, not HEAD. These same bytes must be present at each destination. Archived OO controllers accept an explicit XML argument. Their original fallback XML and sys.path assumptions are preserved but change meaning in the archive; restore the original layout if external dependencies require it. Scripts with fixed relative XML paths and no override were left in place. No repository Python imports/callers of moved controllers were found; known documentation references are mapped above and historical prose is explicitly labeled.

| Original path | SHA-256 (also verified at destination) |
| --- | --- |
| `controller_typev_interface_patched_v2.py` | `c8ce56875e8fe23635b3fef6fda40980173038fc617b6f122a68b3d1274a66ce` |
| `Capstone/xml/tmg_xml_24_mar.xml` | `aae3cdf8799adc10276029096a6d83eb99dfd304150d8546846c5a2fa5fb8e82` |
| `controller_typev_interface.py` | `967d69bc59d17e0bdbd4f931bbe5868f03a7e42ab78462973a7f260317236598` |
| `controller_typev_interface_patched.py` | `7031e5082e6307acbfd97c15a56daa9554e3b58de513126723a2eae7b85ea9be` |
| `controller_typev_interface_phase_display.py` | `f0526604e7e8ad02996bb4ccb8c9d9160fb4aeed4325c61b84b944f68931d76f` |
| `Capstone/tms/controller_typev_interface_patched.py` | `7031e5082e6307acbfd97c15a56daa9554e3b58de513126723a2eae7b85ea9be` |
| `Capstone/tms/controller_typev_feeder_driven.py` | `cae69ae21158299c4f2f02c4e744622025e8970d28e233af7fbb37d9980e3a28` |
| `Capstone/tms/controller_typev_single_feeder_patched.py` | `e3c739032619953abd81571d8e47d1a834bdd8b4b430dcb432fb3144e7bd219f` |
| `Capstone/tms/test_script.py` | `e4b12126f11136418cf4273f0619e51e0e710c5d7643c91b2ceeaecb92b07e24` |
| `summary.txt` | `bf11805c7c42982bfa5111f56c6a8f21ca99bdbd8f0ecec2b4055deca73e0548` |
| `Capstone/summary.txt` | `912e1da5f58cf110e24adefa5891cec4e20a667f8727ecf34ffb5a6b0f423be2` |
| `Capstone/tms/summary.txt` | `5fdb9ce6766307068588d374a29e980a76af1a0e6b4415dc93d25b5be255eb37` |

## Exact duplicate evidence

SHA-256 grouping and byte comparison confirmed the following pairs before moving. All copies remain: identical content does not erase their original layout/provenance.

| Original pair | Shared SHA-256 |
| --- | --- |
| `controller.py` = `Capstone/tms/controller.py` | `723ddeecbb0370501ed35d9325841c496a970983bd7b239a753ab7ed0a4fd95c` |
| `controller-test.py` = `Capstone/tms/controller-test.py` | `eddc79d190525c2b6eb3c8f0baebe30710be4dcd3547b0a924e13112cae30b89` |
| `controller_typev_interface_patched.py` = `Capstone/tms/controller_typev_interface_patched.py` | `7031e5082e6307acbfd97c15a56daa9554e3b58de513126723a2eae7b85ea9be` |

## New guidance and validation

New files are the root README and .gitignore; architecture, DDS interface, Sprint 2 integration, tooling and this inventory under docs; a historical-summary index; and the archive index. Ignore rules cover local virtual environments, Python/tool caches, and dedicated scratch output directories, without broad exclusions for measurement .txt files.

Static validation checks all original bytes at their current destinations, the two documented launch paths, Python AST syntax without importing scripts, XML well-formedness, and local Markdown link targets. Git diff review includes untracked documentation/archive files. This does not validate RTI installation, external dependencies, DDS semantics, network reachability, transport choice, or equipment behavior. The recorded external virtual environment has not been verified on this machine.

Validation result: all 26 original files match their starting bytes, all 10 moves are accounted for, all 15 Python files parse as ASTs, the XML parses, and all 50 local Markdown links resolve. `git diff --check` reports pre-existing CRLF/trailing-whitespace diagnostics against HEAD; retained tracked diffs disappear when ignoring end-of-line whitespace. These bytes were deliberately preserved. Newly written documentation/configuration has no trailing whitespace.

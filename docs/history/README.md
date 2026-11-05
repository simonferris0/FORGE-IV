# Preserved setup and version history

The three summaries were moved verbatim, including pre-existing edits and line endings. They record earlier understanding, not the current runbook. Their old relative references and original filenames describe the pre-cleanup layout; use the [inventory](../file-inventory.md) to locate those files now.

| Preserved document | Original path |
| --- | --- |
| [Root summary](root-summary.txt) | `summary.txt` |
| [Capstone comparison](capstone-summary.txt) | `Capstone/summary.txt` |
| [TMS summary](tms-summary.txt) | `Capstone/tms/summary.txt` |

The original [notes.txt](../../notes.txt) remains at the root and records the active launch command.

Corrections from current content comparison:

- Phase_display is a sibling with useful phase display and OPEN-confirmation differences; it removes patched_v2 device tracking and is not a strict upgrade. Its CLOSE confirmation stays voltage-based.
- Root OO controllers accept an XML argument; the documented explicit path is necessary for the active root launch. Procedural files have fixed relative XML paths. The summaries' blanket statement about all paths is incomplete.
- Current `controller-test.py` has live iteration-50/100 switch commands. In both later procedural patched variants these particular test requests are commented out, including patched (1).
- The DDS reader binds many inputs, but only DeviceInfo, EnergyStartStopState, and Reply read blocks are currently enabled.
- Labels such as “most polished”, “production candidate”, or “production” in the summaries are historical opinions, not runtime qualification or authority to replace patched_v2. The separate families have useful differences.
- The three claimed duplicate pairs were verified against current bytes; all copies have been retained. See inventory hashes.

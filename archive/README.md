# Historical Python variants

All archived files were moved byte-for-byte from the dirty working tree. No Python file was deleted or edited. Original-path suffixes (`root/` or `Capstone/tms/`) distinguish provenance and exact duplicate copies.

- `typev-interface/`: inactive `TypeVControllerInterface` development line; active patched_v2 remains at the repository root.
- `feeder-command/`: separate `MicrogridController` / `TypeVController` command-lifecycle experiments.
- `environment/`: historical hardcoded file-I/O smoke script.

See the [file inventory](../docs/file-inventory.md) for every old/new path and purpose, and [architecture](../docs/architecture.md) for substantive variant differences.

These are historical references, not validated launch alternatives. OO controllers accept an explicit XML argument, but their unchanged fallback XML and `sys.path` calculations depend on their original layout. Archived files may require restoration to that layout to run with external dependencies. No dependency installation or archived-controller execution was performed. The file-I/O smoke script still targets its original absolute path.

The procedural family remains in its original locations because its XML path is hardcoded with no override; the diagnostic reader is similarly retained. There are no empty archive-family placeholders.

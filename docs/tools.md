# Existing diagnostics and test scripts

[Capstone/tms/tms_reader.py](../Capstone/tms/tms_reader.py) is the existing diagnostic DDS script. It gets reader endpoints and contains no application calls to writers. Its shared XML participant also defines writers, so this is not evidence that the participant itself creates only readers.

The script binds many inputs, but **only DeviceInfo, EnergyStartStopState, and Reply have active sample-reading blocks**. Heartbeat, AC measurement, and other receive blocks are commented out. It is not currently a complete heartbeat/measurement monitor. Broad exception handlers can label failures as missing samples.

It remains at its original path because `__file__ + /../xml/tmg_xml_24_mar.xml` resolves to the active XML there, and it appends a relative directory to `sys.path`. With the team's working environment active, its existing manual entry point from the repository root is `python Capstone/tms/tms_reader.py`. Running it joins DDS; it was not run during cleanup.

There is no discovered automated test suite, test runner configuration, packaging framework, or shell launch script. Files called `controller-test*.py` are full procedural equipment controllers, not unit tests; `controller-test.py` includes automatic timed switch requests. They also truncate log files on startup. Do not invoke them as a validation suite.

[Archived test_script.py](../archive/environment/Capstone/tms/test_script.py) only appends text to `/home/michael/Desktop/result.txt`. It is an environment/file-I/O smoke script, with no DDS or controller checks, and has been kept unchanged as history.

Cleanup validation uses byte hashes/comparison, Python AST parsing without imports, XML parsing, local documentation link checks, and Git diff review. These do not exercise equipment, execute top-level script code, or establish runtime correctness.

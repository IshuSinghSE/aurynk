## 2026-03-04 - [Batch ADB shell commands]
**Learning:** Making multiple separate `adb shell` calls incurs significant per-call connection overhead, which slows down device discovery and querying.
**Action:** When querying multiple properties or states from an Android device, batch the commands into a single `adb shell` execution using a delimiter (e.g., `cmd1; echo '---SEP---'; cmd2`) and parse the resulting single stdout.

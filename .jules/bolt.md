## 2024-05-24 - Batched ADB Shell Commands
**Learning:** Running individual `adb shell` commands for each device property has significant overhead due to starting a new subprocess and establishing an ADB connection.
**Action:** Always batch multiple ADB shell commands using a safe delimiter (e.g., `_AURYNK_DELIM_`) to fetch all needed information in a single round trip, significantly improving performance when reading multiple properties or specs.

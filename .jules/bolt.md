## 2024-05-24 - Cache `adb devices` calls for `is_device_connected`
**Learning:** Checking device connectivity in UI loops or fast periodic background tasks via `subprocess.run(["adb", "devices"])` is highly inefficient and can cause significant UI blocking and jank. The cost per call is in the 50-100ms range or more.
**Action:** Always implement a short TTL cache (e.g., 1s) when determining the status of connected devices. Only query `adb` when the cache expires to return connected serials, avoiding thousands of unnecessary subprocess creations per minute.

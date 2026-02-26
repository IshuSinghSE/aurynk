# Bolt's Journal

## 2026-02-26 - [ADB Command Batching]
**Learning:** `subprocess.run` overhead adds up quickly in Python.
**Action:** Always batch sequential ADB commands using delimiters (`; echo DELIMITER;`) when possible, especially for properties retrieval.

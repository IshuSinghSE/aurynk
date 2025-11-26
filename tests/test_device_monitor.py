from aurynk.services.device_monitor import DeviceMonitor


def test_device_monitor_add_remove():
    monitor = DeviceMonitor()
    device = {"address": "test:5555", "name": "Test Device"}
    monitor.set_paired_devices([device])
    assert device["address"] in monitor._paired_devices
    monitor.remove_device(device["address"])
    assert device["address"] not in monitor._paired_devices

# aurynk/device_events.py
_callbacks = []

def register_device_change_callback(cb):
    if cb not in _callbacks:
        _callbacks.append(cb)

def unregister_device_change_callback(cb):
    if cb in _callbacks:
        _callbacks.remove(cb)

def notify_device_changed():
    for cb in _callbacks:
        cb()

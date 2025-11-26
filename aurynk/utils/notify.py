from typing import Optional

_inited = False


def notify_device_event(event: str, device: str = "", extra: str = "", error: bool = False):
    """
    Central notification handler for device events.
    event: 'connected', 'disconnected', 'error', etc.
    device: device name or address
    extra: additional info (e.g. error message)
    error: if True, treat as error notification
    """
    from aurynk.utils.settings import SettingsManager

    settings = SettingsManager()
    if not settings.get("app", "show_notifications", True):
        return
    if event == "connected":
        show_notification(title="Device Connected", body=f"{device} is now connected.")
    elif event == "disconnected":
        show_notification(title="Device Disconnected", body=f"{device} is now disconnected.")
    elif event == "error":
        show_notification(title="Device Error", body=f"{device}: {extra}", icon=None)
    else:
        show_notification(title="Device Event", body=f"{event}: {device} {extra}")


def _ensure_init(app_id: str) -> bool:
    global _inited
    if _inited:
        return True
    try:
        from gi.repository import gi

        gi.require_version("Notify", "0.7")
        from gi.repository import Notify

        Notify.init(app_id)
        _inited = True
        return True
    except Exception:
        return False


def show_notification(
    title: str,
    body: str = "",
    icon: Optional[str] = None,
    app_id: str = "io.github.IshuSinghSE.aurynk",
) -> None:
    if not _ensure_init(app_id):
        return
    try:
        from gi.repository import Notify

        n = Notify.Notification.new(title, body, icon)
        n.show()
    except Exception:
        return

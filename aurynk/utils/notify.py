from typing import Optional

from aurynk.utils.logger import get_logger

logger = get_logger("Notify")

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
        logger.info("Notifications are disabled in settings.")
        return
    try:
        if event == "connected":
            show_notification(
                title=_("Device Connected"), body=_("{} is now connected.").format(device)
            )
        elif event == "disconnected":
            show_notification(
                title=_("Device Disconnected"), body=_("{} is now disconnected.").format(device)
            )
        elif event == "error":
            show_notification(
                title=_("Device Error"), body=_("{}: {}").format(device, extra), icon=None
            )
        else:
            show_notification(title=_("Device Event"), body=f"{event}: {device} {extra}")
    except Exception as e:
        logger.error(f"Exception in notify_device_event: {e}")


def _ensure_init(app_id: str) -> bool:
    global _inited
    if _inited:
        return True
    try:
        import gi

        gi.require_version("Notify", "0.7")
        from gi.repository import Notify

        Notify.init(app_id)
        _inited = True
        return True
    except Exception as e:
        logger.error(f"Exception in _ensure_init: {e}")
        return False


def show_notification(
    title: str,
    body: str = "",
    icon: Optional[str] = None,
    app_id: str = "io.github.IshuSinghSE.aurynk",
) -> None:
    if not _ensure_init(app_id):
        logger.error("_ensure_init failed, notification not shown.")
        # Fallback: print to stderr for CLI users
        import sys

        print(f"[Notification] {title}: {body}", file=sys.stderr)
        return
    try:
        from gi.repository import Notify

        n = Notify.Notification.new(title, body, icon)
        n.show()
    except Exception as e:
        logger.error(f"Exception in show_notification: {e}")
        # Fallback: print to stderr for CLI users
        import sys

        print(f"[Notification] {title}: {body}", file=sys.stderr)
        return

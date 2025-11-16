from typing import Optional

_inited = False


def _ensure_init(app_id: str) -> bool:
    global _inited
    if _inited:
        return True
    try:
        from gi.repository import Notify
        Notify.init(app_id)
        _inited = True
        return True
    except Exception:
        return False


def show_notification(title: str, body: str = "", icon: Optional[str] = None, app_id: str = "io.github.IshuSinghSE.aurynk") -> None:
    if not _ensure_init(app_id):
        return
    try:
        from gi.repository import Notify
        n = Notify.Notification.new(title, body, icon)
        n.show()
    except Exception:
        return

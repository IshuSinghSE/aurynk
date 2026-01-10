"""Utility for managing encoder settings across device changes."""

from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

logger = get_logger("EncoderManager")


def reset_encoders_to_default():
    """Reset video and audio encoder settings to default (empty strings).

    This should be called when devices are paired/unpaired/changed to ensure
    encoder settings don't persist across different devices.
    """
    try:
        settings = SettingsManager()

        # Get current values
        current_video = settings.get("scrcpy", "video_encoder", "")
        current_audio = settings.get("scrcpy", "audio_encoder", "")

        # Only reset if there are custom encoders set
        if current_video or current_audio:
            logger.info("Resetting encoders to default due to device change")
            settings.set("scrcpy", "video_encoder", "")
            settings.set("scrcpy", "audio_encoder", "")
            logger.debug(f"Cleared encoders: video='{current_video}', audio='{current_audio}'")

    except Exception as e:
        logger.error(f"Failed to reset encoders: {e}")

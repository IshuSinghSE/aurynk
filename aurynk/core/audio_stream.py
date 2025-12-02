import subprocess
from typing import List


class AudioStreamManager:
    """Manages PipeWire audio streams using pactl.

    This class handles the creation and destruction of PipeWire modules
    required to stream audio via TCP.
    """

    def __init__(self) -> None:
        """Initializes the AudioStreamManager."""
        self._module_ids: List[str] = []

    def start_stream(self, port: int) -> None:
        """Starts the audio stream on the specified port.

        This loads a null-sink module and a simple-protocol-tcp module
        configured to playback into that sink.

        Args:
            port: The TCP port to listen on.

        Raises:
            subprocess.CalledProcessError: If pactl fails.
        """
        sink_name = f"aurynk_audio_{port}"

        # Load module-null-sink
        cmd_sink = [
            "pactl",
            "load-module",
            "module-null-sink",
            f"sink_name={sink_name}",
            f"sink_properties=device.description=AurynkAudio_{port}",
        ]
        module_id_sink = subprocess.check_output(cmd_sink).decode("utf-8").strip()
        self._module_ids.append(module_id_sink)

        # Load module-simple-protocol-tcp
        # We assume playback=true (receiving audio from port) into the sink we just created.
        cmd_tcp = [
            "pactl",
            "load-module",
            "module-simple-protocol-tcp",
            f"port={port}",
            "playback=true",
            f"sink={sink_name}",
        ]
        module_id_tcp = subprocess.check_output(cmd_tcp).decode("utf-8").strip()
        self._module_ids.append(module_id_tcp)

    def stop_stream(self) -> None:
        """Stops the audio stream by unloading loaded modules.

        Unloads modules in reverse order of loading.
        """
        # Iterate in reverse to unload
        while self._module_ids:
            module_id = self._module_ids.pop()
            subprocess.run(
                ["pactl", "unload-module", module_id],
                check=False,  # We don't want to crash if unload fails, just try the next one
            )

import logging
import socket
import ssl
import subprocess
from typing import Optional


def create_ssl_context(
    cafile: Optional[str] = None,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
    verify: bool = True,
):
    """
    Create and return a configured SSLContext for use by AudioSender.

    - Enforces TLS 1.2+ when supported (sets minimum_version where available)
    - Disables TLSv1 and TLSv1.1 via context.options
    - Loads cert/key and cafile when provided
    - If verify=True, sets CERT_REQUIRED and enables hostname checking
      (uses system CAs when cafile is None). If verify=False, sets
      CERT_NONE (insecure) for compatibility/testing.
    """
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH if cafile else ssl.Purpose.CLIENT_AUTH
    )
    # Prefer setting a minimum version (Python 3.7+). Prefer TLSv1.3 when
    # available, otherwise fall back to TLSv1.2. Only use the deprecated
    # OP_NO_TLS* flags when `minimum_version` is not supported.
    if hasattr(ssl, "TLSVersion") and hasattr(context, "minimum_version"):
        try:
            if hasattr(ssl.TLSVersion, "TLSv1_3"):
                context.minimum_version = ssl.TLSVersion.TLSv1_3
            else:
                context.minimum_version = ssl.TLSVersion.TLSv1_2
        except Exception:
            # If setting minimum_version fails, fall back to disabling older
            # TLS versions via options for compatibility.
            context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    else:
        # Older Python/OpenSSL: disable TLSv1 and TLSv1.1 using options
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

    if certfile and keyfile:
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    if verify:
        if cafile:
            context.load_verify_locations(cafile=cafile)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
    else:
        if cafile:
            context.load_verify_locations(cafile=cafile)
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
    return context


class AudioSender:
    """
    Manages desktop audio streaming over TCP or TLS.
    """

    def __init__(self, device: Optional[str] = None):
        self.device = device or "default"
        self.buffer_size = 1024
        self.proc = None
        self.sock = None

    def _get_ffmpeg_cmd(self):
        return [
            "ffmpeg",
            "-f",
            "pulse",
            "-i",
            self.device,
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-loglevel",
            "error",
            "-",
        ]

    def stream_tcp(self, host: str, port: int):
        """
        Stream audio over plain TCP.
        """
        self._stream(host, port, use_tls=False)

    def stream_tls(
        self,
        host: str,
        port: int,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        cafile: Optional[str] = None,
        verify: bool = True,
    ):
        """
        Stream audio over TLS.
        """
        self._stream(
            host,
            port,
            use_tls=True,
            certfile=certfile,
            keyfile=keyfile,
            cafile=cafile,
            verify=verify,
        )

    def _stream(
        self,
        host: str,
        port: int,
        use_tls: bool = False,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        cafile: Optional[str] = None,
        verify: bool = True,
    ):
        ffmpeg_cmd = self._get_ffmpeg_cmd()
        self.sock = None
        self.proc = None
        try:
            if use_tls:
                # Create a secure SSLContext and enforce TLS 1.2+ (disable TLS 1.0/1.1)
                context = ssl.create_default_context(
                    ssl.Purpose.SERVER_AUTH if cafile else ssl.Purpose.CLIENT_AUTH
                )
                # Disable older, insecure protocol versions
                context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
                try:
                    context.minimum_version = ssl.TLSVersion.TLSv1_2
                except Exception:
                    pass

                if certfile and keyfile:
                    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

                # Verification: require certificates by default. If verify=True we
                # set CERT_REQUIRED and enable hostname checks. If verify=False we
                # fall back to CERT_NONE for compatibility with self-signed setups.
                if verify:
                    # If cafile is provided, use it; otherwise use system CAs
                    if cafile:
                        context.load_verify_locations(cafile=cafile)
                    context.verify_mode = ssl.CERT_REQUIRED
                    context.check_hostname = True
                else:
                    if cafile:
                        context.load_verify_locations(cafile=cafile)
                    context.verify_mode = ssl.CERT_NONE
                    context.check_hostname = False
                    # Runtime warning for insecure configuration
                    logging.getLogger(__name__).warning(
                        "TLS verification is disabled (verify=False). This is insecure and should only be used for testing or with trusted networks."
                    )
                raw_sock = socket.create_connection((host, int(port)))
                self.sock = context.wrap_socket(raw_sock, server_hostname=host)
                print(f"Streaming desktop audio to {host}:{port} over TLS in real-time ...")
            else:
                self.sock = socket.create_connection((host, int(port)))
                print(f"Streaming desktop audio to {host}:{port} in real-time ...")

            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, bufsize=0)
            silence = b"\x00" * self.buffer_size

            while True:
                data = self.proc.stdout.read(self.buffer_size)
                if not data:
                    self.sock.sendall(silence)
                    continue
                self.sock.sendall(data)

        except KeyboardInterrupt:
            print("\nStopped by user. Sending silence for smooth stop...")
            silence = b"\x00" * int(44100 * 2 * 2 * 0.1)
            try:
                if self.sock:
                    self.sock.sendall(silence)
            except Exception:
                pass
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            if self.proc:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2)
                except Exception:
                    pass
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                except Exception:
                    pass
            print("Done streaming.")

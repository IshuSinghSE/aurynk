#!/usr/bin/env python3
"""Test script to verify encoder parsing logic."""

# Sample output from scrcpy --list-encoders
sample_output = """
INFO: scrcpy 3.3.4 <https://github.com/Genymobile/scrcpy>
List of video encoders:
  --video-codec=h264:
    --video-encoder=c2.mtk.avc.encoder (hw) [vendor]
    --video-encoder=OMX.MTK.VIDEO.ENCODER.AVC (hw) [vendor]
    --video-encoder=c2.android.avc.encoder (sw)
  --video-codec=h265:
    --video-encoder=c2.mtk.hevc.encoder (hw) [vendor]
    --video-encoder=OMX.MTK.VIDEO.ENCODER.HEVC (hw) [vendor]
    --video-encoder=c2.android.hevc.encoder (sw)
  --video-codec=av1:
    --video-encoder=c2.android.av1.encoder (sw)
List of audio encoders:
  --audio-codec=opus:
    --audio-encoder=c2.android.opus.encoder (sw)
  --audio-codec=aac:
    --audio-encoder=c2.android.aac.encoder (sw)
  --audio-codec=flac:
    --audio-encoder=c2.android.flac.encoder (sw)
"""


def parse_encoder_list(output: str, encoder_type: str = "video") -> list:
    """Parse the output of scrcpy --list-encoders."""
    encoders = []
    current_codec = None
    in_section = False

    for line in output.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Detect section headers
        if "List of video encoders:" in line:
            in_section = encoder_type == "video"
            print(f"Found video section header, in_section={in_section}")
            continue
        elif "List of audio encoders:" in line:
            in_section = encoder_type == "audio"
            print(f"Found audio section header, in_section={in_section}")
            continue

        # Only process lines in the correct section
        if not in_section:
            continue

        # Detect codec headers
        if encoder_type == "video" and line_stripped.startswith("--video-codec="):
            current_codec = line_stripped.split("=")[1].rstrip(":")
            print(f"Found codec: {current_codec}")
            continue
        elif encoder_type == "audio" and line_stripped.startswith("--audio-codec="):
            current_codec = line_stripped.split("=")[1].rstrip(":")
            print(f"Found codec: {current_codec}")
            continue

        # Parse encoder lines
        encoder_flag = f"--{encoder_type}-encoder="
        if encoder_flag in line_stripped:
            encoder_part = line_stripped.split(encoder_flag, 1)[1]
            encoder_name = encoder_part.split()[0] if encoder_part else ""

            # Extract additional info
            info_parts = []
            if "(hw)" in line_stripped:
                info_parts.append("hw")
            elif "(sw)" in line_stripped:
                info_parts.append("sw")
            if "[vendor]" in line_stripped:
                info_parts.append("vendor")
            if "(alias" in line_stripped:
                info_parts.append("alias")

            info = ", ".join(info_parts) if info_parts else ""

            if encoder_name:
                encoder_dict = {
                    "name": encoder_name,
                    "codec": current_codec or "unknown",
                    "info": info,
                }
                print(f"Found encoder: {encoder_dict}")
                encoders.append(encoder_dict)

    return encoders


if __name__ == "__main__":
    print("=" * 60)
    print("Testing VIDEO encoder parsing:")
    print("=" * 60)
    video_encoders = parse_encoder_list(sample_output, "video")
    print(f"\nTotal video encoders found: {len(video_encoders)}")
    for enc in video_encoders:
        print(f"  - {enc['name']} ({enc['codec']}) {enc['info']}")

    print("\n" + "=" * 60)
    print("Testing AUDIO encoder parsing:")
    print("=" * 60)
    audio_encoders = parse_encoder_list(sample_output, "audio")
    print(f"\nTotal audio encoders found: {len(audio_encoders)}")
    for enc in audio_encoders:
        print(f"  - {enc['name']} ({enc['codec']}) {enc['info']}")

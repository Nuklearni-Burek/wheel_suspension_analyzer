#python video_manipulation/resize_video.py raw_videos/EQE_01_30fps.MP4 --scale 0.5
#You can manipulate the scale, adjust number however you want. You can also use --width or --height to specify exact dimensions instead of a scale factor.


import argparse
import subprocess
import sys
import shutil
from pathlib import Path


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg was not found on your system PATH.")
        print("Install it from https://ffmpeg.org/download.html and try again.")
        sys.exit(1)


def build_scale_filter(width: int = None, height: int = None, scale: float = None) -> str:
    """
    Builds an ffmpeg -vf scale filter string.
    Priority: explicit width/height > scale factor.
    Uses -2 for the unspecified dimension so it auto-calculates while staying
    divisible by 2 (required by most codecs like h264).
    """
    if width and height:
        return f"scale={width}:{height}"
    if width:
        return f"scale={width}:-2"
    if height:
        return f"scale=-2:{height}"
    if scale is not None:
        return f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"
    return None


def build_output_path(input_path: Path, suffix: str) -> Path:
    return input_path.with_name(f"{input_path.stem}_{suffix}{input_path.suffix}")


def resize_video(input_path: Path, output_path: Path, scale_filter: str, crf: int):
    cmd = [
        "ffmpeg",
        "-y",                      # overwrite output if it exists
        "-i", str(input_path),
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-crf", str(crf),          # quality: lower = better quality, bigger file (18-23 typical)
        "-preset", "medium",
        "-c:a", "copy",            # keep audio as-is
        str(output_path),
    ]

    print("Running command:")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("\nffmpeg reported an error. See output above for details.")
        sys.exit(result.returncode)

    print(f"\nDone. Output saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Resize a video's resolution without changing its frame rate or speed."
    )
    parser.add_argument("input", help="Path to the input video file")
    parser.add_argument(
        "--width", type=int, default=None,
        help="Target width in pixels (height auto-calculated to preserve aspect ratio)"
    )
    parser.add_argument(
        "--height", type=int, default=None,
        help="Target height in pixels (width auto-calculated to preserve aspect ratio)"
    )
    parser.add_argument(
        "--scale", type=float, default=None,
        help="Scale factor, e.g. 0.5 for half size (ignored if --width/--height given)"
    )
    parser.add_argument(
        "--crf", type=int, default=18,
        help="Video quality, lower = better/larger (default: 18)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: <input>_resized.<ext>)"
    )

    args = parser.parse_args()

    if not (args.width or args.height or args.scale):
        print("Error: you must specify one of --width, --height, or --scale.")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file '{input_path}' does not exist.")
        sys.exit(1)

    check_ffmpeg()

    scale_filter = build_scale_filter(args.width, args.height, args.scale)

    output_path = Path(args.output) if args.output else build_output_path(input_path, "resized")

    resize_video(input_path, output_path, scale_filter, args.crf)


if __name__ == "__main__":
    main()
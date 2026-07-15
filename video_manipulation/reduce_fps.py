#python video_manipulation/reduce_fps.py raw_videos/EQE_01.MP4 --fps 30
#Use the line above to reduce the frame rate of a video, you can adjust the number.


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


def build_output_path(input_path: Path, target_fps: int) -> Path:
    return input_path.with_name(f"{input_path.stem}_{target_fps}fps{input_path.suffix}")


def reduce_fps(input_path: Path, output_path: Path, fps: int, crf: int):
    cmd = [
        "ffmpeg",
        "-y",                      # overwrite output if it exists
        "-i", str(input_path),
        "-r", str(fps),            # target frame rate (keeps duration the same)
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
        description="Reduce a video's frame rate without changing its playback speed."
    )
    parser.add_argument("input", help="Path to the input video file")
    parser.add_argument(
        "--fps", type=int, default=30,
        help="Target frame rate (default: 30)"
    )
    parser.add_argument(
        "--crf", type=int, default=18,
        help="Video quality, lower = better/larger (default: 18)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path (default: <input>_<fps>fps.<ext>)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file '{input_path}' does not exist.")
        sys.exit(1)

    check_ffmpeg()

    output_path = Path(args.output) if args.output else build_output_path(input_path, args.fps)

    reduce_fps(input_path, output_path, args.fps, args.crf)


if __name__ == "__main__":
    main()
import argparse
import subprocess
import sys
import shutil
from pathlib import Path

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
import argparse
import subprocess
import sys
import shutil
from pathlib import Path

def build_output_path(input_path: Path, target_fps: int) -> Path:
    return input_path.with_name(f"{input_path.stem}_{target_fps}fps{input_path.suffix}")
#run as python barrelDistorionFix.py video.MP4

from datetime import datetime
import os
import cv2
import sys
import numpy as np


def undistort_video(video_path):
    if not os.path.isfile(video_path):
        print(f"Error: {video_path} does not exist.")
        return

    base_name = os.path.basename(video_path)
    output_name = os.path.join(os.path.dirname(video_path), f"undistorted_{base_name}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing: {base_name}")
    print(f"--> Output target: {output_name}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    # Fallback if FPS metadata is missing or corrupted
    if fps < 1.0 or np.isnan(fps):
        fps = 30.0

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_name, fourcc, fps, (width, height))

    # --- Custom Camera & Lens Parameters ---
    focal_length = width * 0.8
    K = np.array(
        [
            [focal_length, 0, width / 2],
            [0, focal_length, height / 2],
            [0, 0, 1],
        ],
        dtype=np.float32,
    )
    # Stronger barrel correction configuration matrix
    D = np.array([-0.5, 0.2, 0, 0], dtype=np.float32)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # Apply geometric transformation matrix math
            undistorted = cv2.undistort(frame, K, D)
            out.write(undistorted)
            # Show real-time frame progress feedback
            cv2.imshow("Undistort Preview", undistorted)
            # Press 'q' to stop processing completely
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\nProcessing interrupted by user execution.")
                break
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()

    print(f"Finished exporting: {output_name}\n")


if __name__ == "__main__":
    # Instead of scanning the directory, just name the video directly.
    video_name = sys.argv[1]
    undistort_video(video_name)
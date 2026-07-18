import os
import sys
import subprocess

import pandas as pd
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QDoubleSpinBox,
    QSpinBox,
    QPlainTextEdit,
)


VIDEO_MANIPULATION_DIR = "video_manipulation"


class PipelineWorker(QThread):
    """Runs the four CLI scripts in sequence in a background thread."""

    log_message = Signal(str)
    finished_ok = Signal(str)   # emits path to final CSV
    finished_err = Signal(str)  # emits error message

    def __init__(self, video_path, fps, scale):
        super().__init__()
        self.video_path = video_path
        self.fps = fps
        self.scale = scale

    def run_script(self, script_name, args):
        """Runs one script via subprocess, streaming stdout/stderr to the log."""
        script_path = os.path.join(VIDEO_MANIPULATION_DIR, script_name)
        cmd = [sys.executable, script_path] + args
        self.log_message.emit(f"$ {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.stdout:
            self.log_message.emit(result.stdout.strip())
        if result.stderr:
            self.log_message.emit(result.stderr.strip())

        if result.returncode != 0:
            raise RuntimeError(
                f"{script_name} failed (exit code {result.returncode}). "
                f"See log above for details."
            )

    def run(self):
        try:
            video = self.video_path
            base, ext = os.path.splitext(os.path.basename(video))
            in_dir = os.path.dirname(video) or "."

            # --- Step 1: reduce_fps.py ---
            self.log_message.emit("Step 1/4: Reducing FPS...")
            fps_output = os.path.join(in_dir, f"{base}_{self.fps}fps{ext}")
            self.run_script(
                "reduce_fps.py",
                [video, "--fps", str(self.fps)],
            )
            if not os.path.isfile(fps_output):
                raise RuntimeError(
                    f"Expected output not found: {fps_output}\n"
                    "Check the naming convention used by reduce_fps.py."
                )

            # --- Step 2: resize_video.py ---
            self.log_message.emit("Step 2/4: Resizing video...")
            resized_output = os.path.join(
                in_dir, f"{base}_{self.fps}fps_resized{ext}"
            )
            self.run_script(
                "resize_video.py",
                [fps_output, "--scale", str(self.scale)],
            )
            if not os.path.isfile(resized_output):
                raise RuntimeError(
                    f"Expected output not found: {resized_output}\n"
                    "Check the naming convention used by resize_video.py."
                )

            # --- Step 3: barrelDistortionFix.py ---
            self.log_message.emit("Step 3/4: Correcting lens distortion...")
            undistorted_name = f"undistorted_{os.path.basename(resized_output)}"
            undistorted_output = os.path.join(in_dir, undistorted_name)
            self.run_script(
                "barrelDistortionFix.py",
                [resized_output],
            )
            if not os.path.isfile(undistorted_output):
                raise RuntimeError(
                    f"Expected output not found: {undistorted_output}\n"
                    "Check the naming convention used by barrelDistortionFix.py."
                )

            # --- Step 4: detect_build_WheelCsv.py ---
            self.log_message.emit("Step 4/4: Detecting wheels & building CSV...")
            self.run_script(
                "detect_build_WheelCsv.py",
                [undistorted_output],
            )

            undistorted_base, _ = os.path.splitext(
                os.path.basename(undistorted_output)
            )
            output_dir = os.path.join(
                in_dir, f"{undistorted_base}_output"
            )
            csv_path = os.path.join(
                output_dir, f"{undistorted_base}_telemetry.csv"
            )
            if not os.path.isfile(csv_path):
                raise RuntimeError(
                    f"Expected CSV not found: {csv_path}\n"
                    "Check the naming convention used by detect_build_WheelCsv.py."
                )

            self.log_message.emit("Pipeline complete.")
            self.finished_ok.emit(csv_path)

        except Exception as e:
            self.finished_err.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wheel Vibration Analyzer")
        self.resize(900, 700)

        self.video_path = None
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- File picker row ---
        file_row = QHBoxLayout()
        self.file_label = QLabel("No video selected")
        browse_btn = QPushButton("Select Video...")
        browse_btn.clicked.connect(self.select_video)
        file_row.addWidget(self.file_label, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # --- FPS / Scale row ---
        params_row = QHBoxLayout()

        params_row.addWidget(QLabel("Target FPS:"))
        self.fps_input = QSpinBox()
        self.fps_input.setRange(1, 240)
        self.fps_input.setValue(30)
        params_row.addWidget(self.fps_input)

        params_row.addWidget(QLabel("Scale:"))
        self.scale_input = QDoubleSpinBox()
        self.scale_input.setRange(0.1, 1.0)
        self.scale_input.setSingleStep(0.1)
        self.scale_input.setValue(0.5)
        params_row.addWidget(self.scale_input)

        params_row.addStretch()
        layout.addLayout(params_row)

        # --- Process button ---
        self.process_btn = QPushButton("Process Video")
        self.process_btn.clicked.connect(self.start_pipeline)
        self.process_btn.setEnabled(False)
        layout.addWidget(self.process_btn)

        # --- Status label ---
        self.status_label = QLabel("Ready.")
        layout.addWidget(self.status_label)

        # --- Log box ---
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(1000)
        self.log_box.setFixedHeight(180)
        layout.addWidget(self.log_box)

        # --- Matplotlib canvas ---
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, stretch=1)

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select video",
            "",
            "Videos (*.mp4 *.MP4 *.avi *.mov *.mkv)",
        )
        if path:
            self.video_path = path
            self.file_label.setText(os.path.basename(path))
            self.process_btn.setEnabled(True)

    def append_log(self, text):
        self.log_box.appendPlainText(text)

    def start_pipeline(self):
        if not self.video_path:
            return

        self.process_btn.setEnabled(False)
        self.status_label.setText("Processing... this may take a while.")
        self.log_box.clear()

        fps = self.fps_input.value()
        scale = self.scale_input.value()

        self.worker = PipelineWorker(self.video_path, fps, scale)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished_ok.connect(self.on_pipeline_done)
        self.worker.finished_err.connect(self.on_pipeline_error)
        self.worker.start()

    def on_pipeline_done(self, csv_path):
        self.status_label.setText(f"Done. Loaded: {csv_path}")
        self.process_btn.setEnabled(True)
        self.plot_csv(csv_path)

    def on_pipeline_error(self, error_message):
        self.status_label.setText("Error during processing (see log).")
        self.append_log(f"ERROR: {error_message}")
        self.process_btn.setEnabled(True)

    def plot_csv(self, csv_path):
        df = pd.read_csv(csv_path)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if "Wheel_ID" in df.columns:
            for wheel_id, group in df.groupby("Wheel_ID"):
                ax.plot(
                    group["Original_Video_Frame"],
                    group["Clearance_Distance_px"],
                    label=wheel_id,
                    marker="o",
                    markersize=2,
                )
            ax.legend()
        else:
            ax.plot(df["Original_Video_Frame"], df["Clearance_Distance_px"])

        ax.set_xlabel("Frame")
        ax.set_ylabel("Clearance Distance (px)")
        ax.set_title("Wheel Well Clearance Over Time")
        self.canvas.draw()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
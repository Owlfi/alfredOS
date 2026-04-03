import os
import subprocess


class PiperAdapter:
    def __init__(self, piper_exe: str, model_path: str) -> None:
        self.piper_exe = piper_exe
        self.model_path = model_path

    def synthesize(self, text: str, output_path: str) -> str:
        if not os.path.exists(self.piper_exe):
            raise FileNotFoundError(f"Piper executable not found: {self.piper_exe}")

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Piper model not found: {self.model_path}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        cmd = [
            self.piper_exe,
            "--model", self.model_path,
            "--output_file", output_path,
        ]

        subprocess.run(cmd, input=text.encode("utf-8"), check=True)
        return output_path

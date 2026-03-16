import subprocess, json
from pathlib import Path
from .chart import convert
PATH_TO_BACKEND_EXE = "./backend.exe"

class SimaisharpWrapper:
    def __init__(self, path_to_backend_exe=PATH_TO_BACKEND_EXE):
        self.path_to_backend_exe = path_to_backend_exe

    def deserialize(self, simai_content, chart_key=5, convert_to_obj=False, return_json=False):
        Path("temp_simai_content.txt").write_text(simai_content, encoding="utf-8")
        result = subprocess.run([self.path_to_backend_exe, "temp_simai_content.txt", str(chart_key)], capture_output=True, text=True)
        dat = json.loads(result.stdout)
        Path("temp_simai_content.txt").unlink()
        if convert_to_obj:
            data = convert(dat)
            if return_json:
                return data, dat
            return data
        return dat
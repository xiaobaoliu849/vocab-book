import os
import sys
import json
import threading
import requests
import subprocess
import time
from vocab_app.config import BASE_DIR, APP_VERSION

class UpdateService:
    # URL to the version info JSON file
    # Example format: {"version": "3.2", "url": "https://example.com/app_v3.2.exe", "changelog": "Fixed bugs..."}
    # For now, we can use a placeholder or a Gitee/Github raw link
    UPDATE_CHECK_URL = "https://gitee.com/api/v5/repos/your_username/vocab_book/releases/latest"
    # Note: Above is an example. In a real scenario, you'd point to a specific raw JSON file controlled by you.
    # Let's assume a simple JSON structure hosted somewhere:
    # {
    #   "version": "3.2",
    #   "download_url": "https://...",
    #   "changelog": "..."
    # }

    # Using a dummy URL for now as per plan, user needs to configure this.
    VERSION_INFO_URL = "https://raw.githubusercontent.com/xiaobaoliu849/vocab-book/main/version.json"

    @staticmethod
    def check_for_updates(callback):
        """
        Check for updates in a separate thread.
        callback(has_update, update_info)
        update_info: dict with keys 'version', 'download_url', 'changelog', etc.
        """
        def _check():
            try:
                # In a real app, you might want to add a timeout
                response = requests.get(UpdateService.VERSION_INFO_URL, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    remote_version = data.get("version")

                    if remote_version and UpdateService._compare_versions(remote_version, APP_VERSION) > 0:
                        callback(True, data)
                    else:
                        callback(False, None)
                else:
                    print(f"Update check failed: {response.status_code}")
                    callback(False, None)
            except Exception as e:
                print(f"Update check error: {e}")
                callback(False, None)

        thread = threading.Thread(target=_check)
        thread.daemon = True
        thread.start()

    @staticmethod
    def _compare_versions(v1, v2):
        """
        Compare two version strings (e.g. "3.1" vs "3.2").
        Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal.
        """
        def parse(v):
            return [int(x) for x in v.split('.')]

        try:
            parts1 = parse(v1)
            parts2 = parse(v2)

            if parts1 > parts2: return 1
            if parts1 < parts2: return -1
            return 0
        except (ValueError, AttributeError) as e:
            print(f"Version comparison error: {e}")
            # 当版本格式无效时，假设远程版本更新
            return 0 if v1 == v2 else 1

    @staticmethod
    def download_update(url, progress_callback, complete_callback):
        """
        Download the update file in a separate thread.
        progress_callback(percentage: float)
        complete_callback(file_path: str)
        """
        def _download():
            try:
                temp_filename = "update_temp.exe"
                temp_path = os.path.join(BASE_DIR, temp_filename)

                response = requests.get(url, stream=True, timeout=30)
                total_size = int(response.headers.get('content-length', 0))

                downloaded = 0
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                progress_callback(progress)

                complete_callback(temp_path)
            except Exception as e:
                print(f"Download error: {e}")
                # Ideally pass error back
                progress_callback(-1) # Signal error

        thread = threading.Thread(target=_download)
        thread.daemon = True
        thread.start()

    @staticmethod
    def restart_and_update(new_exe_path):
        """
        Create a batch script to replace the executable and restart.
        """
        # Determine current executable path
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            # If running from source, we can't really "replace the exe"
            # But for testing, we can simulate it or just print a message
            print("Running from source, cannot perform self-update replacement.")
            # For testing purposes, let's just pretend
            current_exe = os.path.abspath(sys.argv[0])

        exe_dir = os.path.dirname(current_exe)
        exe_name = os.path.basename(current_exe)

        # Batch script path
        bat_path = os.path.join(exe_dir, "update_script.bat")

        # We need to use short paths or quotes to handle spaces
        # The script will:
        # 1. Wait for this process to exit
        # 2. Delete the old exe
        # 3. Move the new exe to the old exe's location
        # 4. Start the new exe
        # 5. Delete itself

        # Note: 'ping' is a common hack to sleep in batch files

        bat_content = f"""
@echo off
timeout /t 2 /nobreak > NUL
:loop
tasklist | find "{os.getpid()}" > NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak > NUL
    goto loop
)

echo Updating application...
del "{current_exe}"
move "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""

        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)

            # Execute the batch file detached
            subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

            # Exit the app
            sys.exit(0)

        except Exception as e:
            print(f"Failed to initiate update: {e}")

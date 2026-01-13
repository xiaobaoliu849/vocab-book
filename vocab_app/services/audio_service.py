import os
import time
import requests
import subprocess
from ..config import SOUNDS_DIR

# 检查是否有可用的音频播放方式
AUDIO_AVAILABLE = True  # 我们使用 subprocess 调用系统播放，总是可用


class AudioService:
    @staticmethod
    def is_available():
        return True

    @staticmethod
    def play_via_wmplayer(file_path):
        """使用 Windows Media Player 静默播放 (无窗口)"""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            # 使用 WPF MediaPlayer，异步播放不等待完成
            ps_script = f'''
Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open('{file_path}')
$player.Play()
Start-Sleep -Milliseconds 2000
'''

            # 使用 Popen 异步执行，不阻塞
            subprocess.Popen(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-Command', ps_script],
                startupinfo=startupinfo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            print("Played via WPF MediaPlayer.")
            return True

        except Exception as e:
            print(f"WPF MediaPlayer error: {e}")
            return False

    @staticmethod
    def play_word(word, on_start=None, on_finish=None, on_error=None):
        """
        Play audio for a word. Downloads if missing.
        """
        try:
            if on_start:
                on_start()

            mp3_path = os.path.join(SOUNDS_DIR, f"{word}.mp3")
            file_path = None

            # Check for cached file
            if os.path.exists(mp3_path):
                file_path = mp3_path

            # Validate existing file
            if file_path and os.path.exists(file_path):
                if os.path.getsize(file_path) < 1000:
                    try:
                        os.remove(file_path)
                        file_path = None
                    except (OSError, PermissionError) as e:
                        print(f"Failed to remove invalid audio file: {e}")

            # If no valid file found, download
            if not file_path:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                download_success = False

                audio_urls = [
                    f"https://dict.youdao.com/dictvoice?audio={word}&type=2",
                    f"https://dict.youdao.com/dictvoice?audio={word}&type=1"
                ]

                for url in audio_urls:
                    try:
                        print(f"Downloading audio from: {url}")
                        r = requests.get(url, headers=headers, timeout=5)

                        if r.status_code == 200 and len(r.content) > 1000:
                            if r.content.strip().startswith(b'<'):
                                print("Skipping: Downloaded content appears to be HTML.")
                                continue

                            file_path = mp3_path
                            with open(file_path, 'wb') as f:
                                f.write(r.content)

                            download_success = True
                            print(f"Audio downloaded successfully: {file_path}")
                            break

                    except Exception as e:
                        print(f"Audio download attempt failed: {e}")
                        continue

                if not download_success:
                    raise Exception("Failed to download audio from Youdao")

            # 播放音频
            print(f"Attempting playback: {file_path}")
            played = AudioService.play_via_wmplayer(file_path)

            if not played:
                if on_error:
                    on_error("Playback failed")
                return

            if on_finish:
                on_finish()

        except Exception as e:
            print(f"Play error: {e}")
            if on_error:
                on_error(str(e))

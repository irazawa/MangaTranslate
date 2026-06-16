import os
import sys
import subprocess
import time

def main():
    # Dapatkan direktori root project
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    os.chdir(base_dir)

    # 1. Pastikan virtual environment 'venv' sudah ada
    venv_path = os.path.join(base_dir, "venv")
    pythonw_path = os.path.join(venv_path, "Scripts", "pythonw.exe")
    main_py = os.path.join(base_dir, "main.py")

    if not os.path.exists(pythonw_path) or not os.path.exists(main_py):
        # Jalankan launcher.bat secara interaktif untuk setup awal jika venv belum ada
        subprocess.call(["cmd.exe", "/c", "launcher.bat"])
        return

    # 2. Jalankan Inpainting Server di background (hidden) jika foldernya ada
    inpainting_proc = None
    inpainting_bat = os.path.join(base_dir, "Inpainting", "run.bat")
    if os.path.exists(inpainting_bat):
        try:
            inpainting_proc = subprocess.Popen(
                [inpainting_bat], 
                cwd=os.path.dirname(inpainting_bat), 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # Beri jeda 3 detik agar server inpainting sempat inisialisasi
            time.sleep(3)
        except Exception as e:
            print(f"Gagal memulai inpainting server: {e}")

    # 3. Jalankan main.py menggunakan pythonw (tanpa console window) dan tunggu hingga ditutup
    try:
        app_proc = subprocess.Popen([pythonw_path, main_py], cwd=base_dir)
        app_proc.wait() # Tunggu sampai aplikasi ditutup oleh user
    except Exception as e:
        print(f"Gagal menjalankan aplikasi utama: {e}")
    finally:
        # 4. Hentikan inpainting server saat aplikasi utama ditutup agar tidak meninggalkan proses yatim (orphan)
        if inpainting_proc is not None:
            try:
                # Di Windows, membunuh task tree dari run.bat menggunakan taskkill lebih bersih
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(inpainting_proc.pid)], 
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                try:
                    inpainting_proc.terminate()
                except Exception:
                    pass

if __name__ == "__main__":
    main()

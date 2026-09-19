import os
import sys
import urllib.request
import zipfile
import subprocess
import platform

def download_ffmpeg():
    system = platform.system()
    print(f"🔍 Определение ОС: {system}")
    
    if system == "Windows":
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        target_zip = "ffmpeg.zip"
        exe_name = "ffmpeg.exe"
    else:
        print("⚠️ Для macOS/Linux скачайте ffmpeg вручную.")
        return

    print(f"⬇️ Скачивание FFmpeg...")
    urllib.request.urlretrieve(url, target_zip)
    
    print("📦 Распаковка FFmpeg...")
    with zipfile.ZipFile(target_zip, 'r') as zip_ref:
        for file in zip_ref.namelist():
            if file.endswith("bin/ffmpeg.exe"):
                with zip_ref.open(file) as source, open(exe_name, "wb") as target:
                    target.write(source.read())
                break
    
    os.remove(target_zip)
    print("✅ FFmpeg успешно добавлен в проект!")

def install_dependencies():
    print("\n📦 Установка зависимостей...")
    
    packages = [
        "numpy>=2.0.0",
        "PyQt6>=6.7.0",
        "pynput>=1.7.7",
        "sounddevice>=0.5.0",
        "soundfile>=0.12.1",
        "pydub>=0.25.1",
        "platformdirs>=4.2.2",
        "pyinstaller>=6.15.0"
    ]
    
    print(" Установка библиотек...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "--only-binary=:all:",
        "--upgrade"
    ] + packages, check=True)
    
    print("✅ Все зависимости установлены!")

def build_app():
    print("\n🛠️ Начало сборки приложения через PyInstaller...")
    
    # Получаем абсолютный путь к текущей директории
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")
    ffmpeg_exe = os.path.join(script_dir, "ffmpeg.exe")
    
    path_sep = ";" if platform.system() == "Windows" else ":"
    
    # Проверяем существование main.py
    if not os.path.exists(main_py):
        print(f"❌ ОШИБКА: Файл main.py не найден по пути: {main_py}")
        print("📁 Текущая директория:", os.getcwd())
        print("📄 Файлы в директории:", os.listdir(script_dir))
        return
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "XadbyPad",
        "--add-data", f"{ffmpeg_exe}{path_sep}.",
        "--workpath", os.path.join(script_dir, "build"),
        "--distpath", os.path.join(script_dir, "dist"),
        main_py
    ]
    
    print(f" Рабочая директория: {script_dir}")
    print(f"📄 main.py: {main_py}")
    print(f"🎬 Запуск команды: {' '.join(cmd)}")
    
    # Запускаем с указанием рабочей директории
    subprocess.run(cmd, cwd=script_dir, check=True)
    
    print("\n🎉 СБОРКА ЗАВЕРШЕНА!")
    print("📁 Готовая программа находится в папке: dist/XadbyPad/")
    print("📦 Заархивируйте эту папку в .zip и отдавайте пользователям.")

if __name__ == "__main__":
    print("=== Xadby Pad Auto Builder ===")
    
    # Получаем директорию скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if not os.path.exists("ffmpeg.exe") and platform.system() == "Windows":
        download_ffmpeg()
    
    install_dependencies()
    build_app()
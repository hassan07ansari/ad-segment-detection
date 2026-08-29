from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent.parent

AUDIO_DIR = PROJECT_ROOT/"data"/"audios"

AUDIO_DIR.mkdir(parents=True,exist_ok=True)

def extract_audio(video_path):
    video_path = Path(video_path)

    audio_path = AUDIO_DIR/f"{video_path.stem}.wav"

    command = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(audio_path)
    ]

    subprocess.run(command, check=True)

    return str(audio_path)

if __name__ == "__main__":

    test_video = PROJECT_ROOT/"data"/"videos"/"Ve0zdhTQA4U.webm"

    saved_audio = extract_audio(test_video)

    print("Audio saved at:")
    print(saved_audio)
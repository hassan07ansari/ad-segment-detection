from pathlib import Path
import yt_dlp

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VIDEO_DIR = PROJECT_ROOT/"data"/"videos"

VIDEO_DIR.mkdir(parents=True,exist_ok=True)

def download_video(url) : 
    ydl_options = {
        "outtmpl" : str(VIDEO_DIR / "%(id)s.%(ext)s"),
        "noplaylist" : True
        }
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info  = ydl.extract_info(url,download=True)

        video_path = ydl.prepare_filename(info)

    return video_path

if __name__ == "__main__":
    test_url = "https://www.youtube.com/shorts/Ve0zdhTQA4U"

    saved_path = download_video(test_url)

    print("Video saved at:")
    print(saved_path)


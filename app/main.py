from datetime import datetime, timezone
import time
import cv2

from acquisition import download_video
from audio import extract_audio
from transcription import transcribe_audio
from detector import detect_ads
from frames import extract_frames
from visual_detector import select_candidate_frames, classify_candidate_frames
from fusion import fuse_detections


def get_video_duration(video_path):

    video = cv2.VideoCapture(str(video_path))

    fps = video.get(cv2.CAP_PROP_FPS)
    total_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)

    duration = total_frames / fps

    video.release()

    return round(duration, 2)


def identify_source(url):

    if "youtube.com/shorts" in url:
        return "youtube", "short"

    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube", "vod"

    elif "instagram.com" in url:
        return "instagram", "short"

    return "other", "vod"


def process_video(url):

    start_time = time.time()

    platform, kind = identify_source(url)

    # 1. DOWNLOAD VIDEO
    video_path = download_video(url)

    duration = get_video_duration(video_path)


    # 2. AUDIO PIPELINE
    audio_path = extract_audio(video_path)

    transcript = transcribe_audio(audio_path)

    audio_detections = detect_ads(transcript)


    # 3. VISUAL PIPELINE

    if kind == "short":
        sample_interval = 0.5
    else:
        sample_interval = 1.0

    frames = extract_frames(
        video_path,
        sample_interval=sample_interval
    )

    candidates = select_candidate_frames(frames)

    visual_detections = classify_candidate_frames(
        candidates
    )


    # 4. AUDIO + VISUAL FUSION
    segments = fuse_detections(
        audio_detections,
        visual_detections,
        kind
    )


    # Add segment IDs required by final output
    for index, segment in enumerate(segments, start=1):

        segment["id"] = f"seg_{index:02d}"


    wall_clock = time.time() - start_time


    # 5. FINAL JSON
    result = {

        "source": {
            "url": url,
            "platform": platform,
            "kind": kind,
            "duration_s": duration,
            "processed_at": datetime.now(
                timezone.utc
            ).isoformat()
        },

        "segments": segments,

        "stats": {
            "wall_clock_s": round(wall_clock, 2),
            "estimated_cost_usd": 0.0,
            "frames_sampled": len(frames),
            "model_calls": len(candidates)
        }
    }

    return result


if __name__ == "__main__":

    import json

    test_url = "https://www.youtube.com/shorts/Ve0zdhTQA4U"

    result = process_video(test_url)

    print(
        json.dumps(
            result,
            indent=2
        )
    )
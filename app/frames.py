from pathlib import Path
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FRAMES_DIR = PROJECT_ROOT/"data"/"frames"

FRAMES_DIR.mkdir(parents=True,exist_ok=True)

def extract_frames(video_path,sample_interval = 0.5):
    video_path = Path(video_path)

    video = cv2.VideoCapture(str(video_path))

    if not video.isOpened():
        raise ValueError(f"could not open : {video_path}")

    fps = video.get(cv2.CAP_PROP_FPS)

    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

    duration = total_frames/fps

    print(f"FPS:{fps}")
    print(f"Total frames : {total_frames}")
    print(f"Duration:{duration:.2f} seconds")


    video_frame_dir = FRAMES_DIR/video_path.stem

    video_frame_dir.mkdir(parents=True,exist_ok=True)

    frames = []

    timestamp = 0.0

    while timestamp < duration:

        video.set(cv2.CAP_PROP_POS_MSEC,timestamp*1000)   # tells opencv to move to  this timestamp in the video


        success,frame = video.read()

        if not success:
            break


        frame_name = f"frame_{timestamp:.1f}.jpg"

        frame_path = video_frame_dir/frame_name

        cv2.imwrite(str(frame_path),frame)  # saves the extracted frame as a JPG image

        frames.append({
            "timestamp" : round(timestamp,2),
            "path" : str(frame_path)
        })

        timestamp = timestamp + sample_interval  #it is 0.5 sample interval as of now

    video.release()

    return frames


if __name__ == "__main__":

    test_video = (PROJECT_ROOT/"data"/"videos"/"Ve0zdhTQA4U.webm")

    extracted_frames = extract_frames(test_video)

    print(f"\nExtracted {len(extracted_frames)}frames.")







        


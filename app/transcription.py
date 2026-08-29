from pathlib import Path
from faster_whisper import WhisperModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent

model = WhisperModel("small",device = "cpu",compute_type="int8")

def transcribe_audio(audio_path):
    segments,info = model.transcribe(
        str(audio_path),
        task='translate',
        vad_filter = True
    )

    transcript = []

    for segment in segments:

        transcript.append({
            "start" : round(segment.start,2),
            "end" : round(segment.end,2),
            "text" : segment.text.strip()
        })

    return {
        "detected_language" : info.language,
        "language_probability" : round(
            info.language_probability,3
        ),
        "segments" : transcript
    }

if __name__ == "__main__":

    test_audio = (
        PROJECT_ROOT
        /"data"
        /"audios"
        /"Ve0zdhTQA4U.wav"
    )

    result = transcribe_audio(test_audio)

    print("Detected language:")
    print(result["detected_language"])

    print("\nTranscript:\n")
    for segment in result['segments']:
        print(
            f'[{segment['start']} - {segment['end']}]'
            f'{segment["text"]}'
        )
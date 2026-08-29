from transcription import transcribe_audio
from pathlib import Path
import json
import ollama


PROJECT_ROOT = Path(__file__).resolve().parent.parent


STRONG_AD_PHRASES = [
    "sponsored by",
    "today's sponsor",
    "brought to you by",
    "paid partnership",
    "use code",
    "promo code",
    "discount code",
    "link in the description",
    "affiliate link",
    "shop now",
    "buy now",
    "order now",
    "call now",
    "download now",
    "sign up",
    "free trial"
]


def classify_with_llm(text):

    prompt = f"""
You are an advertisement classifier.

An advertisement is content whose primary purpose is to promote
a product, service, brand, sponsor, affiliate offer,
or paid creator offering.

Transcript:
"{text}"

Decide whether this is an advertisement.

Allowed ad types:
preroll
midroll_sponsor_read
product_placement
self_promo
affiliate
platform_inserted
bumper
other

Return ONLY JSON:

{{
    "is_ad": true,
    "ad_type": "other",
    "brand": null,
    "confidence": 0.0,
    "description": "short explanation"
}}
"""

    response = ollama.chat(
        model="qwen3:4b-instruct",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        format="json"
    )

    return json.loads(response["message"]["content"])


def detect_ads(transcript_result):

    detections = []

    for segment in transcript_result["segments"]:

        text = segment["text"].lower()

        matched_signals = []

        for phrase in STRONG_AD_PHRASES:

            if phrase in text:
                matched_signals.append(phrase)

        if matched_signals:

            detections.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "is_ad": True,
                "ad_type": "other",
                "brand": None,
                "confidence": 0.90,
                "description": "Matched strong advertising phrase.",
                "source": "rule",
                "matched_signals": matched_signals
            })

        else:

            llm_result = classify_with_llm(segment["text"])

            if llm_result.get("is_ad") is True:

                detections.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                    "is_ad": True,
                    "ad_type": llm_result.get("ad_type"),
                    "brand": llm_result.get("brand"),
                    "confidence": llm_result.get("confidence"),
                    "description": llm_result.get("description"),
                    "source": "llm"
                })

    return detections


if __name__ == "__main__":

    test_audio = (
        PROJECT_ROOT
        / "data"
        / "audios"
        / "Ve0zdhTQA4U.wav"
    )

    transcript = transcribe_audio(test_audio)

    detections = detect_ads(transcript)

    print("\nDetected advertisements:\n")

    print(json.dumps(detections, indent=2))
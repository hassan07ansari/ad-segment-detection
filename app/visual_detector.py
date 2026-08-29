from pathlib import Path
import json
import ollama
import cv2


PROJECT_ROOT = Path(__file__).resolve().parent.parent


ALLOWED_AD_TYPES = {
    "preroll",
    "midroll_sponsor_read",
    "product_placement",
    "self_promo",
    "affiliate",
    "platform_inserted",
    "bumper",
    "other"
}


# SINGLE FRAME VLM CLASSIFICATION
def classify_frame(frame_path):

    prompt = """
You are an advertisement detector for video frames.

An advertisement is visual content whose primary purpose is to promote
a product, service, brand, sponsor, affiliate offer, business,
or paid creator offering.

Inspect this frame carefully.

Look for:
- business or brand names
- phone numbers or contact information
- prices or discounts
- promotional banners
- calls to action
- product or service promotion
- sponsor graphics
- promotional text in any language, including Telugu

Do not classify something as an advertisement only because
a person, object, number, or product appears.

Allowed ad types:
- preroll
- midroll_sponsor_read
- product_placement
- self_promo
- affiliate
- platform_inserted
- bumper
- other

A persistent channel logo, watermark, or creator branding by itself
is not an advertisement.

Only classify it as advertising when it is part of an explicit
promotional message, call to action, sponsor placement,
or commercial offer.

The "ad_type" MUST be exactly one of these values.
Do not create new ad types.
If none clearly applies, use "other".

Return ONLY JSON:

{
    "is_ad": true,
    "ad_type": "other",
    "brand": null,
    "confidence": 0.0,
    "description": "short explanation",
    "visual_evidence": []
}
"""

    response = ollama.chat(
        model="qwen3-vl:4b",
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [str(frame_path)]
            }
        ],
        format="json"
    )

    print("\nRAW RESPONSE:")
    print(repr(response["message"]["content"]))

    content = response["message"]["content"].strip()

    if not content:
        return {
            "is_ad": False,
            "ad_type": "other",
            "brand": None,
            "confidence": 0.0,
            "description": "VLM returned an empty response.",
            "visual_evidence": []
        }

    result = json.loads(content)

    if result.get("ad_type") not in ALLOWED_AD_TYPES:
        result["ad_type"] = "other"

    return result


# COMPARING TWO FRAMES
def frame_difference(frame_path_1, frame_path_2):

    frame1 = cv2.imread(str(frame_path_1))
    frame2 = cv2.imread(str(frame_path_2))

    frame1 = cv2.resize(
        frame1,
        (160, 90)
    )

    frame2 = cv2.resize(
        frame2,
        (160, 90)
    )

    frame1 = cv2.cvtColor(
        frame1,
        cv2.COLOR_BGR2GRAY
    )

    frame2 = cv2.cvtColor(
        frame2,
        cv2.COLOR_BGR2GRAY
    )

    difference = cv2.absdiff(
        frame1,
        frame2
    )

    return difference.mean()


# SELECTING IMPORTANT FRAMES
def select_candidate_frames(
    frames,
    difference_threshold=20,
    backup_interval=5.0
):

    if not frames:
        return []

    selected = [frames[0]]

    previous_frame = frames[0]

    last_backup_time = frames[0]["timestamp"]

    for current_frame in frames[1:]:

        difference = frame_difference(
            previous_frame["path"],
            current_frame["path"]
        )

        scene_changed = (
            difference >= difference_threshold
        )

        periodic_backup = (
            current_frame["timestamp"]
            - last_backup_time
            >= backup_interval
        )

        if scene_changed or periodic_backup:

            selected.append(current_frame)

        if periodic_backup:

            last_backup_time = current_frame["timestamp"]

        previous_frame = current_frame

    return selected


# CLASSIFYING THE SELECTED CANDIDATE FRAMES
def classify_candidate_frames(candidates):

    detections = []

    for index, candidate in enumerate(candidates):

        print(
            f"\nChecking candidate "
            f"{index + 1}/{len(candidates)} "
            f"at {candidate['timestamp']} seconds"
        )

        result = classify_frame(
            candidate["path"]
        )

        result["timestamp"] = candidate["timestamp"]

        if result.get("is_ad") is True:

            detections.append(result)

    return detections


# TESTING THE VISUAL PIPELINE
if __name__ == "__main__":

    from frames import extract_frames

    test_video = (
        PROJECT_ROOT
        / "data"
        / "videos"
        / "Ve0zdhTQA4U.webm"
    )

    frames = extract_frames(
        test_video,
        sample_interval=0.5
    )

    candidates = select_candidate_frames(
        frames
    )

    print(
        "\nTotal sampled frames:",
        len(frames)
    )

    print(
        "Candidate frames:",
        len(candidates)
    )

    print("\nCandidate timestamps:")

    for candidate in candidates:

        print(
            candidate["timestamp"]
        )

    visual_detections = classify_candidate_frames(
        candidates
    )

    print("\nVISUAL AD DETECTIONS:")

    print(
        json.dumps(
            visual_detections,
            indent=2
        )
    )
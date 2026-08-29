def strong_visual_evidence(detection):

    evidence_text = " ".join(
        detection.get("visual_evidence", [])
    ).lower()

    description = detection.get(
        "description",
        ""
    ).lower()

    text = evidence_text + " " + description

    strong_signals = [
        "price",
        "phone",
        "contact",
        "discount",
        "offer",
        "call",
        "buy",
        "book",
        "promo",
        "sponsor",
        "₹"
    ]

    return any(
        signal in text
        for signal in strong_signals
    )


def visual_to_segment(detection):

    timestamp = detection["timestamp"]

    # Candidate frames may be ~5 seconds apart,
    # so boundary is only approximate.
    start = max(
        0,
        timestamp - 2.5
    )

    end = timestamp + 2.5

    return {
        "start_s": round(start, 2),
        "end_s": round(end, 2),
        "ad_type": detection.get(
            "ad_type",
            "other"
        ),
        "brand": detection.get("brand"),
        "confidence": detection.get(
            "confidence",
            0.0
        ),
        "description": detection.get(
            "description",
            ""
        ),
        "evidence": {
            "frame_timestamps": [
                timestamp
            ],
            "transcript_span": "",
            "signals_used": [
                "vlm_frame"
            ]
        }
    }


def audio_to_segment(detection):

    return {
        "start_s": detection["start"],
        "end_s": detection["end"],
        "ad_type": detection.get(
            "ad_type",
            "other"
        ),
        "brand": detection.get("brand"),
        "confidence": detection.get(
            "confidence",
            0.0
        ),
        "description": detection.get(
            "description",
            ""
        ),
        "evidence": {
            "frame_timestamps": [],
            "transcript_span": detection.get(
                "text",
                ""
            ),
            "signals_used": [
                "asr"
            ]
        }
    }


def fuse_detections(
    audio_detections,
    visual_detections,
    kind
):

    final_segments = []

    visual_segments = []

    for detection in visual_detections:

        if strong_visual_evidence(detection):

            visual_segments.append(
                visual_to_segment(detection)
            )


    if kind == "short":

        # Visual is primary for Shorts/Reels.
        final_segments.extend(
            visual_segments
        )

        # Only explicit audio-rule detections are
        # allowed through independently.
        for detection in audio_detections:

            if detection.get("source") == "rule":

                final_segments.append(
                    audio_to_segment(detection)
                )


    else:

        # Audio is primary for long-form video.
        for detection in audio_detections:

            final_segments.append(
                audio_to_segment(detection)
            )

        final_segments.extend(
            visual_segments
        )


    final_segments.sort(
        key=lambda x: x["start_s"]
    )

    return final_segments


# DESIGN.md

# Ad Segment Detection in Video

## 1. Goal

The goal of this project is to take a video URL and return a machine-readable timeline of the advertising segments present inside the video.

The videos in the test set are different from each other:

* long-form YouTube videos
* YouTube Shorts
* Instagram Reels
* live streams

I did not want to use the same detection method for every format because the strongest advertising signal is different depending on the type of video.

For example, in a long YouTube podcast, a sponsor may mainly be detected from what the host says. In a Reel or Short, the actual speech may be normal informational content while an advertisement is displayed visually on part of the screen.

Because of this, I built separate audio and visual detection paths and then combine their results.

---

# 2. What I Consider an Advertisement

For this project, I consider something an advertisement when there is a clear attempt to promote a company, product, service, offer, paid sponsor, creator product, affiliate product, or another commercial action.

Some signals that can support this decision are:

* sponsor language
* discount codes
* prices or offers
* phone numbers
* booking or purchase instructions
* "buy now", "call now", "subscribe", or similar requests
* a promotional panel
* clinic/business details
* explicit sponsor branding
* product placement with promotional intent

I do not consider every visible brand or every positive statement an advertisement.

For example:

* a channel watermark alone is not an ad
* a doctor giving informational health advice is not automatically an ad
* a company logo appearing only as normal producer branding is not automatically an ad

The important factor for me is **promotional intent**, not simply whether a brand name is visible.

---

# 3. Ad Type Taxonomy

I use the taxonomy required in the assignment:

### preroll

An advertisement that appears before the main content begins.

### midroll_sponsor_read

A sponsor message spoken during the main content.

### product_placement

A product or brand is deliberately placed inside the content as promotion.

### self_promo

The creator, channel, clinic, or company promotes itself.

### affiliate

The content promotes something using an affiliate relationship, link, or code.

### platform_inserted

An advertisement inserted by the video platform rather than being present inside the underlying media.

### bumper

A short promotional or sponsored card, usually only a few seconds long.

### other

An advertisement that is clear but does not fit the other categories properly.

---

# 4. Architecture

The main flow of my project is:

```text
Video URL
   |
   v
Video Acquisition
   |
   +----------------------------+
   |                            |
   v                            v
Audio Pipeline              Visual Pipeline
   |                            |
Extract Audio                Sample Frames
   |                            |
Whisper Transcript           OpenCV Candidate Filtering
   |                            |
Rule + Text LLM              Vision Language Model
   |                            |
   +-------------+--------------+
                 |
                 v
          Fusion / Decision
                 |
                 v
          Final JSON Result
```

The final result contains:

* source information
* detected ad segments
* start and end timestamps
* type
* brand
* confidence
* description
* evidence
* processing statistics

---

# 5. Video Acquisition

For YouTube videos I use `yt-dlp` to download the video locally.

I chose a simple local-file flow because the actual detection pipeline should not depend strongly on the website acquisition method.

For Instagram Reels, I do not try to defeat Instagram's anti-automation or authentication system.

The pipeline is able to work from a local media file.

In production, for public Instagram URLs I would treat acquisition as a separate service. It would need to handle:

* authentication
* rate limits
* retries
* account/session management
* changes to Instagram endpoints
* legal and platform terms

I would only use an acquisition approach that complies with the platform's terms and applicable legal requirements.

I intentionally did not spend the assignment time trying to build an Instagram scraping system because that is separate from the advertisement detection problem.

---

# 6. Audio Pipeline

The audio pipeline is mainly useful for long-form videos.

The flow is:

```text
Video
→ FFmpeg
→ mono 16 kHz WAV
→ faster-whisper
→ timestamped transcript
→ rule detection + text LLM
```

I use:

```text
faster-whisper
WhisperModel("small")
device = "cpu"
compute_type = "int8"
task = "translate"
```

I use translation so Telugu speech can become an English timestamped transcript before text classification.

## Audio ad detection

For each transcript segment, I first check for strong advertising phrases such as:

* sponsored by
* today's sponsor
* brought to you by
* paid partnership
* use code
* promo code
* discount code
* affiliate link
* shop now
* buy now

If one of these strong phrases is present, I treat it as stronger evidence.

If there is no strong rule match, I use a local `qwen3:4b-instruct` model through Ollama to understand the meaning of the transcript.

I chose this combination because rules are reliable for very obvious sponsor language, while the LLM can understand advertising that is expressed in less predictable language.

---

# 7. Audio Limitation I Found

One important failure happened on the YouTube Short.

The woman was explaining the health benefits of a leaf. This was informational content.

However, the text LLM classified part of the speech as an advertisement with very high confidence.

This showed me that positive language about a product, ingredient, health benefit, or topic is not the same as commercial intent.

Because of this failure, I do not trust LLM-only audio detections equally across all formats.

For Shorts and Reels, visual evidence is given more importance.

---

# 8. Visual Pipeline

The visual pipeline is especially important for Shorts and Reels.

For the test YouTube Short:

* duration was about 63.88 seconds
* original video contained 1597 frames
* I sampled one frame every 0.5 seconds
* this produced 128 sampled frames

I intentionally used relatively dense sampling because short visual advertisements or changing panels could otherwise be missed.

However, sending all 128 frames to a vision model would be too slow on my local CPU.

Because of this, I added a cheap filtering step before the VLM.

---

# 9. Candidate Frame Filtering

I compare neighbouring sampled frames using OpenCV.

The basic process is:

1. resize both frames to 160 x 90
2. convert them to grayscale
3. calculate `cv2.absdiff`
4. calculate the mean difference
5. keep the frame when the difference is large enough

My current difference threshold is approximately `20`.

I also keep a backup frame every 5 seconds even when there is no major visual change.

This is important because some advertisements stay static for a long time. If I only selected scene changes, I could miss a static sponsor panel.

For the Short:

```text
128 sampled frames
        |
        v
OpenCV filtering
        |
        v
14 candidate frames
```

The candidate timestamps included:

```text
0.0
4.5
5.0
10.0
15.0
20.0
25.0
30.0
35.0
40.0
45.0
50.0
55.0
60.0
```

This reduced the number of expensive vision-model calls significantly.

---

# 10. Vision Model

For candidate frames I use:

```text
qwen3-vl:4b
```

through Ollama.

The model receives a candidate image and returns fields such as:

* is_ad
* ad_type
* brand
* confidence
* description
* visual evidence

For example, on a known frame from the YouTube Short, the model correctly identified the Avis Vascular Center advertisement and detected signals such as:

* Avis Vascular Center
* ₹4500
* phone number
* Telugu promotional text

This confirmed that visual analysis was useful for advertisements that the audio pipeline could not detect correctly.

I also validate the returned `ad_type` in Python so the model cannot return categories outside the required assignment taxonomy.

---

# 11. Fusion Strategy

The audio and visual pipelines do not have equal importance for every video type.

## Short videos and Reels

For Shorts and Reels:

```text
visual evidence = primary
audio evidence = supporting
```

This decision came directly from my test Short.

The spoken content was informational, while the real advertisement was displayed visually.

Therefore, an LLM-only audio guess does not automatically become a final advertisement for a Short.

A strong audio rule such as "sponsored by" can still be accepted independently.

## Long-form video

For long-form video:

```text
audio evidence = primary
visual evidence = supplementary
```

This is because a host may read a sponsor message while the visual scene remains almost unchanged.

---

# 12. Segment Boundaries

Audio detections already contain transcript start and end timestamps.

Visual detections are harder because a single positive candidate frame does not directly tell me the exact beginning and ending of an advertisement.

My current simple approach uses an approximate window around a positive visual timestamp.

This means visual boundaries are not exact.

I do not hide this limitation.

I plan to measure it using boundary error in the evaluation rather than claiming that a positive frame gives an exact segment.

A better system would inspect nearby frames before and after a positive frame to find the actual transition.

---

# 13. Live Streams

Live streams are different because there is no final video duration and the system cannot look into the future.

For my manual ground truth I observed approximately a 30-minute window of the supplied news live stream.

In a production live system, I would process the stream in fixed windows.

For example:

```text
current live window
→ process available audio and frames
→ detect candidate advertisements
→ keep small state from previous window
→ commit completed segments
→ continue to next window
```

If a sponsor read starts near the end of one window and continues into the next, I would not immediately close the segment.

I would keep the possible open segment in temporary state and join it with evidence from the next window.

This prevents one real sponsor read from becoming two false segments just because it crossed a processing boundary.

My current submission does not implement a complete production streaming system. I focused first on the required VOD and short-video pipeline.

---

# 14. Ambiguity Decisions

## 1. "If you like this channel, join my Patreon."

I would label this as `self_promo`.

It is an explicit request asking the viewer to financially support something connected to the creator.

---

## 2. Host wears a hoodie with their own merch logo for the whole video

I would not automatically label the whole video as an advertisement.

If the host only wears the hoodie and never promotes or discusses it, I treat it as passive branding.

If the host tells viewers where to buy it or actively promotes it, I would label that part as `self_promo`.

---

## 3. A 1.4-second animated "sponsored by" bumper

I would label this as `bumper`.

This case is one reason I use dense sampling for short videos.

A sampling interval that is too large could completely miss a 1.4-second event.

---

## 4. Movie review showing 40 seconds of the official trailer

I would not automatically call the trailer an advertisement.

If the trailer is being shown as part of the review or criticism, I treat it as editorial content.

If it is shown as a paid promotional insertion, then I would label it as advertising.

---

## 5. Platform pre-roll that does not appear in downloaded media

I would not include it in the ground truth for the downloaded media.

The detector cannot detect pixels or audio that do not exist in its input.

For example, while manually watching the live stream I saw a Groww advertisement inserted by YouTube. I did not include that as part of the underlying stream ground truth.

---

## 6. 90-second sponsor read with no visual change

I would rely primarily on audio.

This is one of the main reasons I did not build a frame-only system.

The host's speech can contain strong sponsor language even if the visual frame remains unchanged.

---

## 7. Reel is an advertisement from first frame to last frame

I would use:

```text
start_s = 0.0
end_s = actual video duration
```

The advertisement covers the complete video.

---

## 8. Two sponsors back-to-back with no gap

I would create two segments if they are clearly two different sponsors.

The lack of silence or visual gap does not make them the same advertisement.

Brand or sponsor identity is enough to create a boundary between them.

---

# 15. What Did Not Work

Several things did not work as expected during implementation.

## Text LLM false positive

The text LLM treated informational health discussion as advertising.

This showed that semantic classification alone can confuse positive language with commercial intent.

## Visual false positive

The visual model sometimes treated normal doctor/business branding as `self_promo`.

This is why I added the rule that a persistent channel logo or watermark alone should not automatically be treated as an advertisement.

## Empty VLM response

Sometimes the local VLM returned an empty response.

Trying to directly parse this using `json.loads()` caused a crash.

I added a guard so an empty response is handled safely instead of crashing the entire pipeline.

## Multi-image request

I tried sending all 14 candidate images in one VLM request.

The request was approximately 28,992 tokens while the available context was only 4,096 tokens.

The request therefore failed.

I considered smaller batches or contact sheets but did not add more complexity before the deadline.

## Local CPU latency

The biggest engineering problem is VLM inference speed.

A single candidate frame can take several minutes on my local CPU.

Three frames could take more than ten minutes.

Because of this, a complete 14-frame visual pass is currently too slow for a convenient live demonstration.

This is the main reason my recorded demonstration uses a known real candidate frame to show the visual-model output rather than pretending that the complete visual pipeline runs quickly.

---

# 16. Cost and Latency

I use local models rather than paid hosted APIs.

Therefore my current hosted-model API cost is:

```text
estimated_cost_usd = 0
```

This does not mean computation is actually free.

It excludes:

* local hardware cost
* electricity
* CPU/GPU time

The main cost in my current implementation is time.

The VLM running on CPU is the main latency bottleneck.

For example, the Short produces 128 sampled frames, which are reduced to 14 candidates, but even those 14 VLM calls can still require a long time locally.

In a production environment I would calculate:

```text
wall clock time / video duration
```

to report processing time as a multiple of real time.

---

# 17. Determinism

The OpenCV frame sampling and rule-based checks are deterministic when the input is unchanged.

The local language and vision models can still produce slightly different classifications or descriptions between runs.

Segment boundaries from visual detections are also approximate because they are currently created around sampled candidate timestamps.

For a production version I would reduce this variation by:

* using lower model temperature
* validating JSON strictly
* caching model outputs for identical frames
* using deterministic boundary refinement
* storing model version and prompt version with each evaluation

---

# 18. What Breaks at 1000 Videos Per Day

The current local CPU implementation would not scale to 1000 videos per day.

The main problems would be:

* VLM inference time
* sequential processing
* large number of extracted frames
* local storage
* repeated Whisper processing
* long queues
* failure recovery

I would not solve this by simply running more copies of the current code.

I would first reduce unnecessary work.

Possible changes include:

* GPU inference
* smaller/faster vision model
* better candidate ranking
* lower-resolution model input
* controlled batching
* parallel worker queues
* caching
* separating audio and visual workers
* processing only the modalities needed for each video type

For example, a long podcast may not need dense visual analysis if the audio already gives strong sponsor evidence.

---

# 19. What I Would Build With Two More Weeks

With another two weeks I would focus on improving reliability and speed rather than adding unrelated features.

My priorities would be:

1. Improve exact visual segment boundaries by checking neighbouring frames.
2. Add proper live-stream window processing and state across windows.
3. Run the VLM using a GPU or faster model.
4. Test controlled batching without exceeding model context.
5. Improve visual candidate ranking.
6. Add stronger tests for JSON parsing and malformed model output.
7. Calibrate confidence values using the labelled test set.
8. Add more reliable merging of nearby audio and visual detections.
9. Add caching for repeated frames and model requests.
10. Improve the minimal viewer and display evidence for each detected segment.

---

# 20. What I Cut and Why

Because of the assignment deadline, I stopped adding engineering complexity once the main audio, visual, fusion, and API flow existed.

I intentionally did not spend more time on:

* automated Instagram scraping
* GPU deployment
* complex VLM batching
* a full production live-stream architecture
* database infrastructure
* advanced frontend work

The biggest limitation is that full local visual inference is slow.

For the demonstration, I use a real candidate frame that I manually know contains an advertisement and show the actual VLM result for that frame.

I do not present this as a complete fast end-to-end run.

The same visual classification function is used by the normal pipeline on selected candidate frames, but running all candidates locally takes much longer because of CPU inference latency.

---

# 21. Use of AI Tools

I used ChatGPT while building this assignment for discussion, debugging support, understanding parts of the implementation, and helping organize documentation.

The main project decisions were based on my own testing of the supplied videos and the failures I observed while running the pipeline.

I manually watched and labelled the five test inputs myself for the ground truth.

I also reviewed and substantially rewrote the project explanations so that I can understand and explain the design and code during the follow-up interview.

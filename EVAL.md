# EVAL.md

# Evaluation

## 1. Evaluation Goal

The purpose of this evaluation is to compare what I manually observed in the supplied test videos with what my ad-detection pipeline actually detected.

I first created the ground truth by manually watching the supplied videos.

I did this so that the model output would be compared against my own human labels rather than treating the model itself as the source of truth.

The main questions I wanted to evaluate were:

* Did the system detect a real advertisement?
* Did the system create false advertisements?
* Did audio or visual evidence work better for a particular video type?
* How close were the predicted segment boundaries to the manual boundaries?
* What caused the system to fail?
* What currently limits the speed of the system?

The full manual labels are stored in:

```text
ground_truth.json
```

---

# 2. Ground Truth Method

I manually reviewed all five supplied test inputs.

For each video I noted:

* normal video content
* advertisement start and end times when available
* brand
* advertisement type
* visible or spoken evidence
* cases where I was unsure whether something should count as an advertisement

My general rule was:

> I label something as an advertisement when there is clear promotional intent for a product, service, brand, sponsor, creator, clinic, offer, or commercial action.

I did not automatically label every visible logo or positive statement as an advertisement.

For example:

* a normal channel watermark alone was not treated as an ad
* informational health discussion was not automatically treated as an ad
* platform-served YouTube advertisements were kept separate from advertisements actually present in the downloaded media

For the live stream, I manually observed approximately a 30-minute window because the stream had no fixed ending.

---

# 3. Current Evaluation Status

I did not complete a full end-to-end system run on all five test videos before the submission deadline.

I therefore do not report evaluation numbers that I did not actually measure.

My current evaluation status is:

| Video             | Ground Truth                                     | System Evaluation                                                                   |
| ----------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Long-form YouTube | Manually labelled                                | Full pipeline not completed                                                         |
| YouTube Short     | Manually labelled                                | Audio tested, visual sampling/filtering tested, representative VLM candidate tested |
| Live stream       | Approximately 30-minute window manually reviewed | Complete live detection path not implemented                                        |
| Instagram Reel 1  | Manually labelled                                | Full pipeline not run                                                               |
| Instagram Reel 2  | Manually labelled                                | Full pipeline not run                                                               |

The YouTube Short is the video on which I performed the most detailed pipeline testing.

Most of the failure cases in this document came from that test.

---

# 4. Metrics

The metrics I would use for full evaluation are described below.

## Precision

Precision measures how many predicted advertisements are actually advertisements.

```text
Precision = True Positives / (True Positives + False Positives)
```

High precision means the system does not produce many false advertisements.

---

## Recall

Recall measures how many real advertisements were successfully detected.

```text
Recall = True Positives / (True Positives + False Negatives)
```

High recall means the system does not miss many real advertisements.

---

## F1 Score

F1 combines precision and recall.

```text
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

---

## Segment IoU

For this task, detecting an advertisement is not enough. The predicted start and end timestamps also matter.

I would therefore use segment Intersection over Union.

```text
IoU =
overlap duration
-----------------------
combined segment duration
```

For example:

```text
Ground truth: 4 s → 20 s
Prediction:   6 s → 22 s
```

The two segments overlap, but their boundaries are not identical.

A higher IoU means the predicted timeline is closer to the manual ground truth.

---

## Boundary Error

Boundary error measures how far the predicted start or end is from the manual label.

Example:

```text
Ground truth start = 4.0 s
Predicted start    = 5.0 s

Start boundary error = 1.0 s
```

This metric is important for my visual pipeline because the current visual boundary generation is approximate.

---

# 5. Why I Do Not Report Final Metric Numbers

I have defined precision, recall, F1, IoU and boundary error because these are the metrics I would use for a full comparison against `ground_truth.json`.

However, I have not reported final numerical values because I did not complete final end-to-end predictions for all five inputs.

I also do not report precision and recall only from the partially tested Short because I do not yet have a complete final prediction set for that video.

I have:

* the complete manual ground truth
* the audio detector output
* frame sampling results
* candidate frame filtering results
* a real VLM result from a known candidate frame

But I do not have a complete final visual pass over all candidate frames.

Calculating full precision or recall from only these partial outputs would make the result look more complete than it actually is.

There is also an important example of why simple overlap can be misleading.

The audio model incorrectly labelled informational speech from approximately:

```text
28.2 s → 41.2 s
```

as an advertisement.

However, the real visual Avis advertisement is already present during that time.

A metric based only on timestamp overlap could therefore make this audio detection look partly correct even though the audio model made the wrong semantic decision.

For this reason I report this as a false-positive reasoning failure rather than presenting a misleading score.

---

# 6. YouTube Short — Main Evaluation

The YouTube Short produced the most useful evaluation results.

The main content is a lady explaining the health benefits of a leaf.

My manual ground truth says that this spoken discussion is informational content.

The actual advertisement is mainly visual.

From approximately:

```text
4.0 s → 63.8 s
```

a promotional panel for Avis Vascular Center appears on the screen.

The visual advertisement includes signals such as:

* Avis Vascular Center
* ₹4500
* phone number
* promotional Telugu text
* business information

This test showed why I need both audio and visual signals.

---

# 7. Visual Sampling Result

The Short was approximately:

```text
63.88 seconds
```

The original video contained:

```text
1597 frames
```

I sampled every:

```text
0.5 seconds
```

This produced:

```text
128 sampled frames
```

Sending all 128 frames to the vision model would be too expensive in terms of local processing time.

I therefore used OpenCV frame-difference filtering and a periodic backup frame.

This reduced:

```text
128 sampled frames
```

to:

```text
14 candidate frames
```

This filtering worked as intended and reduced the number of expensive VLM calls.

One of the selected frames was:

```text
frame_10.0.jpg
```

I already knew from manual review that this frame contained the real Avis advertisement.

The VLM correctly identified the advertisement and extracted visual evidence including:

* Avis Vascular Center
* ₹4500
* phone number
* promotional text

This confirmed that the visual model can detect the important advertisement in this Short.

---

# 8. Failure Case 1 — Audio False Positive

## What happened

The woman in the Short was explaining the health benefits of a leaf.

The text LLM classified part of this speech as an advertisement.

The detected interval was approximately:

```text
28.2 s → 41.2 s
```

The model gave this classification high confidence.

My manual review says that the speech itself was informational rather than promotional.

## Root Cause

The model confused positive language about the benefits of something with commercial advertising intent.

Talking positively about a product, ingredient, treatment, or topic does not automatically mean that the speaker is selling it.

## Design Change

Because of this failure, I made the fusion logic stricter for Shorts and Reels.

For these formats:

```text
visual evidence = primary
audio evidence = supporting
```

An LLM-only audio guess does not automatically create a final ad segment.

Strong audio rules such as:

* sponsored by
* use code
* discount code
* paid partnership

can still provide independent evidence.

---

# 9. Failure Case 2 — Visual Branding False Positive

## What happened

The visual model classified normal doctor/business or channel branding as `self_promo` on an early frame.

My manual judgement was that the visible branding by itself was not enough to call it an advertisement.

## Root Cause

A vision-language model can see a business name or logo and assume that it has promotional intent.

However, some branding is simply part of the normal video layout.

## Change

I made the visual prompt more explicit.

A persistent:

* watermark
* channel logo
* creator logo
* normal business identity

should not automatically count as an advertisement.

I look for stronger promotional evidence such as:

* price
* offer
* contact number
* booking instruction
* commercial message
* sponsor wording
* call to action

---

# 10. Failure Case 3 — Empty VLM Response

## What happened

During testing, `qwen3-vl:4b` sometimes returned an empty response:

```text
''
```

The code originally expected every model response to contain valid JSON.

When the response was empty, JSON parsing failed.

## Root Cause

The pipeline assumed that model output would always be valid.

That is not safe when working with language or vision models.

## Fix

I added a guard for empty responses.

Instead of allowing the complete pipeline to crash, the failed visual classification can return a safe result with:

```text
is_ad = false
confidence = 0
```

and an explanation that the model returned an empty response.

---

# 11. Failure Case 4 — Multi-Image Context Limit

I also tried to reduce latency by sending all 14 candidate images in one VLM request.

This did not work.

The request required approximately:

```text
28,992 tokens
```

while the available model context was approximately:

```text
4,096 tokens
```

The request therefore exceeded the context limit.

Possible improvements include:

* smaller image batches
* contact sheets
* lower-resolution input
* larger-context model
* stronger candidate filtering

I did not add these changes before submission because I wanted to avoid introducing more complexity without enough time to test it properly.

---

# 12. Latency

Latency is currently the largest limitation in my implementation.

Even after reducing the Short from:

```text
128 sampled frames
```

to:

```text
14 candidate frames
```

the local vision model remains slow.

I am running:

```text
qwen3-vl:4b
```

locally through Ollama on CPU.

A single visual candidate can take several minutes.

During testing, processing only a few candidate frames could take more than ten minutes.

This means that running the complete visual pass over all 14 candidates is currently too slow for a convenient live demonstration.

The OpenCV filtering significantly reduced unnecessary work, but the VLM inference itself is still the main bottleneck.

---

# 13. Cost

The current implementation uses local models:

* faster-whisper
* qwen3:4b-instruct through Ollama
* qwen3-vl:4b through Ollama

Therefore I do not have a hosted model API charge for the current tests.

```text
estimated_cost_usd = 0
```

This does not mean that processing is completely free.

This value does not include:

* electricity
* hardware
* CPU processing time
* possible future GPU cost

My current trade-off is therefore:

```text
low hosted API cost
but
high local inference latency
```

---

# 14. Other Test Videos

## Long-form YouTube

I manually labelled the long-form video.

A clear Vista Imaging Diagnostics preroll advertisement appears at the beginning.

I did not complete a full end-to-end system evaluation of this 46-minute video.

My architecture gives more importance to audio for long-form content because sponsor reads can be spoken while the visual scene remains almost unchanged.

---

## Instagram Reel 1

I manually labelled the Asian Dental Official Reel.

It contains informational dental content followed by a clear self-promotional section near the end.

The complete pipeline was not run on this Reel before submission.

---

## Instagram Reel 2

I manually labelled the Clinique K Dental Reel.

The clear promotional section is the full-screen clinic promotion near the end.

I did not automatically treat the complete doctor-patient discussion as an advertisement because the commercial intent of the earlier discussion is less clear.

The complete pipeline was not run on this Reel before submission.

---

## Live Stream

I manually observed approximately 30 minutes of the supplied Asia Net News live stream.

I observed:

* persistent Schneider Electric branding
* an embedded Subscribe Now channel promotion
* Edimannickal Golden Diamonds branding associated with a panelist feed
* other changing advertisements

I did not record exact boundaries for all changing advertisements, so I did not invent timestamps.

I also saw a Groww advertisement inserted by YouTube during playback.

I did not include this as part of the underlying stream because it appeared to be a platform-served advertisement rather than part of the actual live media.

A complete production live-stream processing path is not implemented in the current submission.

---

# 15. Demonstration Limitation

I do not want to present the local VLM as if it runs quickly when it does not.

For the recording, I use a real candidate frame from the tested YouTube Short.

The selected frame is one where I manually know the Avis advertisement is visible.

I run the actual visual classification function on that frame and show the resulting JSON.

I then explain how the visual and audio detections are intended to enter the fusion step.

The complete candidate-frame loop uses the same visual-classification function.

The reason I do not wait for all candidate frames during the recording is the high local CPU inference latency.

This is a limitation of the current implementation, not something I hide from the evaluation.

---

# 16. Evaluation Summary

The main finding from my testing is that the useful signal changes depending on the video type.

The Short demonstrated this clearly:

```text
Audio semantic model
→ informational health discussion
→ incorrect ad classification

Visual model
→ Avis promotional panel
→ correctly identified advertisement
```

This supports the decision to use:

```text
Long-form:
audio primary

Shorts / Reels:
visual primary
```

The main limitations I observed are:

* local VLM inference is slow
* visual boundaries are currently approximate
* text models can confuse informational language with promotional intent
* vision models can confuse normal branding with self-promotion
* model responses can be empty or malformed
* large multi-image requests can exceed the model context
* live-stream handling is not fully implemented
* the complete five-video system evaluation was not finished before submission

I prefer to report these limitations directly rather than create evaluation numbers that I did not measure.

With more evaluation time, I would run the final pipeline on all five test videos and calculate:

* precision
* recall
* F1
* segment IoU
* start boundary error
* end boundary error

against the manual `ground_truth.json`.

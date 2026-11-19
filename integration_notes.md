# Lab 3 — Concepts and Clarifications

Notes on what the spectra, parameters and noise files **mean**, collected from the questions asked while working with the app. This is about understanding, not about how the app is built (see `design.md` for that).

## How to read this document

Every claim is tagged so you can tell how much to trust it:

| Tag | Meaning |
|---|---|
| **[Measured]** | Computed directly from your files in `data/`. Reproducible. |
| **[Observed]** | Read off a screenshot you sent. It is what the plot shows, but a plot reading can be off. |
| **[Concept]** | Standard signal-processing theory. Not specific to your files. |
| **[Not verified]** | A reasonable expectation I have **not** checked. Treat it as a hypothesis. |

**How the measurements were made.** The clean originals (`music.wav`, `c_scale.wav`) are in `data/`. Subtracting a clean file from its noisy version gives the noise exactly. Filter quality is scored as **SNR in dB against the clean file** (higher is better).

**Limits of that method:**
- It is only possible because the lab supplied the clean files.
- SNR is a number, not the same as "sounds better". Listening is still required.
- Only the settings I tried were tested. "Best found" does not mean "best possible".
- All sample values are on the app's −1..1 scale. A 16-bit value such as 5000 is 5000 / 32768 ≈ 0.153.

---

## Part A — Reading the spectrum

### A1. What the floor (dB) setting means [Concept + Observed]

The dB axis is **relative**. The tallest point in the view is defined as 0 dB. Every other point is plotted as 10·log10(P / P_max).

| dB | Power vs. the peak | Amplitude vs. the peak |
|---|---|---|
| 0 | the peak itself | the peak itself |
| −20 | 1/100 | 1/10 |
| −40 | 1/10,000 | 1/100 |
| −60 | 1/1,000,000 | 1/1000 |

The **floor** is the lowest level you want to see. Anything quieter is drawn *at* the floor. In the `c_scale` screenshot (floor −29) the flat line on both sides of the peak is clipped data, not real zero.

Why it exists:
1. Bins with exactly zero power would be minus infinity on a log scale.
2. It sets the bottom of the y-axis (and the blue end of the spectrogram colour bar).

The floor only changes the picture, never the computed data.

**It can hide noise [Observed].** In `c_scale_p1r5000.wav` at a floor of −40 dB the background was flat blue, and the notes looked clean. At about −85 dB a speckled haze across all frequencies appeared. If you are hunting for noise, use a floor of −60 to −85.

### A2. Frequency bins [Concept]

The transform cannot measure every frequency. It sorts energy into evenly spaced slots called **bins**:

- Bin k is centred at **f = k · Fs / N**.
- Bin width (frequency resolution) = **Fs / N**.
- Block duration = **N / Fs** seconds.
- A bin is a bucket, not an exact frequency. A tone between two bins spreads over both.

| Fs | N | Bin width | Block length |
|---|---|---|---|
| 16000 | 128 | 125 Hz | 8 ms |
| 16000 | 2048 | 7.8 Hz | 128 ms |
| 16000 | 8192 | 1.95 Hz | 512 ms |

### A3. The block-size trade-off [Concept, matches Observed]

Larger N gives finer frequency detail but coarser timing, and smaller N does the opposite. You cannot get both.

**Observed on `music.wav`:**
- N = 8192: thin, sharp horizontal lines, but the picture is built from half-second tiles, so you cannot tell when inside a tile a note started.
- N = 128: broad, chunky bands (only 16 rows in 0–2000 Hz), but events such as the quiet gap near 4 s show with sharp timing.

For music, N around 1024–2048 is a reasonable compromise [Concept].

### A4. Windows (Rectangular, Hamming, Hanning) [Concept]

Each block is multiplied by a window before the transform.
- **Rectangular** (no shaping): narrowest peak, but the most **leakage**: energy of a strong tone smears into neighbouring bins, forming a skirt around the peak.
- **Hamming / Hanning**: taper the block edges, so the skirt is smaller and the peak slightly wider.

The app divides power by sum(w²)/N, so levels are comparable across windows.

[Not verified] I have not measured the leakage difference on your files. The `c_scale` single-block screenshot with a Rectangular window shows a wide skirt around the peak. Compare it yourself with Hanning for lab step 4.

### A5. View modes and scales [Concept]

| Setting | Meaning |
|---|---|
| Single block | One block's spectrum. Previous/Next steps through the file. |
| Average of all blocks | Mean of the blocks' **linear** power, then converted to dB. dB values are never averaged. Best for steady noise. |
| Spectrogram | Frequency against time, colour is level (blue = floor, red = 0 dB). |
| Linear / dB | Linear shows only the strongest peaks. dB shows weak components. |
| Lower / Upper freq | Display zoom only. The computed data is unchanged. |

### A6. What a spectrogram shows [Concept + Observed]

- **Horizontal line:** a sustained tone. A stable note stays at one frequency.
- **Several lines stacked:** harmonics (multiples of the fundamental) and/or several notes at once.
- **Vertical stripe across many frequencies:** a short, broadband event such as a click or onset.
- **The vertical edges every block length** are block boundaries, not necessarily real changes.

**Observed on `c_scale`:** each note is one horizontal line, stepping upward about once per second over 8 s, with a vertical smear at each step. A block that straddles two notes contains both frequencies, which explains smearing at the transitions [Concept]. Whether those smears are partly clicks from the abrupt note change in the recording [Not verified] — compare with the clean `c_scale.wav` at the same settings.

### A7. DC offset [Measured]

In `music_p01r500.wav` (and equally in the clean `music.wav`) a constant stripe at the bottom of every spectrogram:

- The average sample value is **0.0055**, not 0.
- The 0 Hz bin and the 7.8 Hz bin sit at about **−23 dB and −26 dB** relative to the loudest point. The bins just above are about −55 dB.
- With a Hanning window the offset leaks into the bin next to 0 Hz, so the stripe is about two bins tall (0–15.6 Hz).
- It is identical in the clean file, so it is **not noise**, and it is inaudible.

The bright band at 60–130 Hz is music: the strongest average bins in the file are at **70.3, 62.5, 78.1 and 93.8 Hz** (bass), plus 742 Hz.

---

## Part B — What each noise file actually is [Measured]

The file-name codes were first read as guesses. Below is what the difference (noisy − clean) shows.

### B1. `p` files: random noise on a fraction of samples

| File | Samples with added noise | Largest noise value | SNR before filtering |
|---|---|---|---|
| `music_p01r500` | 0.98 % | 0.015 | 30.0 dB |
| `music_p05r2000` | 4.9 % | 0.061 | 11.0 dB |
| `music_p1r5000` | 9.8 % | 0.153 | −0.1 dB |
| `c_scale_p1r5000` | 10.1 % | 0.153 | 24.9 dB |

- `p01` ≈ 1 %, `p05` ≈ 5 %, `p1` ≈ 10 % of samples are hit.
- `r` is the maximum size: 500 / 32768 = 0.015, 2000 / 32768 = 0.061, 5000 / 32768 = 0.153.
- The noise values are random up to that size (the median is about half of the maximum), not constant spikes.
- This noise is spread evenly over frequency. In a spectrogram it looks like a flat haze. **Spectra alone cannot tell this noise from continuous white noise**; the time-domain difference can.

### B2. `s` files: one pure sine

| File | Noise frequency | Peak size | Noise power within ±5 Hz of that frequency |
|---|---|---|---|
| `music_s120r7000` | 120 Hz | 0.214 | 100 % |
| `music_s350r5000` | 350 Hz | 0.153 | 100 % |
| `c_scale_s400r5000` | 400 Hz | 0.153 | 100 % |

The number after `s` is the exact frequency, and `r` is the sine's amplitude (7000 / 32768 = 0.214, 5000 / 32768 = 0.153). The `music_s` files have an SNR of **−14.8 and −11.9 dB**: the sine is louder than the music. In `c_scale_s400r5000` the SNR is 13.2 dB.

### B3. `nb` files: band-limited noise

| File | Stated band | Measured band (within 10 dB of the peak) | SNR before |
|---|---|---|---|
| `music_nb400-700r2000` | 400–700 Hz | 399–702 Hz | −2.2 dB |
| `music_nb5000-7999r3000` | 5000–7999 Hz | 4927–7999 Hz | −5.7 dB |
| `c_scale_nb700-2000r8000` | 700–2000 Hz | 692–2020 Hz | 10.9 dB |

The numbers after `nb` are the band edges in Hz. The meaning of `r` for these files was **not determined**.

**Observed** in your spectrogram of `music_nb400-700r2000`: a broad red band from about 400 to 700 Hz runs through the whole file, which matches the measurement above.

---

## Part C — Choosing a filter [Measured]

### C1. Which noise goes with which filter [Concept, supported by the measurements below]

| Noise | Where it shows in the spectrum | Filter |
|---|---|---|
| `p` (random on a fraction of samples) | flat haze everywhere | Median with threshold |
| `s` (one sine) | one thin line | Notch, narrow band around that frequency |
| `nb` (a band) | a raised block over the band | Notch over the band, or lowpass if the band lies above the music |

### C2. Median with threshold

How it works: each sample is compared to the median of its neighbours. If it differs from the median by more than the **threshold**, it is replaced by the median. Otherwise it stays. The **window** is how many samples form the neighbourhood (odd).

| File | SNR before | Setting tried | SNR after |
|---|---|---|---|
| `music_p01r500` | 30.0 | window 3, threshold 0.01 | **18.2 (worse)** |
| | | window 3, threshold 0.1 (almost no change) | 30.0 |
| `music_p05r2000` | 11.0 | window 3, threshold 0.02 (best found) | 17.0 |
| | | window 3, threshold 0.05 | 12.4 |
| | | window 3, threshold 0.001 (your choice) | 15.0 |
| | | window 7, threshold 0.001 (the first file saved in `Submission/`) | 11.7 |
| `music_p1r5000` | −0.1 | window 5, threshold 0.01 | 12.6 |
| | | window 7, threshold 0.03 (best found) | 14.2 |
| `c_scale_p1r5000` | 24.9 | window 3, threshold 0 to 0.01 (best median found) | 27.7 |
| | | **lowpass 1000 Hz, order 4 (your choice)** | **33.9** |

What this means:
- **`music_p01r500` cannot be improved by this filter.** It is already 30 dB clean, and its noise (≤ 0.015) is smaller than the music's own sample-to-sample changes. The filter cannot tell them apart and damages real music. A valid conclusion for a write-up is that this file is too clean to benefit, supported by this measurement.
- The default threshold in the app (0.05) is too high for `music_p05r2000` and `c_scale_p1r5000`.
- For `c_scale_p1r5000` the gain from the median is small (+2.8 dB). 10 % of samples are hit, so neighbouring bad samples sometimes survive a window-3 median.
- **For `c_scale_p1r5000` a lowpass is better than the median (33.9 dB against 27.7 dB).** The noise is spread over all frequencies and every note is below 530 Hz, so cutting everything above 1000 Hz removes most of the noise. A median filter is not automatically the best choice for a `p` file.
- For `music_p05r2000` your window 3 with threshold 0.001 (15.0 dB) beats window 7 with the same threshold (11.7 dB). A threshold of 0.02 reached 17.0 dB in my search.
- I searched windows 3, 5 and 7 and a few thresholds only.

### C3. Notch (band-reject)

Parameters:
- **Lower / Upper (Hz):** edges of the blocked band. The rule is `0 < lower < upper < Fs/2` (here Fs/2 = 8000 Hz). They cannot be equal: that would be a band of zero width.
- **Order:** how steep the edges are. The result is not a brick wall. Attenuation is deepest in the middle of the band and weaker towards the edges.

**Sine noise:**

| File | SNR before | Notch tried | SNR after |
|---|---|---|---|
| `c_scale_s400r5000` | 13.2 | 399–401, order 2 | **34.6** |
| | | 398–402, order 2 | 32.9 |
| | | 395–405, order 4 | 27.3 |
| `music_s350r5000` | −11.9 | 349–351, order 2 | 13.7 |
| | | 345–355, order 4 | **17.8** |
| `music_s120r7000` | −14.8 | 119–121, order 2 | 11.7 |
| | | 115–125, order 4 | **16.1** |

Two opposite trends:
- In `c_scale` the **narrowest** notch is best, because the scale's notes (such as 392 Hz and 440 Hz) are close to 400 Hz, and a wider notch cuts into them.
- In the `music_s` files the **wider** notch of the three tried is best, because a very narrow notch leaves part of the sine behind. I did not test widths beyond ±5 Hz.

So the best width depends on the file and on how much music lies near the sine.

**Narrowband noise:**

| File | SNR before | Filter tried | SNR after |
|---|---|---|---|
| `music_nb400-700r2000` | −2.2 | notch 390–710, order 8 | 9.6 |
| | | notch 400–700, order 4 | 9.0 |
| | | lowpass (800 to 4500 Hz) | about −2 (no help) |
| `music_nb5000-7999r3000` | −5.7 | notch 5000–7990, order 8 | 12.8 |
| | | lowpass 4500, order 4 | **17.6** |
| `c_scale_nb700-2000r8000` | 10.9 | notch 670–2030, order 8 | **32.8** |
| | | notch 700–2000, order 4 | 28.1 |
| | | lowpass 600 | 19.0 |

What this means:
- When the noise band lies **above** the music (`nb5000-7999`), a **lowpass** beat the notch in my tests. A notch also has to stop at 7990 Hz (the upper edge must be below 8000), so the last few Hz of noise survive.
- When the band sits **inside** the music's range (`music_nb400-700`), a lowpass does not help, and only a notch helps. The result is about 9 dB, not a clean result, because the music inside the band is removed together with the noise.
- A higher order helped on the wide bands in these tests.

### C4. Images [Measured]

**The noise.** Random values added to a fraction of the colour values, in each channel: up to about 10 % for `p1` and 5 % for `p05` (9.8 % and 4.9 % in the photo files). The largest noise value is `r` / 255 (200 gives 0.78, 100 gives 0.39). It shows as single coloured dots.

**Scores.** PSNR in dB against the clean image, whole image, peak value 1 (higher is better):

| File | Noisy | Median 3 | Median 5 | Gaussian σ=1 | Gaussian σ=2 |
|---|---|---|---|---|---|
| `photo_p1_r200` | 19.2 | **29.6** | 25.7 | 25.2 | 22.6 |
| `photo_p05_r100` | 27.3 | **30.4** | 25.9 | 27.1 | 23.0 |
| `text_p1_r200` | 19.8 | **25.7** | 19.3 | 22.3 | 19.0 |
| `text_p05_r100` | **28.7** | 26.0 | 19.2 | 23.3 | 19.2 |

What this means:
- **Median 3 is the best of these four filters on three images,** which matches what you saw.
- **On `text_p05_r100` median 3 scores below the noisy image.** The few noisy dots do less damage than the thin letter strokes lose to the filter. Visually the dots are gone, so the score is only a guide. A light Gaussian (σ=0.5) scored 29.5 dB there, the best number I found.
- **Larger kernels are worse.** Median 5 scores below median 3 on every image, and Gaussian scores fall as sigma grows. This agrees with your observation that both are sensitive to the size.
- **Gaussian blur does not remove an isolated noisy pixel.** It spreads it into its neighbours, so faint speckle remains while detail is already lost. Median suits this noise because the noise is impulsive.
- **The text suffers more than the photo.** Thin, high-contrast strokes are damaged sooner by any filter that mixes neighbouring pixels.

[Observed] In the crop comparisons, median 3 softens skin texture and braids in the photo and thins the letters in the text.

### C5. The settings you chose, scored [Measured]

SNR in dB against the clean file, using the saved files in `Submission/` where they exist:

| File | Your filter | Before | After | Comment |
|---|---|---|---|---|
| `c_scale_nb700-2000r8000` | lowpass 600 Hz | 10.9 | 19.0 | Works. A notch over 670–2030 Hz, order 8, reached 32.8. |
| `c_scale_p1r5000` | lowpass 1000 Hz | 24.9 | 33.9 | Better than the median (27.7). |
| `c_scale_s400r5000` | notch 390–410 Hz | 13.2 | **10.4** | Removes the tone but also weakens the 392 Hz note, which lies inside the band. A 399–401 Hz notch scored 34.0. |
| `music_nb400-700r2000` | notch 400–700 Hz | −2.2 | 9.0 | Works, but the music in the band goes too. |
| `music_nb5000-7999r3000` | lowpass 3000 Hz | −5.7 | 15.8 | Works. Lowpass 4000 Hz scored 17.6, and 400 Hz only 4.5. |
| `music_p01r500` | median, window 3, threshold 0.01 | 30.0 | **18.2** | Worse than the original. See C2. |
| `music_p05r2000` | median, window 3, threshold 0.001 | 11.0 | 15.0 | Works. |
| `music_s120r7000` | notch 100–200 Hz | −14.8 | 10.2 | Works. The band is wider than the tone (120 Hz). |
| `music_s350r5000` | notch 320–400 Hz | −11.9 | 13.8 | Works. |

Not scored: `music_p1r5000` (no saved result).

---

## Part D — Errors and surprises you hit, and what they meant

| What you saw | What it meant |
|---|---|
| Notch failed with Lower = 0 | The notch needs a lower edge above 0 Hz. A band from 0 up to 200 Hz is a **highpass** job, so a Highpass filter was added. For the DC stripe a cutoff of about 20 Hz is enough. A cutoff of 200 Hz would also cut the bass line (the strongest bins are at 62–94 Hz). |
| `RuntimeError: Cannot play asynchronously from memory` | A bug in the app's playback code: Windows' sound API cannot play in the background from an in-memory buffer. Fixed by playing from a temporary file. |
| Images looked grey in the Noise Filter tab | The files are colour (RGB) but the loader converted them to grey. The Noise Filter tab now keeps colour. The Power Spectrum tab still analyses a grey version, as its requirements say. |
| The median filter "didn't work" on `music_p01r500` | See C2. The file is too clean for this filter to help, so the result you saw was correct. |
| Noise invisible in the spectrogram | The floor was too high (A1). |

---

## Part E — Corrections to my earlier answers

I got these wrong or imprecise earlier:

1. **Sampling frequency of `music.wav`.** I guessed about 10 kHz from a 0–5000 Hz axis. That axis was your Upper-frequency setting. Fs is **16000 Hz** and the file is 10 s long. The qualitative conclusions held, but the block lengths I quoted were off.
2. **Meaning of `p`.** I assumed 0.1 / 0.5 / 1 %. Measured: **1 / 5 / 10 %** of the samples (B1).
3. **"Pops are isolated spikes."** Measured: random-sized noise on a fraction of samples, not fixed spikes.
4. **Median threshold of 0.005–0.01 for `music_p01r500`.** This was wrong advice: it lowered SNR from 30 to about 17–18 dB (C2).
5. **"Use a narrow notch."** Too general. It is best for `c_scale_s400`, but wider was better for the `music_s` files (C3).
6. **Notch for `nb5000-7999`.** I suggested the notch without testing it. In the tests a lowpass at 4500 Hz was better (C3).
7. **Median as the first choice for `c_scale_p1r5000`.** I recommended the median filter and a lowpass second. Your lowpass at 1000 Hz scored 33.9 dB against 27.7 dB for the best median (C2).
8. **Image filtering.** I wrote that nothing was measured and only gave expectations. It is now measured (C4), and `text_p05_r100` turned out to be the exception where median 3 scores below the noisy image.
9. **Starting threshold for `c_scale_p1r5000`.** I suggested 0.02–0.05. The best median setting found was 0 to 0.01.

---

## Part F — What has not been verified

- **Listening.** I have not heard any of these files. The SNR numbers do not replace your own judgement of whether a result sounds better.
- **Lab Part I answers.** The statements about note transitions, the effect of different windows, and block size are standard theory plus your screenshots. Confirm them against your own plots, and include your spectrograms in the submission.
- **Image filtering.** Scored with PSNR (C4), which is only a guide. Judge the pictures by eye as well.
- **`music_p1r5000`.** No result has been saved or scored for it.
- **Other settings.** Filter settings outside the ranges listed in the tables might do better.
- **The meaning of `r` in the `nb` files.**
- **Whether the vertical stripes in `c_scale_p1r5000` at 1, 2, … 7 s are caused by note changes or by noise.** They line up with the note changes, which suggests the music, but this was not tested against the clean file.

# Lab 3 — Interrogation Log

A record of the questions asked during this working session about **what is happening** in the spectra, parameters and noise files, with a short answer and an honest status for each.

## About this log

- **Source:** reconstructed from the conversation. Questions are quoted or closely paraphrased, with spelling lightly cleaned. Nothing was added that was not asked.
- **Scope:** only the questions about understanding. Requests to build or change the app are not listed. The few app problems you reported are in the appendix, only because they turned out to be informative.
- **Entries marked "no question typed"** are screenshots you sent without a question. I responded to them, so they are logged, but the interpretation of what you wanted is mine.
- **Status labels:**

| Label | Meaning |
|---|---|
| **Held up** | Later measurements or checks agree with the answer. |
| **Refined** | Mostly right, but later measurement changed or sharpened it. |
| **Corrected** | The answer was wrong or misleading and was fixed later. |
| **Theory only** | Standard signal-processing concepts, not tested on your files. |

- Detailed numbers and tables are in `integration_notes.md`. References like "Notes C2" point to its sections.

---

## Q1. What do the parameters mean, especially Floor?

**You asked:** to explain the parameters you can configure, because you were struggling to understand the **floor** parameter, and to talk more about the other parameters too.

**You were looking at:** `c_scale.wav`, single block (block 1 of 63), N = 2048, Rectangular window, floor −29 dB, frequency range 0–1000 Hz. One peak near 260 Hz.

**Short answer:**
- dB is **relative**: the tallest point is 0 dB, everything else is how far below it.
- The **floor** is the lowest level shown. Anything quieter is drawn at the floor. The flat line at −29 dB in your plot is clipped, not true silence.
- A higher floor shows only strong content. A lower floor reveals faint things such as leakage and noise.
- It changes only the display, not the computed data.
- Other parameters covered: N (frequency resolution Fs/N = 7.8 Hz, block length 128 ms here), Fs (read from the WAV header), window type, view modes, linear vs dB, the frequency range (zoom only), channel and row/column (not relevant to this file).

**Status:** Held up (theory). The peak near 260 Hz was identified as middle C by reading the axis.

---

## Q2. How do I interpret the `music.wav` spectrogram (N = 8192)?

**You asked:** (working on Part I, step 5) you see a spectrogram with "a signal with ranging frequencies" and needed help understanding the graph and how to interpret it.

**You were looking at:** `music.wav`, spectrogram, N = 8192, Rectangular, y-axis 0–5000 Hz, x-axis about 10 s.

**Short answer:**
- A horizontal streak is a sustained note. Several streaks at once are harmonics of one note and/or several notes together, not a single sweeping signal.
- The vertical edges every block length are block boundaries, not necessarily note changes.
- Large N gives thin lines but coarse timing.
- Energy is concentrated at lower frequencies. A quiet stretch appears near 4–6 s.

**Status:** **Refined.** The qualitative reading holds, but I assumed Fs ≈ 10 kHz from the axis. That axis was only your Upper-frequency setting. Fs is 16000 Hz, so the block length was about 0.51 s, not 0.82 s (see Q3).

---

## Q3. (No question typed) The same file at N = 128

**You sent:** a spectrogram of `music.wav` at N = 128, 0–2000 Hz, 1250 blocks.

**Short answer:**
- This is where I corrected the Fs mistake from Q2: Fs = 16000 Hz, the file is 10 s long.
- At N = 128 the bin width is 125 Hz and the block is 8 ms. Bands are broad (16 rows in 0–2000 Hz), but events show with sharp timing.
- Features read from the plot: a persistent bright band around 200–250 Hz, a drop-out near 4.1 s, a burst near 8.1 s at about 700 Hz, a patch near 1 s at about 850 Hz.
- The speckled vertical striping: short blocks with a Rectangular window give a noisy estimate.
- Frames the lab's question "what effect does block size have".

**Status:** Held up. The numbers follow from Fs/N and N/Fs. The feature timings are read off the plot, not measured.

---

## Q4. What does the frequency bin mean?

**You asked:** "what does the frequency bin mean in this context".

**Short answer:**
- A bin is one slot of the spectrum. Bin k is centred at k·Fs/N, and bin width is Fs/N.
- It is a bucket, not an exact frequency: a tone between two bins spreads over both.
- Finer bins require longer blocks, which costs time resolution.
- Example with Fs = 16000, N = 128: bins at 0, 125, 250 Hz, … up to 8000 Hz (65 bins).

**Status:** Held up (theory). See Notes A2.

---

## Q5. Is a median filter right for `c_scale_p1r5000`, and what do window and threshold mean?

**You asked:** how to filter the noise in this file. You thought a median filter might work and it looked like white noise, but you weren't sure, and didn't understand the **window** and **threshold** parameters. You asked for my advice.

**You were looking at:** `c_scale_p1r5000.wav`, spectrogram, N = 2048, Hanning, floor −40 dB. Clean notes only; the noise was invisible.

**Short answer:**
- The −40 dB floor was hiding the noise. Lower it to about −80 to see it.
- Spectra cannot distinguish pops from continuous white noise; look at the waveform for spikes.
- The filename suggests pops, so a median filter is the right tool.
- Window = how many neighbouring samples form the median (odd; start at 3 or 5). Threshold = how far a sample must differ from the median to be replaced.
- Suggested start: window 5, threshold 0.02–0.05.

**Status:** **Refined.**
- Measured: the noise is random-sized values on about 10 % of samples, not isolated spikes.
- The best setting found for this file was window 3, threshold 0–0.01, a gain of 2.8 dB (SNR 24.9 → 27.7). Window 5 with threshold 0.05 also helped (27.0 dB).
- The advice to use the median held up, and my starting values were slightly high.
- Notes B1, C2.

---

## Q6. After seeing the noise, "notch is an alternative right?"

**You asked:** whether a notch filter is an alternative. **You were looking at:** the same file at floor about −85 dB, showing a haze at all frequencies.

**Short answer:**
- A notch removes a narrow band. This noise is spread over all frequencies, so a notch does not fit.
- The notch belongs to the `s` (sine) and `nb` (band) files.
- The vertical bars at 1, 2, … 7 s are probably clicks at the note changes (part of the music), because pops would not line up with exact seconds.
- The median is the first choice for this file; a lowpass is the second.

**Status:** **Theory only** for "notch doesn't fit" (I never ran a notch on a `p` file). **Not verified:** that the vertical bars come from the note changes. That needs a comparison with the clean `c_scale.wav` at the same settings.

---

## Q7. What are the notch parameters? Can lower and upper be the same?

**You asked:** to help you understand the notch parameters, what "upper and lower frequency" mean, and whether they can be the same.

**Short answer:**
- Lower and Upper are the edges of the blocked band. Order sets how steep the edges are.
- They cannot be equal: a band of zero width is invalid. The rule is `0 < lower < upper < Fs/2`.
- For one tone use a narrow band around it. Narrower removes less music but must still contain the noise; wider is safer but cuts more music.
- The filter edges are gradual, not brick walls.
- I gave suggested edges per file, derived from the filenames.

**Status:** **Refined.**
- Measured: the `s` files really are a single sine at the stated frequency (120, 350, 400 Hz), and the `nb` bands match their stated edges.
- But "narrow is gentler" is not universal. For `c_scale_s400` the narrowest notch (399–401) was best (SNR 13.2 → 34.6). For `music_s350` and `music_s120` a wider notch (±5 Hz) did better than ±1 Hz.
- Notes B2, C3.

---

## Q8. "What do you think of this one?" — `music_nb400-700r2000`

**You sent:** two spectrograms (0–1000 Hz and 0–8000 Hz, Rectangular, N = 2048, floor about −77 dB).

**Short answer:**
- A broad red band from about 400–700 Hz runs through the whole file, which is the narrowband noise and matches the filename.
- It is louder than the music in that range. Music sits below (bass) and above (the patch near 750–800 Hz).
- Recommended: notch 400–700 Hz, order 4 to 6, verify the edges with Hanning. Lowpass is the wrong tool. The cost: music inside the band is removed too.

**Status:** **Held up.** Measured: the noise band is 399–702 Hz. Notch 400–700 raised SNR from −2.2 to about 9 dB (9.6 with 390–710, order 8). Lowpass did not help (about −2 dB). Notes B3, C3.

---

## Q9. "What do you think of this one?" — `music_p01r500`

**You sent:** two spectrograms (floor −100 dB, N = 2048, Rectangular).

**Short answer:**
- No band or line stands apart from the music, only a faint broadband haze. I could not pick out the noise from the plot.
- I read the vertical stripes (about 0.4, 0.7, 7 s) as music onsets, since the `nb400-700` file showed a stripe at about 7 s too.
- I guessed this was the mildest pop file, then advised a median with window 3 and a threshold of 0.005–0.01.

**Status:** **Corrected.**
- The "mildest file" guess was right: only about 1 % of samples are noisy, at most 0.015 in size, and SNR is already 30 dB.
- My threshold advice was **wrong**. Window 3, threshold 0.01 lowered SNR from 30.0 to 18.2 dB. The noise is smaller than the music's own sample-to-sample changes, so the filter damages real music. The best "setting" was to leave the file alone.
- The stripe interpretation is not verified. Notes C2.

---

## Q10. "Can you see the constant red at 0?"

**You asked:** whether I could see the constant red at 0 Hz in a Hanning spectrogram of `music_p01r500` (0–1000 Hz).

**Short answer:**
- I could not tell from the picture alone whether it was at exactly 0 Hz or in the 60–120 Hz region, so I measured the file.
- It is a **DC offset**: the average sample value is 0.0055, not 0. The 0 Hz and 7.8 Hz bins are at about −23 and −26 dB; the bins above are about −55 dB.
- The clean `music.wav` has the identical offset, so it is not noise and is inaudible.
- The bright band at 60–130 Hz is the music's bass (strongest bins 62–94 Hz).

**Status:** **Held up.** Measured. Notes A7.

---

## Q11. (No question typed) Zoom to 0–200 Hz

**You sent:** the same file zoomed to 0–200 Hz.

**Short answer:** the stripe is two bins tall (0–15.6 Hz), a constant ≈ −25 dB colour in every column, matching the measurement in Q10. The bass line is the red region at 60–130 Hz.

**Status:** Held up.

---

## Q12. "You mean for a median filter?"

**You asked:** whether my earlier advice ("a threshold of about 0.005–0.01 should be workable … try it and listen") was about the median filter.

**Short answer:** yes: the Threshold field of Median + threshold on `music_p01r500`, with window 3 (then 5). The threshold is the smallest deviation from the local median that gets a sample replaced. For `r5000` files I said to start around 0.03–0.05.

**Status:** **Corrected** for `music_p01r500` (see Q9: that threshold hurts). For the `r5000` files, measured best thresholds were about 0.03 (music) and 0–0.01 (`c_scale`).

---

## Q13. "Which of these can I use?" — `music_p05r2000`

**You said:** you got another file like the previous one, the previous attempt didn't work, and you were struggling to find which of these you can use. **You sent:** two spectrograms of `music_p05r2000` (Hanning, N = 2048, floor −84 dB).

**Short answer:** I stopped guessing from spectrograms and subtracted each clean file from its noisy version. Result (SNR before → best found):

| File | Before | After | Setting |
|---|---|---|---|
| `music_p01r500` | 30.0 dB | no gain | leave it alone |
| `music_p05r2000` | 11.0 dB | 17.0 dB | window 3, threshold 0.02 |
| `music_p1r5000` | −0.1 dB | 14.2 dB | window 7, threshold 0.03 |
| `c_scale_p1r5000` | 24.9 dB | 27.7 dB | window 3, threshold 0–0.01 |

Also found: `p` is the **fraction of samples** hit (1 %, 5 %, 10 %), not 0.1 / 0.5 / 1 %.

**Status:** **Held up** (measured). Caveats: SNR is measured against the clean file and does not equal "sounds better", and only windows 3, 5, 7 and a few thresholds were tried. Notes B1, C2.

---

## Appendix — App problems you reported that taught something

| What you reported | What was happening | Lesson |
|---|---|---|
| "Why am I getting this error when I try to play the audio" (`RuntimeError: Cannot play asynchronously from memory`) | An app bug: Windows' sound API cannot play in the background from a memory buffer. | Fixed by playing a temporary file. No effect on your analysis. |
| "Why am I experiencing a failure here" (Notch, Lower = 0) | The notch requires `0 < lower`. A band from 0 to 200 Hz is a highpass job. | A Highpass filter was added. A 20 Hz cutoff removes the DC offset; 200 Hz would cut the bass. |
| "I'm trying to work on the image but they seem to be in gray scale" | The image files are colour (RGB). The loader converted them to grey. | The Noise Filter tab now keeps colour. The Power Spectrum tab still uses grey, as its requirements say. |

---

## Summary of statuses

| Q | Topic | Status |
|---|---|---|
| 1 | Floor and parameters | Held up |
| 2 | `music.wav` N = 8192 | Refined (Fs guess was wrong) |
| 3 | `music.wav` N = 128 | Held up |
| 4 | Frequency bin | Held up |
| 5 | Median on `c_scale_p1r5000` | Refined |
| 6 | Is notch an alternative? | Theory only |
| 7 | Notch parameters | Refined |
| 8 | `music_nb400-700` | Held up |
| 9 | `music_p01r500` | **Corrected** |
| 10 | Constant red at 0 | Held up |
| 11 | Zoom 0–200 Hz | Held up |
| 12 | Median threshold clarification | **Corrected** (for p01r500) |
| 13 | Which file can be fixed | Held up (measured) |

**Still open (not verified):**
- Whether the vertical bars at note changes in `c_scale_p1r5000` come from the music rather than the noise (compare with the clean `c_scale.wav`).
- Everything about image filtering.
- Whether the filtered files actually sound better. Only listening can settle this.

# Noise Filter App — Requirements (v2)

> Supersedes `requirements_v1.md`. Source material: `requirements_v1.md`, `requirements_xform_powerspec_v2.txt` (the "PS spec"), and `Lab 3.pdf`.
> Items marked **[assumed]** are my inference from file names or silence in the sources — please confirm or correct them.

---

## 1. Purpose

A small Python/Tkinter desktop app for **understanding spectra and removing noise** from audio and images. It is the working tool for Lab 3 (CMU MSEAI, Processing Worlds Information).

The app has two tabs:

| Tab | Role | Build order |
|---|---|---|
| **Noise Filter** | Load a noisy file, apply a chosen filter with parameters, preview, and save the cleaned result. | **First** |
| **Power Spectrum** | Analyse a file's spectrum (single block, average, spectrogram) so you know *where* the noise lives before filtering. | Second, added from the PS spec |

The two tabs are linked by workflow: **look at the spectrum → decide the filter → filter → look at the spectrum again.**

### 1.1 Constraints
- Python with **Tkinter / ttk** UI. Nothing else for the UI.
- Libraries allowed: `numpy`, `scipy`, `pillow`, `matplotlib` (TkAgg, embedded via `FigureCanvasTkAgg`). **No other third-party packages.**
- The Power Spectrum tab lives in its own module, `powerspec_tab.py`, exposing `PowerSpecTab(ttk.Frame)`. DSP code is free of tkinter so it can be unit-tested (PS spec A3).

---

## 2. Lab context (what the app must let me do)

### Part I — Power spectrum exploration (clean files)
Files: `music.wav`, `c_scale.wav`.
1. Get the Power Spectrum tab into the app (dummy UI first, then integrate the PS spec).
2. Explore: change window, step block by block, average across file, adjust frequency range and dB floor, switch linear/dB.
3. **Spectrogram of `c_scale.wav`** with a y-range chosen so the notes are clearly visible. Answer in the write-up: Can individual notes be seen? What happens at note transitions? What does block size change?
4. **Single-block stepping of `c_scale.wav`** starting at N = 2048, comparing Rectangular / Hamming / Hanning. Can I see where the frequency changes? Which window do I prefer?
5. Spectrogram + a few block spectra of `music.wav`.

### Part II — Noise removal (noisy files)
- **Audio:** three noise types — random white-noise **pops**, **sinusoidal** noise, **narrowband white** noise. Inspect the noise in the Power Spectrum tab first, then filter. Candidate filters named in the lab: **median filter with threshold**, **narrowband band-reject (notch)**, **lowpass**. Deliverable: best `.wav` per noise file + filter type and parameters.
- **Images:** `photo.png` and `text.png` carry random white noise only. Remove it; deliverable: best result per image, plus a comment on how each filter behaves on each image type.
- Write-up: short, enough to follow what I did and why. Not a formal report.

---

## 3. Input files

| Group | File | What it is |
|---|---|---|
| Clean audio | `music.wav`, `c_scale.wav` | Reference recordings, no added noise |
| Noisy `c_scale` | `c_scale_nb700-2000r8000.wav` | Narrowband white noise, 700-2000 Hz, amplitude 8000 |
| | `c_scale_p1r5000.wav` | Pops, p = 1, amplitude 5000 |
| | `c_scale_s400r5000.wav` | Sinusoid at 400 Hz, amplitude 5000 |
| Noisy `music` | `music_nb400-700r2000.wav` | Narrowband, 400-700 Hz, amplitude 2000 |
| | `music_nb5000-7999r3000.wav` | Narrowband, 5000-7999 Hz, amplitude 3000 |
| | `music_p01r500.wav`, `music_p05r2000.wav`, `music_p1r5000.wav` | Pops, p = 01 / 05 / 1, amplitude 500 / 2000 / 5000 |
| | `music_s120r7000.wav`, `music_s350r5000.wav` | Sinusoid at 120 Hz (amp 7000) / 350 Hz (amp 5000) |
| Clean images | `photo.png`, `text.png` | Photo (smooth, natural) vs. text (sharp edges, two-tone) |
| Noisy images | `photo_p1_r200.bmp`, `photo_p05_r100.bmp`, `text_p1_r200.bmp`, `text_p05_r100.bmp` | White noise, p = 1 / 05, range 200 / 100 |

The files are named in the Canvas module listing; they are not yet in this folder. Place them in `data/`.

**File-name codes (decoded from the real names; the exact meaning of `p` and `r` is still [assumed]):**
- `nb<lo>-<hi>r<amp>` = **n**arrow**b**and white noise between `lo` and `hi` Hz, amplitude `r` (16-bit sample units).
- `p<prob>r<amp>` = **p**ops (random impulses). `p` is the pop density (`p01`, `p05`, `p1` is probably 0.1 %, 0.5 %, 1 %), `r` the pop amplitude.
- `s<freq>r<amp>` = **s**inusoidal noise at `freq` Hz, amplitude `r`.
- Images: `p<n>_r<n>` is the white-noise density and range.

The Power Spectrum tab confirms these: an `s400` file shows a spike at 400 Hz, `nb` files a raised plateau across their band, and `p` files a broad raised floor.

**Supported inputs**
- Audio: `.wav` — PCM 8/16/24/32-bit integer, 32-bit float, WAVE_FORMAT_EXTENSIBLE. Mono or stereo.
- Images: anything Pillow reads — png, jpg/jpeg, bmp, gif, tif/tiff.

**Outputs:** filtered `.wav` (same sample rate and channel count as the input) and filtered image (png/bmp), written through a save dialog.

---

## 4. Application shell

- Window title: **"Noise Filter"**.
- A `ttk.Notebook` with two tabs, in this order: **Noise Filter**, **Power Spectrum**.
- Switching tabs must not lose either tab's state (PS spec D2).
- Each tab has its **own log window**; messages for a tab go only to that tab's log (PS spec A4).
- Every file-selection field in the whole app (input *and* output, both tabs) is a **read-only, word-wrapping field**: long paths break mid-word onto extra lines and the wrap width follows the window width, so the full path is always visible (PS spec C1a, E13).
- Errors never crash the app and never leave a tab unusable: log `ERROR`, keep the previous state. No pop-up message boxes for tab-specific messages.
- Log line format: `HH:MM:SS LEVEL: message`, level `INFO` or `ERROR` (ERROR in red).

### 4.1 Integration plan (Lab Part I.1)
1. Build the shell with a **trivial dummy Noise Filter tab** (one button + log; "button pressed" is logged). This proves the host works.
2. Drop in `powerspec_tab.py` per the PS spec; the host changes only by an import and a `notebook.add(...)` call.
3. Replace the dummy tab with the real Noise Filter tab.

---

## 5. Tab 1 — Noise Filter

Built first, but the lab leaves its details open ("show me how you investigate"), so this is a proposed design; items are **[assumed]** unless the lab states them.

### 5.1 Layout
```
+-------------------------------------------------------------------+
| Input file        | Filter                | Parameters (per filter)|
| [Browse...][path] | ( ) Median + thresh.  | (changes with filter)  |
| Type: wav / image | ( ) Notch (band-rej.) |                        |
| Channel / info    | ( ) Lowpass           | [Apply] [Reset]        |
|                   | ( ) Other image filter| [Play before/after]    |
+-------------------------------------------------------------------+
|   Before (original)          |   After (filtered)                 |
|   waveform or image          |   waveform or image                |
+-------------------------------------------------------------------+
| [Save filtered...]                                                |
+-------------------------------------------------------------------+
| Log window                                                        |
+-------------------------------------------------------------------+
```

### 5.2 Audio filters
| Filter | Targets | Parameters |
|---|---|---|
| **Median with threshold** | Random pops (impulses) | Window length (odd, samples); threshold. A sample is replaced by the local median only if it deviates from it by more than the threshold, so clean samples are untouched. |
| **Notch / band-reject** | Sinusoidal noise and narrowband white noise | Centre frequency (Hz), bandwidth or low/high edges (Hz), filter order/length. Sinusoids need a narrow notch; `nb` noise needs a wide band. |
| **Lowpass** | Broadband hiss, high-frequency narrowband noise | Cutoff (Hz), order/length. |

- **One filter at a time (decided).** Apply runs the selected filter on the original input. Chaining is deferred; the design keeps a hook for it (see `design.md`).
- Design with `scipy.signal` (e.g. `iirnotch`/`butter` + `filtfilt`, or FIR with `firwin`); the specific design is an implementation choice recorded in `design.md`.
- Playback of before/after is **desirable** because the lab asks me to *listen* and judge "better". Without a non-stdlib audio dependency the options are `winsound` (Windows only) or none; see Open Question Q3.

### 5.3 Image filters
Noise here is white (per-pixel random), so candidates are:
- **Mean / Gaussian blur** (lowpass),
- **Median filter**,
- plus optionally one edge-preserving option.

Parameters: kernel size (odd), sigma for Gaussian. Show before/after side by side. The lab specifically asks what filters do differently on `photo.png` (smooth content) vs. `text.png` (sharp edges), so the tab should make same-parameter comparisons easy.

### 5.4 Behaviours
- Loading a file shows the original in the "Before" pane; Apply fills "After"; Reset clears it.
- Invalid parameters (even window, cutoff ≥ Nyquist, notch outside 0..Fs/2, etc.) → `ERROR` log, previous state kept.
- Saving always goes through a save dialog, suggests `<input>_filtered.wav|png`, logs `file saved: <path>` or `save cancelled`.
- A **"Send to Power Spectrum tab"** action loads the filtered result into the spectrum analyser for before/after comparison **[assumed — not in the lab, but it closes the loop]**.

---

## 6. Tab 2 — Power Spectrum

Full behaviour is defined by the **PS spec**, which is authoritative; this section summarises it and describes what the screen looks like. (References like *B9* or *C6* point to sections of that file.)

### 6.1 Screen (from the reference screenshot)

```
+- Noise Filter ---------------------------------------------------------- _ [] X -+
| [Noise Filter] [Power Spectrum]                                                  |
| +- Input file ---+ +- Parameters -------+ +- View ------------+ +- Scale ------+ |
| |[Browse..][path]| |Transform size N:512| |(o) Single block   | |( )Linear (o)dB| |
| | Channel: Left  | |Fs (Hz):  1         | |( ) Average of all | |Floor (dB): -40| |
| | (o)Row ( )Col  | |Window: Rectangular | |( ) Spectrogram    | |Lower freq: 0  | |
| |       Index: 1 | |                    | |[Prev] Block:1 of 0| |Upper freq: 0.5| |
| +----------------+ +--------------------+ |        [Next]     | |  [Save PNG...]| |
|                                           +-------------------+ +---------------+ |
|  +----------------------------------------------------------------------------+ |
|  |                                                                            | |
|  |              Load a .wav or image file (Browse...)                         | |
|  |                         (matplotlib plot area)                             | |
|  +----------------------------------------------------------------------------+ |
|  [home][<][>] [pan][zoom][cfg] [save]        <- matplotlib navigation toolbar    |
|  +----------------------------------------------------------------------------+ |
|  | 20:48:25 INFO: Power Spectrum tab ready. Defaults: N=512, Fs=1 Hz,         | |
|  | window=Rectangular, floor=-40 dB, scale=dB, mode=Single block, channel=Left| |
|  +----------------------------------------------------------------------------+ |
+----------------------------------------------------------------------------------+
```

Four `LabelFrame` groups run left to right across the top, then the plot, the toolbar, and the log. Controls that don't apply are **greyed, not hidden**.

### 6.2 Controls and their rules

| Group | Control | Behaviour |
|---|---|---|
| **Input file** | Browse… + wrapping read-only path | Opens `.wav`/image. Wraps long paths (C1a). |
| | Channel (Left / Right / Mono) | WAV only. Mono = (L+R)/2. Disabled for mono files and for images. |
| | Row / Column radios + Index spinbox | Image only (1-based). Disabled for WAV. *(Not needed for Lab 3 audio work, but the PS spec requires it.)* |
| **Parameters** | Transform size N | Drop-down 16 … 16384 (powers of 2), default **512**. |
| | Fs (Hz) | Editable for images, default 1; read-only from header for WAV. Must be > 0. |
| | Window | Rectangular (default), Hamming, Hanning. |
| **View** | Single block / Average of all blocks / Spectrogram | Default Single block. |
| | Previous block, Block entry, "of M", Next block | Single-block mode only. Prev/Next disabled at the ends. Bad entry → `ERROR`. |
| **Scale** | Linear / dB | Default dB. |
| | Floor (dB) | −200…0, default −40. Enabled only in dB or Spectrogram. |
| | Lower / Upper freq (Hz) | Always enabled; valid when `0 ≤ lower < upper ≤ Fs/2`. Defaults 0 and Fs/2 (0.5 Hz at Fs = 1). Reset on file load or Fs change. |
| | Save PNG… | Always opens a save dialog; disabled until a file is loaded. |

Changing any parameter, channel, or row/column resets to block 1 and recomputes (C1d, C2d).

### 6.3 What it computes (the maths, B1–B12)

- **Transform:** real-to-real orthonormal sinusoidal transform, size N × N matrix `T` — row 0 = `1/√N`; rows 1…N/2−1 = `√(2/N)·cos(2πkn/N)`; row N/2 = `cos(πn)/√N`; rows N/2+1…N−1 = `√(2/N)·sin(2π(N−k)n/N)`. **Implemented with `rfft`**, not matrix multiply (a matrix version exists for testing only).
- **Power:** `P[0]=c₀²`, `P[N/2]=c²_{N/2}`, `P[k]=c_k²+c²_{N−k}` — N/2+1 bins, bin k at `k·Fs/N`.
- **Window:** periodic Rectangular/Hamming/Hann, power divided by `sum(w²)/N` so levels are comparable across windows.
- **Blocks:** non-overlapping, hop = N, last block zero-padded, `M = ceil(L/N)`, no mean removal.
- **Average:** mean of *linear* power over all blocks, **then** dB — never average dB.
- **dB:** `10·log10(P/Pmax)`, max = 0 dB, clipped at the floor; all-zero data → everything at floor + INFO.
- **Spectrogram:** (N/2+1) × M array, normalised to its global max, blue (floor) → red (0 dB) colormap, colorbar in dB, frequency upward. x-axis = block number for images, **time (s) = (j−1)·N/Fs for WAV**.

### 6.4 Plot titles and axes
- Spectrum: x = frequency (Hz) over the chosen range; y = "Power (dB re max)" or "Power". Title: file name, mode, N, window (+ block number in single-block mode). Navigation toolbar included.
- Spectrogram: y = frequency (Hz) over the chosen range; x = time or block; colorbar in dB.

### 6.5 Saving
"Save PNG…" saves exactly what's shown (title, labels, colorbar), `dpi=150`, suggested names `<input>_block3.png`, `<input>_average.png`, `<input>_spectrogram.png`; `.png` appended if missing. Cancel logs `save cancelled`; success logs `file saved: <path>`; failure logs `ERROR` and the tab stays usable.

### 6.6 Behaviour on the first view (matches the screenshot)
- Plot area shows the placeholder text "Load a .wav or image file (Browse…)".
- Log's first line records the defaults.
- Prev/Next, Block box, Channel, Row/Column, Index, and Save PNG are disabled/greyed until a file is loaded.
- "of 0" shows because no blocks exist yet.

> **Note on the screenshot:** the Floor spinbox and frequency boxes appear active even though no file is loaded. That is consistent with the spec (floor is enabled in dB mode; the frequency entries are "always enabled").

---

## 7. How Lab questions map to features

| Lab question | Feature that answers it |
|---|---|
| Different windows | Window drop-down (Rectangular / Hamming / Hanning) |
| Walk block by block | Previous / Next block, N set to 2048 |
| Average spectrum of whole file | "Average of all blocks" mode |
| See notes in the C-scale | Spectrogram + Lower/Upper freq range set to the scale's pitch band |
| Effect of block size | N drop-down (compare e.g. 512 vs 2048 vs 8192: more frequency resolution but less time resolution) |
| Where does noise live? | Average spectrum of noisy file vs. clean file |
| Which filter, which parameters? | Noise Filter tab; spectrum before/after via "Send to Power Spectrum" |

---

## 8. Non-functional requirements

- **Responsiveness:** vectorised numpy (reshape to M × N, `rfft` on axis 1). Files over 100 million samples rejected with `ERROR` (PS spec D1). Spectrogram drawing may decimate; computed data must not.
- **Code quality:** DSP functions are pure (arrays in, arrays out) with one-line docstrings; no global mutable state beyond each tab's own object (D3).
- **Defaults when the spec is silent:** choose a sensible default and note it in the tab's log; do not stop and ask.

---

## 9. Acceptance and deliverables

### 9.1 Tests (no GUI required)
`test_powerspec.py` with plain asserts implementing PS spec **E1–E13**: orthonormality, FFT == matrix multiply, Parseval, pure-tone bin placement, 1 kHz peak at N = 1024, block count `ceil(L/N)`, window normalisation, average-then-dB, dB max = 0 and floor clipping, PNG saving incl. bad-path handling, defaults, frequency-range validation, and path-field wrapping.
Filter tests (new): median removes isolated spikes and leaves clean samples; notch attenuates the target tone by a stated minimum; lowpass attenuates above cutoff.

### 9.2 Submission (Lab 3)
- Spectrogram of `c_scale.wav` with answers to the three questions in §2 Part I.3.
- Short observations on window and block-size effects (Part I.4–5).
- Best filtered `.wav` for each noisy audio file, with filter type and parameters.
- Best filtered image for `photo.png` and `text.png` with comment on filter behaviour per image type.
- Concise write-up of what I tried and why.

### 9.3 Project files
```
Lab 3/
  requirements_v2.md          this file
  design.md                   full design (next step)
  app.py                      entry point, notebook shell
  noise_filter_tab.py         Tab 1 UI
  filters.py                  pure filter functions (no tkinter)
  powerspec_tab.py            Tab 2 UI: PowerSpecTab(ttk.Frame)
  powerspec_dsp.py            pure DSP for Tab 2 (no tkinter) [assumed split]
  test_powerspec.py           E1–E13
  test_filters.py             filter tests
  data/                       Canvas input files
  output/                     filtered results
```

---

## 10. Open questions

| # | Question | My default if unanswered |
|---|---|---|
| Q1 | Are the file-name codes in §3 right (nb = narrowband, p = pops, s = sinusoid)? | Treated as in §3 |
| Q2 | ~~Chain filters?~~ **Decided: one filter at a time for now; chaining later.** | n/a |
| Q3 | Audio playback inside the app? `winsound` works on Windows only. | Include a Windows-only before/after Play button; skip silently elsewhere |
| Q4 | Should Tab 1 get a "Send to Power Spectrum" shortcut? | Yes |
| Q5 | Is `Lab 3/data/` where the Canvas files will go? | Yes |
| Q6 | Single `.py` file or the module split in §9.3? | Module split (the PS spec requires its own module) |

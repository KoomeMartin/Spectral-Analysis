# Noise Filter — Lab 3

A small Python/Tkinter app for **understanding spectra and removing noise** from audio and images (CMU MSEAI, Processing Worlds Information, Lab 3).

It has two tabs that work together:

| Tab | Purpose |
|---|---|
| **Noise Filter** | Load a noisy `.wav` or image, apply one filter at a time, compare before/after, save the result. |
| **Power Spectrum** | Analyse a file's spectrum (single block, average of all blocks, or spectrogram) to see *where* the noise is before choosing a filter. |

**Typical workflow:** load a noisy file in Noise Filter → **Analyze original** (opens it in Power Spectrum) → decide the filter from the spectrum → **Apply** → **Analyze filtered** to check the result → **Save filtered**.

## Run it

```
python app.py
```

Needs Python 3 with `numpy`, `scipy`, `pillow` and `matplotlib` (Tkinter comes with Python). Audio playback uses `winsound`, so it works on Windows only.

Tests (no GUI interaction needed; some create a hidden window):

```
python test_powerspec.py
python test_filters.py
```

## What the app can do

- **Power Spectrum tab:** transform size N from 16 to 16384, Rectangular / Hamming / Hanning windows, single block / average / spectrogram views, linear or dB scale with an adjustable floor, frequency-range zoom, Save PNG.
- **Noise Filter tab:**
  - Audio: Median + threshold, Notch (band-reject), Lowpass, Highpass.
  - Images (colour is kept): Gaussian, Median, Mean.
  - Play original/filtered, Analyze original/filtered, Save filtered.
  - Saved names record what was done, for example `c_scale_s400r5000_notch_390-410_o4.wav` or `music_p05r2000_medthr_w3_t0p02.wav`.
- Limitation: one filter is applied at a time (always from the original file).

## Where everything is

**Code**

| File | Purpose |
|---|---|
| [app.py](app.py) | Entry point. Window with the two tabs. |
| [noise_filter_tab.py](noise_filter_tab.py) | Noise Filter tab (UI). |
| [powerspec_tab.py](powerspec_tab.py) | Power Spectrum tab (UI). |
| [powerspec_dsp.py](powerspec_dsp.py) | Spectrum maths: transform, windows, blocks, dB. No UI code. |
| [filters.py](filters.py) | The filters and the file-name tags. No UI code. |
| [audio_io.py](audio_io.py) | Reading and writing WAV files and images. |
| [ui_common.py](ui_common.py) | Shared widgets: log window and wrapping file-path field. |
| [test_powerspec.py](test_powerspec.py) | Tests for the spectrum maths and the Power Spectrum tab. |
| [test_filters.py](test_filters.py) | Tests for the filters, file I/O and the Noise Filter tab. |

**Documents**

| File | Purpose |
|---|---|
| [Lab 3.pdf](Lab%203.pdf) | The assignment. |
| [requirements_xform_powerspec_v2.txt](requirements_xform_powerspec_v2.txt) | The provided specification for the Power Spectrum tab. |
| [requirements_v1.md](requirements_v1.md) | The original one-paragraph brief. |
| [requirements_v2.md](requirements_v2.md) | What the app must do, in detail. |
| [design.md](design.md) | How the app is built: architecture, modules, data flow. Written before the code, so a few details differ (for example it mentions an `output/` folder that is not used). |
| [interrogation.md](interrogation.md) | Log of the questions asked while working and the answers, with a status for each. |
| [integration_notes.md](integration_notes.md) | Concepts (floor, bins, windows, DC offset) and measured filter results on the lab files. |

**Data and results**

| Folder | Contents |
|---|---|
| `data/` | The lab's input files: clean `music.wav`, `c_scale.wav`, `photo.png`, `text.png`, plus their noisy versions. |
| `Submission/` | Your saved filtered files and spectrogram images. |
| `latex/` | The Lab 3 report (`main.tex`) and its figures in `images/`. See `latex/README.md`. |
| `scripts/` | `make_report_figures.py` regenerates the report figures and prints the scores quoted in the report. |

## The lab data files

Measured against the clean files, the names mean:

- `s<freq>r<amp>`: one sine of that frequency (Hz) added.
- `nb<low>-<high>r<amp>`: noise limited to that band (Hz).
- `p<n>r<amp>`: random noise added to a fraction of samples (`p01` ≈ 1 %, `p05` ≈ 5 %, `p1` ≈ 10 %).
- Images: `p…_r…` files carry random noise.

Details and which filter suited which file are in [integration_notes.md](integration_notes.md).

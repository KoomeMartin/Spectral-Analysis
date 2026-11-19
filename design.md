# Noise Filter App — Design

Companion to `requirements_v2.md` (what and why). This file says **how**. The Power Spectrum maths is defined by `requirements_xform_powerspec_v2.txt` (the "PS spec", section ids like *B9* refer to it).

---

## 1. System overview

A Tkinter desktop app with two tabs in one `ttk.Notebook`. The tabs share no state; they only exchange files/arrays through one explicit hand-off (§8).

```
                          app.py  (NoiseFilterApp, ttk.Notebook)
                         /                                    \
        noise_filter_tab.py                              powerspec_tab.py
        NoiseFilterTab(ttk.Frame)                        PowerSpecTab(ttk.Frame)
              |         \                                     |        \
         filters.py   audio_io.py  <------ shared ------>  powerspec_dsp.py
        (pure DSP)    (WAV/image load+save, no tkinter)     (pure DSP)
                              \                              /
                               ui_common.py (LogPane, PathField)
```

### 1.1 Layering rules
1. **DSP modules** (`filters.py`, `powerspec_dsp.py`, `audio_io.py`) import numpy/scipy/Pillow only, never tkinter or matplotlib. They are pure: arrays in, arrays out, one-line docstrings (D3).
2. **Tab modules** own widgets and state, call DSP, never do maths themselves.
3. **`ui_common.py`** holds the two widgets both tabs need: `LogPane` and `PathField`.
4. Dependencies point downward only. No module imports `app.py`.

### 1.2 Files

| File | Responsibility |
|---|---|
| `app.py` | Entry point. Builds root window "Noise Filter", the notebook, and both tabs. |
| `ui_common.py` | `LogPane`, `PathField`. |
| `audio_io.py` | `load_wav`, `save_wav`, `load_image`, `save_image`. |
| `filters.py` | `median_threshold`, `notch`, `lowpass`, `image_gaussian`, `image_median`, `image_mean`. |
| `noise_filter_tab.py` | Tab 1 UI. |
| `powerspec_dsp.py` | Transform, power, windows, blocking, spectrogram, dB. |
| `powerspec_tab.py` | Tab 2 UI. |
| `test_powerspec.py` | PS spec E1-E13. |
| `test_filters.py` | Filter and I/O tests. |
| `data/`, `output/` | Canvas inputs; filtered results. |

---

## 2. Application shell (`app.py`)

```python
class NoiseFilterApp:
    def __init__(self, root):
        root.title("Noise Filter")
        nb = ttk.Notebook(root); nb.pack(fill="both", expand=True)
        self.nf = NoiseFilterTab(nb, on_send_to_spectrum=self._send)
        self.ps = PowerSpecTab(nb)
        nb.add(self.nf, text="Noise Filter")
        nb.add(self.ps, text="Power Spectrum")
```

- Tabs are frames that stay alive in the notebook, so state survives tab switches (D2).
- The host needs only the import and `nb.add` for the PS tab (A3).
- Window opens at roughly 1130 x 790 (the reference screenshot), resizable; plot and log stretch, control row keeps its height.
- **Build order:** step 1 uses a dummy tab (button writes "button pressed" to its log) to prove integration; step 2 swaps in `NoiseFilterTab`.

---

## 3. Shared UI components (`ui_common.py`)

### 3.1 `LogPane(ttk.Frame)`
Read-only `ScrolledText` (monospace, about 6 lines high at the bottom of each tab).

| Method | Behaviour |
|---|---|
| `info(msg)` / `error(msg)` | Append `HH:MM:SS LEVEL: msg`. `error` uses a red text tag. Auto-scroll to end. |

Widget state is `disabled` between writes so users cannot type in it. Each tab owns one instance; no tab writes to another's log (A4).

### 3.2 `PathField(ttk.Frame)`
Browse button + read-only wrapping path display (C1a, E13).
- Display is a `tk.Label` (or disabled `tk.Text`) with `wraplength` bound to the widget width via `<Configure>`, so wrapping follows window resize. Mid-word breaks are needed because paths have no spaces, so the display uses a disabled `tk.Text(wrap="char", height=n)` and recomputes `height` from `len(path) / chars_per_line`. The field is therefore always taller than one line for long paths.
- API: `set(path)`, `get()`, `on_browse` callback. Used for every input and output path in both tabs.

---

## 4. I/O (`audio_io.py`)

| Function | Returns / does |
|---|---|
| `load_wav(path)` | `WavData(samples: float64 [n_ch, L] in -1..1, fs: int, n_channels, bit_depth, fmt)` |
| `save_wav(path, samples, fs)` | Writes 16-bit PCM (clipped), same `fs` and channel count |
| `load_image(path)` | `ImageData(gray: float64 [H, W] in 0..1, rgb_or_gray_pil)` |
| `save_image(path, array)` | Writes png/bmp, clipped to 0..255 |

**WAV parsing (B/C1b).** Parse the RIFF header by hand (so 24-bit and `WAVE_FORMAT_EXTENSIBLE` work; `scipy.io.wavfile` is a fallback only). Support PCM 8 (unsigned), 16, 24, 32-bit and float32. Convert to float in -1..1. 24-bit is unpacked from 3-byte groups. Unsupported format, empty data, or > 100 M samples raises `AudioIOError(reason)`; tabs catch it and log `ERROR`.

**Image.** `Image.open(p).convert("L")`, divide by 255.

**Scale note for noise.** Lab file names carry amplitudes like `r5000` (16-bit sample units). After conversion to -1..1 that is about 0.15 full scale. Filter thresholds in the UI are shown in the **normalised -1..1 scale** and the tooltip gives the 16-bit equivalent.

---

## 5. Power Spectrum tab

### 5.1 DSP API (`powerspec_dsp.py`, pure)

| Function | Spec | Notes |
|---|---|---|
| `tmatrix(N)` | B2-B6 | Test only; N x N. |
| `transform_blocks(blocks)` | B7 | `blocks` is M x N. `rfft(axis=1)`, then `c0, c_{N/2}, c_k, c_{N-k}` assembled by slicing. No matrix multiply. |
| `raw_power(coefs)` | B8 | M x (N/2+1). |
| `get_window(name, N)` | B9 | `scipy.signal.get_window(..., fftbins=True)`; names Rectangular/Hamming/Hanning map to boxcar/hamming/hann. |
| `make_blocks(x, N)` | B10 | Zero-pad to `M*N`, `reshape(M, N)`, `M = ceil(L/N)`; `L < N` gives one padded block. |
| `block_powers(x, N, window)` | B9+B10+B8 | `blocks * w`, transform, power, divide by `sum(w^2)/N`. Returns M x (N/2+1). One vectorised call (D1). |
| `average_power(P)` | B12 | `P.mean(axis=0)`, **linear**. |
| `to_db(P, floor)` | C6b/c | `10*log10(P/Pmax)`, clip at floor; zeros and negatives to floor; `Pmax == 0` returns all-floor and a flag so the tab logs INFO. |
| `freq_axis(N, fs)` | B11 | `k*fs/N`, k = 0..N/2. |
| `spectrogram_db(P, floor)` | C8 | Transpose to (N/2+1) x M, normalise by the global max, `to_db`. |

### 5.2 Tab state (a single `PsState` dataclass held by the tab)

```
path, kind ('wav'|'image'|None), fs, stream (1-D float), channels, n_ch
channel ('Left'|'Right'|'Mono'), orient ('Row'|'Column'), index
N=512, window='Rectangular', mode='single'|'average'|'spectrogram'
scale='dB'|'linear', floor=-40.0, f_lo=0.0, f_hi=fs/2, block=1
P (M x (N/2+1) cache), M
```

**Compute cache.** `P` is recomputed only when the stream, N, or window changes. Block change, scale, floor, frequency range and mode switches redraw from the cache. This keeps stepping through blocks instant. Per C7a the frequency range only changes the display limits, not the data.

### 5.3 Widget tree (matches the reference screenshot)

```
PowerSpecTab(ttk.Frame)
 |- controls (ttk.Frame, one row, 4 LabelFrames side by side)
 |   |- "Input file":  PathField | Channel Combobox (Left/Right/Mono) | Row/Column Radiobuttons | Index Spinbox
 |   |- "Parameters":  Transform size N Combobox(16..16384) | Fs Entry | Window Combobox
 |   |- "View":        Radiobuttons (Single block / Average of all blocks / Spectrogram)
 |   |                 [Previous block] Block: Entry "of M" [Next block]
 |   |- "Scale":       Radiobuttons (Linear / dB) | Floor Spinbox(-200..0) | Lower freq Entry | Upper freq Entry | [Save PNG...]
 |- canvas area:       matplotlib Figure in FigureCanvasTkAgg   (placeholder text until a file loads)
 |- NavigationToolbar2Tk
 |- LogPane
```

Layout uses `grid` with the canvas row weighted so only plot and log stretch.

### 5.4 Enable/disable matrix (greyed, never hidden)

| Control | No file | WAV mono | WAV stereo | Image | Single | Average | Spectrogram |
|---|---|---|---|---|---|---|---|
| Channel | off | off | **on** | off | | | |
| Row/Column + Index | off | off | off | **on** | | | |
| Fs entry | on | read-only | read-only | **on** | | | |
| Prev / Next / Block entry | off | | | | **on** (Prev off at 1, Next off at M) | off | off |
| Floor | on (dB default) | | | | dB only | dB only | **always** |
| Lower/Upper freq | always on | | | | | | |
| Save PNG | off | | | | on once loaded | | |

One method, `_refresh_controls()`, sets every control's state from `PsState`. It is called after every state change, so rules live in one place.

### 5.5 Event flow

```
Browse -> _load(path)
   load via audio_io -> on error: log ERROR, keep previous state, return
   set kind/fs/stream, reset f range to 0..fs/2, block=1
   log INFO "loaded <name>, <type>, <L> samples, Fs=<fs>"
   _recompute() -> _redraw() -> _refresh_controls()

param change (N / Fs / Window / channel / row / col / index)
   validate -> on error: log ERROR, restore widget to previous value, return
   update state, block=1, log INFO
   _recompute() (only if data-affecting) -> _redraw()

block / scale / floor / freq range / mode change
   validate -> update state -> _redraw()
```

### 5.6 Plot drawing (`_redraw`)
- Clear the figure, rebuild axes (single/average) or axes + colorbar (spectrogram).
- **Spectrum:** `ax.plot(freq, y)`; `xlim = (f_lo, f_hi)`; y is dB with `ylim = (floor, 0)` or linear power. Labels per C7b. Title: `<file> | single block k of M | N=512 | Hamming`.
- **Spectrogram:** `imshow(S, origin="lower", aspect="auto", extent=[x0, x1, 0, fs/2], cmap=LinearSegmentedColormap.from_list("br", ["blue","red"]), vmin=floor, vmax=0)`, then `set_ylim(f_lo, f_hi)`. Colorbar labelled "dB". x-axis: time `(j-1)*N/fs` for WAV, block number 1..M for images. For large M, columns are decimated **for drawing only**; `P` is untouched (C8e).
- `fig.canvas.draw_idle()` once at the end.
- No file loaded: draw the placeholder "Load a .wav or image file (Browse...)".

### 5.7 Validation (every rejection logs `ERROR`, keeps previous value)
| Input | Rule |
|---|---|
| Block | integer, `1 <= b <= M` |
| Fs | float, `> 0` (image only) |
| Floor | float, `-200 <= f <= 0` |
| Frequency range | floats, `0 <= lo < hi <= fs/2` |
| Index | integer, `1..rows` or `1..cols` |
| File | > 0 samples, <= 100 M, supported format |

### 5.8 Saving (C9)
`save_png(path=None)`: if `path is None`, open `asksaveasfilename` (default `.png`, filter "PNG image (*.png)", name `<input>_block<k>.png | _average.png | _spectrogram.png`); cancel logs `save cancelled`. Appends `.png` if missing; `fig.savefig(path, dpi=max(150, fig.dpi))`; any exception logs `ERROR: <reason>`. The optional `path` parameter lets tests bypass the dialog (E10).

---

## 6. Noise Filter tab

### 6.1 DSP API (`filters.py`, pure)

| Function | Signature | Method |
|---|---|---|
| `median_threshold` | `(x, window, threshold)` | `scipy.signal.medfilt`-style running median `m`; output `x` where `abs(x-m) <= threshold`, else `m`. Clean samples are untouched. Window forced odd. |
| `notch` | `(x, fs, f_lo, f_hi, order)` | Band-reject: `scipy.signal.butter(order, [f_lo, f_hi], "bandstop", fs=fs, output="sos")` + `sosfiltfilt` (zero phase). A narrow band covers a sinusoid; a wide band covers `nb` noise. |
| `lowpass` | `(x, fs, cutoff, order)` | `butter(..., "lowpass", output="sos")` + `sosfiltfilt`. |
| `image_gaussian` | `(img, sigma)` | `scipy.ndimage.gaussian_filter`. |
| `image_median` | `(img, size)` | `scipy.ndimage.median_filter`. |
| `image_mean` | `(img, size)` | `scipy.ndimage.uniform_filter`. |

Audio filters operate per channel on a 1-D array; the tab loops channels. IIR designs use second-order sections for numerical stability at narrow bands. A notch whose edges touch 0 or Nyquist is rejected by validation rather than silently altered.

### 6.2 Filter-to-noise guide (the intended workflow)

| Noise (file code) | Look in Power Spectrum for | Filter |
|---|---|---|
| Sinusoid `s<freq>` | One narrow spike at `<freq>` Hz | Notch, narrow band centred on `<freq>` |
| Narrowband `nb<lo>-<hi>` | Plateau above the music between `lo` and `hi` | Notch with `lo..hi` as edges (or lowpass if the band sits above the music, e.g. `nb5000-7999`) |
| Pops `p<n>r<amp>` | Raised broadband floor; spikes in the waveform | Median with threshold (just above typical signal change) |

### 6.3 Widget tree

```
NoiseFilterTab(ttk.Frame)
 |- controls row
 |   |- "Input file":  PathField | info label (type, Fs, channels, length)
 |   |- "Filter":      Radiobuttons (Median+threshold / Notch / Lowpass | image: Gaussian / Median / Mean)
 |   |                 (radio set switches with input kind)
 |   |- "Parameters":  frame rebuilt per selected filter (see 6.4)
 |   |- "Actions":     [Apply] [Reset] [Play original] [Play filtered] [Send to Power Spectrum]
 |- preview area:      two matplotlib axes, "Before" and "After"
 |                     audio -> waveform; image -> picture
 |- "Output file":     PathField (read-only) | [Save filtered...]
 |- LogPane
```

### 6.4 Parameters per filter

| Filter | Parameters (defaults) |
|---|---|
| Median + threshold | Window length, odd, samples (5); Threshold, normalised 0..1 (0.05) |
| Notch | Lower edge Hz (350); Upper edge Hz (450); Order (4) |
| Lowpass | Cutoff Hz (4000); Order (4) |
| Gaussian | Sigma (1.0) |
| Median (image) | Size, odd (3) |
| Mean (image) | Size, odd (3) |

Frequency limits come from the loaded file's `Fs` (`0 < f < Fs/2`).

### 6.5 State and flow
```
NfState: path, kind, fs, data (original), result (filtered or None), filter, params
Apply -> validate params (ERROR + keep result on failure)
      -> result = filter(original, params)          # always from the ORIGINAL
      -> redraw "After", log INFO "<filter> applied: <params>"
Reset -> result = None, clear After pane
Save  -> save dialog (suggest <input>_filtered.wav|png), log saved/cancelled/ERROR
```

**One filter at a time (decided).** Apply always starts from `original`. Chaining hook: `Apply` is the single call site `result = _run_pipeline(original, [(name, params)])`. Chaining later means passing a longer list, or a checkbox "apply to current result" that uses `result` instead of `original` as the input. No other code changes.

### 6.6 Playback
`Play` uses `winsound.PlaySound` from an in-memory 16-bit WAV, async (`SND_MEMORY | SND_ASYNC`). On non-Windows the buttons are disabled and a one-line INFO is logged. No extra packages.

### 6.7 Send to Power Spectrum
`on_send_to_spectrum(samples, fs, label)` hands arrays to `PowerSpecTab.load_array(samples, fs, label)`, which behaves like a file load (resets range and block, logs `loaded <label> (from Noise Filter)`). `PowerSpecTab` therefore exposes `load_array` besides `_load(path)`. The Notebook then selects the Power Spectrum tab.

---

## 7. Error handling

- Every callback body is `try/except` through one decorator `@guarded(self.log)`, so an unexpected exception logs `ERROR: <type>: <message>` and the tab stays usable.
- Loading builds the new state in locals and swaps it in only on success, so a failed load leaves the previous file and plot intact.
- No `messagebox` for tab-specific messages (A4).

---

## 8. Testing

### 8.1 `test_powerspec.py` (plain asserts, no GUI) — PS spec E1-E13

| Id | Test |
|---|---|
| E1 | `T @ T.T == I` for N = 16, 64, 512 (1e-9) |
| E2 | `transform_blocks` equals `T @ x`, N = 16..4096 (1e-9) |
| E3 | Parseval for rectangular window |
| E4 | Cosine/sine at bin k0 puts all power in bin k0 |
| E5 | 1 kHz tone at 44.1 kHz, N = 1024, peak within one bin |
| E6 | `M = ceil(L/N)`, last block zero-padded |
| E7 | Window normalisation (rect identity; Hamming/Hann DC power within a few %) |
| E8 | Average-then-dB differs from dB-then-average; implementation does the former |
| E9 | dB max exactly 0, nothing below floor, zeros at floor |
| E10 | PNG saves for single, average, spectrogram (signature `89 50 4E 47`); bad path logs ERROR, no raise |
| E11 | Tab defaults |
| E12 | Frequency range behaviour and rejections |
| E13 | Path-field wrapping |

E10-E13 construct the tab under a hidden `Tk()` root and call methods directly; E1-E9 import only `powerspec_dsp`.

### 8.2 `test_filters.py`
- Median-threshold removes an isolated spike and leaves other samples bit-identical.
- Notch cuts a 400 Hz tone by at least 40 dB while leaving a 1 kHz tone within 1 dB.
- Lowpass cuts a tone above cutoff by at least 40 dB.
- Gaussian/median reduce image noise standard deviation.
- `load_wav` round trips 8/16/24/32-bit and float WAVs; `save_wav` then `load_wav` preserves values to quantisation.

### 8.3 Manual smoke run
`python app.py` starts, both tabs appear, the PS tab's first log line reads: `Power Spectrum tab ready. Defaults: N=512, Fs=1 Hz, window=Rectangular, floor=-40 dB, scale=dB, mode=Single block, channel=Left.` Then the Part I and II walkthroughs below.

---

## 9. Lab walkthrough (how the finished app answers the lab)

1. **C-scale spectrogram:** load `c_scale.wav`, Spectrogram, N = 2048, set Lower/Upper to the scale's pitch range (about 200-1200 Hz **[assumed]**), save PNG. Notes appear as horizontal bands; transitions show smeared or double bands where a block straddles two notes. Larger N sharpens frequency but blurs time, smaller N does the reverse.
2. **Block stepping:** Single block, N = 2048, Next block through the scale; repeat with Hamming and Hanning (lower sidelobes, slightly wider peak).
3. **`music.wav`:** spectrogram plus a few single blocks.
4. **Noise:** load each noisy file, view Average, identify the noise (spike / plateau / floor), compare against the clean twin, pick the filter in Tab 1, Apply, Send to Power Spectrum, compare, save the best `.wav`.
5. **Images:** apply Gaussian / Median / Mean at several sizes to `photo_*` and `text_*`; note blur on text edges versus good smoothing on the photo.

---

## 10. Build plan

| Step | Deliverable | Done when |
|---|---|---|
| 1 | `app.py` shell + dummy tab + `ui_common.py` | Button logs "button pressed" |
| 2 | `powerspec_dsp.py` + `test_powerspec.py` E1-E9 | Tests pass |
| 3 | `powerspec_tab.py` | Tab matches the screenshot; E10-E13 pass |
| 4 | `audio_io.py`, `filters.py`, `test_filters.py` | Tests pass |
| 5 | `noise_filter_tab.py` replaces dummy | Filter, preview, save work |
| 6 | Hand-off + playback + lab runs on real files | Deliverables in `output/` |

## 11. Decisions and open items

**Decided:** Tkinter; one filter at a time, chaining deferred; module split per §1.2; pure DSP separated from UI; real file names recorded in `requirements_v2.md`.

**Still assumed (cheap to change):** exact meaning of `p`/`r` in file names; thresholds in normalised units; Windows-only playback; spectrogram pitch range for the C-scale; default filter parameter values.

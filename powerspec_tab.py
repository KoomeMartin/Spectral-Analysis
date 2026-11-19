"""Power Spectrum tab: PowerSpecTab(ttk.Frame). DSP lives in powerspec_dsp.py."""
import math
import os
import tkinter as tk
from tkinter import filedialog, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

import audio_io
import powerspec_dsp as dsp
from ui_common import LogPane, PathField, guarded

SIZES = [2 ** k for k in range(4, 15)]
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff")
CMAP = LinearSegmentedColormap.from_list("blue_red", ["blue", "red"])
MAX_DRAW_COLUMNS = 4000


class PowerSpecTab(ttk.Frame):
    """Spectrum / average / spectrogram analyser for .wav and image files."""

    def __init__(self, master):
        super().__init__(master)
        # committed state
        self.kind = None          # 'wav' | 'image' | None
        self.path = ""
        self.label = ""
        self.fs = 1.0
        self.wav = None           # [n_ch, L]
        self.img = None           # [rows, cols]
        self.stream = None
        self.N, self.window = 512, "Rectangular"
        self.mode, self.scale, self.floor = "single", "dB", -40.0
        self.f_lo, self.f_hi = 0.0, 0.5
        self.block, self.M, self.P = 1, 0, None
        self.ax = None
        self._build()
        self.log = self.log_pane
        self._refresh_controls()
        self._redraw()
        self.log.info("Power Spectrum tab ready. Defaults: N=512, Fs=1 Hz, window=Rectangular, "
                      "floor=-40 dB, scale=dB, mode=Single block, channel=Left.")

    # ------------------------------------------------------------------ UI
    def _build(self):
        self.n_var = tk.StringVar(value="512")
        self.fs_var = tk.StringVar(value="1")
        self.win_var = tk.StringVar(value="Rectangular")
        self.ch_var = tk.StringVar(value="Left")
        self.orient_var = tk.StringVar(value="Row")
        self.idx_var = tk.StringVar(value="1")
        self.mode_var = tk.StringVar(value="single")
        self.scale_var = tk.StringVar(value="dB")
        self.floor_var = tk.StringVar(value="-40")
        self.lo_var = tk.StringVar(value="0")
        self.hi_var = tk.StringVar(value="0.5")
        self.block_var = tk.StringVar(value="1")
        self.of_var = tk.StringVar(value="of 0")

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=4, pady=4)

        g = ttk.LabelFrame(bar, text="Input file")
        g.pack(side="left", fill="y", padx=2)
        self.path_field = PathField(g, on_browse=self.browse, width=18)
        self.path_field.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=2)
        g.columnconfigure(0, weight=1)
        ttk.Label(g, text="Channel:").grid(row=1, column=0, sticky="e")
        self.ch_box = ttk.Combobox(g, textvariable=self.ch_var, values=["Left", "Right", "Mono"],
                                   width=7, state="readonly")
        self.ch_box.grid(row=1, column=1, columnspan=2, sticky="w")
        self.ch_box.bind("<<ComboboxSelected>>", lambda e: self._on_channel())
        self.row_rb = ttk.Radiobutton(g, text="Row", value="Row", variable=self.orient_var, command=self._on_index)
        self.col_rb = ttk.Radiobutton(g, text="Column", value="Column", variable=self.orient_var, command=self._on_index)
        self.row_rb.grid(row=2, column=0, sticky="e")
        self.col_rb.grid(row=2, column=1, sticky="w")
        self.idx_box = ttk.Spinbox(g, textvariable=self.idx_var, from_=1, to=1, width=5, command=self._on_index)
        self.idx_box.grid(row=2, column=2, padx=4)
        self.idx_box.bind("<Return>", lambda e: self._on_index())
        self.idx_box.bind("<FocusOut>", lambda e: self._on_index())

        g = ttk.LabelFrame(bar, text="Parameters")
        g.pack(side="left", fill="y", padx=2)
        ttk.Label(g, text="Transform size N:").grid(row=0, column=0, sticky="e")
        self.n_box = ttk.Combobox(g, textvariable=self.n_var, values=[str(s) for s in SIZES], width=7, state="readonly")
        self.n_box.grid(row=0, column=1, padx=4, pady=2)
        self.n_box.bind("<<ComboboxSelected>>", lambda e: self._on_params())
        ttk.Label(g, text="Fs (Hz):").grid(row=1, column=0, sticky="e")
        self.fs_entry = ttk.Entry(g, textvariable=self.fs_var, width=10)
        self.fs_entry.grid(row=1, column=1, padx=4, pady=2, sticky="w")
        self.fs_entry.bind("<Return>", lambda e: self._on_params())
        self.fs_entry.bind("<FocusOut>", lambda e: self._on_params())
        ttk.Label(g, text="Window:").grid(row=2, column=0, sticky="e")
        self.win_box = ttk.Combobox(g, textvariable=self.win_var, values=list(dsp.WINDOWS), width=11, state="readonly")
        self.win_box.grid(row=2, column=1, padx=4, pady=2)
        self.win_box.bind("<<ComboboxSelected>>", lambda e: self._on_params())

        g = ttk.LabelFrame(bar, text="View")
        g.pack(side="left", fill="y", padx=2)
        for r, (txt, val) in enumerate([("Single block", "single"), ("Average of all blocks", "average"),
                                        ("Spectrogram", "spectrogram")]):
            ttk.Radiobutton(g, text=txt, value=val, variable=self.mode_var, command=self._on_mode).grid(
                row=r, column=0, columnspan=4, sticky="w")
        self.prev_btn = ttk.Button(g, text="Previous block", command=lambda: self._step(-1))
        self.prev_btn.grid(row=3, column=0, padx=2)
        ttk.Label(g, text="Block:").grid(row=3, column=1)
        self.block_entry = ttk.Entry(g, textvariable=self.block_var, width=6)
        self.block_entry.grid(row=3, column=2)
        self.block_entry.bind("<Return>", lambda e: self._on_block_entry())
        ttk.Label(g, textvariable=self.of_var).grid(row=3, column=3, padx=2)
        self.next_btn = ttk.Button(g, text="Next block", command=lambda: self._step(1))
        self.next_btn.grid(row=3, column=4, padx=2)

        g = ttk.LabelFrame(bar, text="Scale")
        g.pack(side="left", fill="y", padx=2)
        ttk.Radiobutton(g, text="Linear", value="linear", variable=self.scale_var, command=self._on_scale).grid(row=0, column=0)
        ttk.Radiobutton(g, text="dB", value="dB", variable=self.scale_var, command=self._on_scale).grid(row=0, column=1)
        ttk.Label(g, text="Floor (dB):").grid(row=1, column=0, sticky="e")
        self.floor_box = ttk.Spinbox(g, textvariable=self.floor_var, from_=-200, to=0, width=6, command=self._on_floor)
        self.floor_box.grid(row=1, column=1)
        self.floor_box.bind("<Return>", lambda e: self._on_floor())
        self.floor_box.bind("<FocusOut>", lambda e: self._on_floor())
        for r, (txt, var) in enumerate([("Lower freq (Hz):", self.lo_var), ("Upper freq (Hz):", self.hi_var)], start=2):
            ttk.Label(g, text=txt).grid(row=r, column=0, sticky="e")
            e = ttk.Entry(g, textvariable=var, width=9)
            e.grid(row=r, column=1)
            e.bind("<Return>", lambda ev: self._on_freq())
            e.bind("<FocusOut>", lambda ev: self._on_freq())
        self.save_btn = ttk.Button(g, text="Save PNG...", command=self.save_png)
        self.save_btn.grid(row=4, column=0, columnspan=2, pady=2)

        self.fig = Figure(figsize=(6, 3.2), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        tb = ttk.Frame(self)
        tb.pack(fill="x")
        NavigationToolbar2Tk(self.canvas, tb, pack_toolbar=True).update()
        self.log_pane = LogPane(self, height=6)
        self.log_pane.pack(fill="x", padx=4, pady=4)

    def _refresh_controls(self):
        """Set every control's enabled state from the committed state (greyed, never hidden)."""
        def st(w, on):
            w.state(["!disabled" if on else "disabled"])
        loaded = self.kind is not None
        wav_stereo = self.kind == "wav" and self.wav.shape[0] > 1
        st(self.ch_box, wav_stereo)
        if wav_stereo:
            self.ch_box.state(["readonly"])
        st(self.row_rb, self.kind == "image")
        st(self.col_rb, self.kind == "image")
        st(self.idx_box, self.kind == "image")
        st(self.fs_entry, self.kind != "wav")
        single = loaded and self.mode == "single"
        st(self.block_entry, single)
        st(self.prev_btn, single and self.block > 1)
        st(self.next_btn, single and self.block < self.M)
        st(self.floor_box, self.scale == "dB" or self.mode == "spectrogram")
        st(self.save_btn, loaded)
        self.of_var.set(f"of {self.M}")
        self.block_var.set(str(self.block))

    # ------------------------------------------------------------ loading
    @guarded
    def browse(self):
        path = filedialog.askopenfilename(
            title="Open audio or image",
            filetypes=[("Audio / image", "*.wav *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff"), ("All files", "*.*")])
        if path:
            self.load_file(path)

    def load_file(self, path):
        """Load a .wav or image file; on any failure log ERROR and keep the previous state."""
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".wav":
                w = audio_io.load_wav(path)
                data, kind, fs = w.samples, "wav", float(w.fs)
                info = f"WAV, {w.n_channels} ch, {data.shape[1]} samples, Fs={fs:g} Hz"
            elif ext in IMAGE_EXTS:
                data, kind, fs = audio_io.load_image(path), "image", (self.fs if self.kind == "image" else 1.0)
                info = f"image, {data.shape[0]}x{data.shape[1]} px"
            else:
                raise audio_io.AudioIOError(f"unsupported file type '{ext}'")
        except audio_io.AudioIOError as exc:
            self.log.error(f"{os.path.basename(path)}: {exc}")
            return False
        self._install(data, kind, fs, path, os.path.basename(path))
        self.log.info(f"file loaded: {os.path.basename(path)} ({info})")
        return True

    def load_array(self, data, fs, label, kind="wav"):
        """Load in-memory data (e.g. a filtered result) as if it were a file."""
        self._install(np.asarray(data, dtype=float), kind, float(fs), label, label)
        self.log.info(f"loaded {label}: {kind}, Fs={fs:g} Hz")

    def _install(self, data, kind, fs, path, label):
        if kind == "wav":
            data = np.atleast_2d(data)
            if data.shape[1] > dsp.MAX_SAMPLES:
                self.log.error("file too large (> 100 million samples)")
                return
            self.wav, self.img = data, None
            if data.shape[0] == 1 and self.ch_var.get() != "Left":
                self.ch_var.set("Left")
        else:
            self.wav, self.img = None, data
            self.idx_var.set("1")
            self._set_index_range()
        self.kind, self.path, self.label, self.fs = kind, path, label, fs
        self.fs_var.set(f"{fs:g}")
        self.path_field.set(path)
        self._reset_range()
        self._select_stream()
        self.block = 1
        self._recompute()
        self._refresh_controls()
        self._redraw(f"graph computed ({self._view_desc()})")

    def _set_index_range(self):
        n = self.img.shape[0] if self.orient_var.get() == "Row" else self.img.shape[1]
        self.idx_box.configure(to=n)

    def _select_stream(self):
        if self.kind == "wav":
            ch = self.ch_var.get()
            if self.wav.shape[0] == 1:
                self.stream = self.wav[0]
            elif ch == "Right":
                self.stream = self.wav[1]
            elif ch == "Mono":
                self.stream = (self.wav[0] + self.wav[1]) / 2
            else:
                self.stream = self.wav[0]
        else:
            i = int(self.idx_var.get()) - 1
            self.stream = self.img[i, :] if self.orient_var.get() == "Row" else self.img[:, i]

    def _recompute(self):
        self.P = dsp.block_powers(self.stream, self.N, self.window)
        self.M = self.P.shape[0]

    def _reset_range(self):
        self.f_lo, self.f_hi = 0.0, self.fs / 2
        self.lo_var.set("0")
        self.hi_var.set(f"{self.f_hi:g}")

    # ------------------------------------------------------------ handlers
    @guarded
    def _on_channel(self):
        if self.kind != "wav":
            return
        self._select_stream()
        self.block = 1
        self._recompute()
        self._refresh_controls()
        self.log.info(f"channel selected: {self.ch_var.get()}")
        self._redraw(f"graph computed ({self._view_desc()})")

    @guarded
    def _on_index(self):
        if self.kind != "image":
            return
        rows, cols = self.img.shape
        limit = rows if self.orient_var.get() == "Row" else cols
        self._set_index_range()
        try:
            i = int(self.idx_var.get())
            if not 1 <= i <= limit:
                raise ValueError
        except ValueError:
            self.log.error(f"{self.orient_var.get().lower()} index must be an integer 1..{limit}")
            self.idx_var.set(str(getattr(self, "_idx_ok", 1)))
            return
        self._idx_ok = i
        self._select_stream()
        self.block = 1
        self._recompute()
        self._refresh_controls()
        self.log.info(f"{self.orient_var.get().lower()} {i} selected")
        self._redraw(f"graph computed ({self._view_desc()})")

    @guarded
    def _on_params(self):
        changed = []
        n = int(self.n_var.get())
        if n != self.N:
            self.N = n
            changed.append(f"N={n}")
        if self.win_var.get() != self.window:
            self.window = self.win_var.get()
            changed.append(f"window={self.window}")
        if self.kind != "wav":
            try:
                fs = float(self.fs_var.get())
                if not fs > 0 or not math.isfinite(fs):
                    raise ValueError
            except ValueError:
                self.log.error("Fs must be a number > 0")
                self.fs_var.set(f"{self.fs:g}")
                fs = self.fs
            if fs != self.fs:
                self.fs = fs
                changed.append(f"Fs={fs:g} Hz")
                self._reset_range()
        if not changed:
            return
        self.log.info("parameter changed: " + ", ".join(changed))
        self.block = 1
        if self.kind:
            self._recompute()
        else:
            self._reset_range()
        self._refresh_controls()
        self._redraw(f"graph computed ({self._view_desc()})" if self.kind else None)

    @guarded
    def _on_mode(self):
        self.mode = self.mode_var.get()
        self._refresh_controls()
        self._redraw(f"{'spectrogram computed' if self.mode == 'spectrogram' else 'graph computed'} ({self._view_desc()})"
                     if self.kind else None)

    @guarded
    def _on_scale(self):
        self.scale = self.scale_var.get()
        self._refresh_controls()
        self.log.info(f"scale: {self.scale}")
        self._redraw()

    @guarded
    def _on_floor(self):
        try:
            v = float(self.floor_var.get())
            if not -200 <= v <= 0:
                raise ValueError
        except ValueError:
            self.log.error("floor must be a number from -200 to 0 dB")
            self.floor_var.set(f"{self.floor:g}")
            return
        if v != self.floor:
            self.floor = v
            self.log.info(f"floor set to {v:g} dB")
            self._redraw()

    @guarded
    def _on_freq(self):
        try:
            lo, hi = float(self.lo_var.get()), float(self.hi_var.get())
            if not (0 <= lo < hi <= self.fs / 2):
                raise ValueError
        except ValueError:
            self.log.error(f"frequency range must satisfy 0 <= lower < upper <= Fs/2 ({self.fs / 2:g} Hz); kept "
                           f"{self.f_lo:g}..{self.f_hi:g}")
            self.lo_var.set(f"{self.f_lo:g}")
            self.hi_var.set(f"{self.f_hi:g}")
            return
        if (lo, hi) != (self.f_lo, self.f_hi):
            self.f_lo, self.f_hi = lo, hi
            self.log.info(f"frequency range set to {lo:g}..{hi:g} Hz")
            self._redraw()

    def _on_block_entry(self):
        self.go_to_block(self.block_var.get())

    @guarded
    def go_to_block(self, text):
        try:
            b = int(str(text).strip())
            if not 1 <= b <= self.M:
                raise ValueError
        except ValueError:
            self.log.error(f"block must be an integer 1..{self.M}")
            self.block_var.set(str(self.block))
            return
        self.block = b
        self._refresh_controls()
        self._redraw(f"graph computed ({self._view_desc()})")

    def _step(self, d):
        self.go_to_block(self.block + d)

    # ------------------------------------------------------------- drawing
    def _view_desc(self):
        if self.mode == "single":
            return f"block {self.block} of {self.M}"
        if self.mode == "average":
            return f"average of {self.M} blocks"
        return f"spectrogram, {self.M} blocks"

    def _title(self):
        mode = {"single": f"block {self.block} of {self.M}", "average": "average", "spectrogram": "spectrogram"}[self.mode]
        return f"{self.label} | {mode} | N={self.N} | {self.window}"

    def _redraw(self, msg=None):
        self.fig.clf()
        self.ax = self.fig.add_subplot(111)
        ax = self.ax
        if self.kind is None:
            ax.set_xticks([])
            ax.set_yticks([])
            ax.text(0.5, 0.5, "Load a .wav or image file (Browse...)", ha="center", va="center", transform=ax.transAxes)
            self.canvas.draw_idle()
            return
        ax.set_title(self._title(), fontsize=9)
        if self.mode == "spectrogram":
            self._draw_spectrogram(ax)
        else:
            self._draw_spectrum(ax)
        self.fig.tight_layout()
        self.canvas.draw_idle()
        if msg:
            self.log.info(msg)

    def _draw_spectrum(self, ax):
        y = self.P[self.block - 1] if self.mode == "single" else dsp.average_power(self.P)
        f = dsp.freq_axis(self.N, self.fs)
        if self.scale == "dB":
            y, allzero = dsp.to_db(y, self.floor)
            if allzero:
                self.log.info("all-zero data: plotting everything at the floor")
            ax.set_ylabel("Power (dB re max)")
            ax.set_ylim(self.floor - 1, 1)
        else:
            ax.set_ylabel("Power")
        ax.plot(f, y, lw=1)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_xlim(self.f_lo, self.f_hi)
        ax.grid(True, alpha=0.3)

    def _draw_spectrogram(self, ax):
        S, allzero = dsp.spectrogram_db(self.P, self.floor)
        if allzero:
            self.log.info("all-zero data: plotting everything at the floor")
        stride = max(1, math.ceil(S.shape[1] / MAX_DRAW_COLUMNS))  # decimate for drawing only
        if self.kind == "wav":
            extent = [0, self.M * self.N / self.fs, 0, self.fs / 2]
            ax.set_xlabel("Time (s)")
        else:
            extent = [0.5, self.M + 0.5, 0, self.fs / 2]
            ax.set_xlabel("Block number")
        im = ax.imshow(S[:, ::stride], origin="lower", aspect="auto", extent=extent, cmap=CMAP,
                       vmin=self.floor, vmax=0 if self.floor < 0 else self.floor + 1, interpolation="nearest")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_ylim(self.f_lo, self.f_hi)
        self.fig.colorbar(im, ax=ax, label="dB")

    # -------------------------------------------------------------- saving
    def _suggest_name(self):
        base = os.path.splitext(os.path.basename(self.label or "output"))[0]
        tail = {"single": f"block{self.block}", "average": "average", "spectrogram": "spectrogram"}[self.mode]
        return f"{base}_{tail}.png"

    def save_png(self, path=None):
        """Save the displayed plot as PNG; with path=None a save dialog is shown."""
        try:
            if self.kind is None:
                self.log.error("nothing to save: no input file loaded")
                return False
            if path is None:
                path = filedialog.asksaveasfilename(
                    title="Save PNG", defaultextension=".png", filetypes=[("PNG image (*.png)", "*.png")],
                    initialfile=self._suggest_name())
                if not path:
                    self.log.info("save cancelled")
                    return False
            if not path.lower().endswith(".png"):
                path += ".png"
            self.fig.savefig(path, dpi=max(150, self.fig.dpi))
            self.log.info(f"file saved: {os.path.abspath(path)}")
            return True
        except Exception as exc:  # noqa: BLE001
            self.log.error(f"save failed: {exc}")
            return False

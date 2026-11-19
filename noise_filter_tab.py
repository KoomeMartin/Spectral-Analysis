"""Noise Filter tab: load a file, apply ONE filter at a time, preview before/after, save."""
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import audio_io
import filters
from ui_common import LogPane, PathField, guarded

try:
    import winsound
except ImportError:  # non-Windows
    winsound = None

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff")
MAX_PLOT_POINTS = 20000


class NoiseFilterTab(ttk.Frame):
    """Tab 1. `on_send(data, fs, label, kind)` hands a filtered result to the spectrum tab."""

    def __init__(self, master, on_send=None):
        super().__init__(master)
        self.on_send = on_send
        self.kind, self.path, self.fs = None, "", 1.0
        self.original = None   # audio [n_ch, L] or image 2-D
        self.result = None
        self.applied = None    # (filter name, params) that produced self.result
        self.param_vars = {}
        self._play_path = None
        self.filter_var = tk.StringVar()
        self._build()
        self.log = self.log_pane
        self._set_filter_choices(None)
        self._draw()
        self.log.info("Noise Filter tab ready. Load a .wav or image file (Browse...).")

    # ------------------------------------------------------------------ UI
    def _build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=4, pady=4)

        g = ttk.LabelFrame(bar, text="Input file")
        g.pack(side="left", fill="y", padx=2)
        self.in_field = PathField(g, on_browse=self.browse, width=24)
        self.in_field.pack(fill="x", padx=4, pady=2)
        self.info_var = tk.StringVar(value="No file loaded")
        ttk.Label(g, textvariable=self.info_var, wraplength=220).pack(anchor="w", padx=4)

        self.filter_frame = ttk.LabelFrame(bar, text="Filter")
        self.filter_frame.pack(side="left", fill="y", padx=2)

        self.param_frame = ttk.LabelFrame(bar, text="Parameters")
        self.param_frame.pack(side="left", fill="y", padx=2)

        g = ttk.LabelFrame(bar, text="Actions")
        g.pack(side="left", fill="y", padx=2)
        self.apply_btn = ttk.Button(g, text="Apply", command=self.apply)
        self.reset_btn = ttk.Button(g, text="Reset", command=self.reset)
        self.play_o = ttk.Button(g, text="Play original", command=lambda: self.play(False))
        self.play_f = ttk.Button(g, text="Play filtered", command=lambda: self.play(True))
        self.send_o_btn = ttk.Button(g, text="Analyze original", command=self.send_original)
        self.send_btn = ttk.Button(g, text="Analyze filtered", command=self.send_filtered)
        for i, b in enumerate([self.apply_btn, self.reset_btn, self.play_o, self.play_f,
                               self.send_o_btn, self.send_btn]):
            b.grid(row=i // 2, column=i % 2, padx=2, pady=1, sticky="ew")

        self.fig = Figure(figsize=(6, 3), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        out = ttk.LabelFrame(self, text="Output file")
        out.pack(fill="x", padx=4)
        self.out_field = PathField(out, on_browse=self.save, button_text="Save filtered...", width=60)
        self.out_field.pack(fill="x", padx=4, pady=2)

        self.log_pane = LogPane(self, height=6)
        self.log_pane.pack(fill="x", padx=4, pady=4)

    def _set_filter_choices(self, kind):
        for w in self.filter_frame.winfo_children():
            w.destroy()
        names = [n for n, f in filters.FILTERS.items() if kind is None or f.kind == kind]
        if kind is None:
            names = [n for n, f in filters.FILTERS.items() if f.kind == "audio"]
        self.filter_var.set(names[0])
        for n in names:
            ttk.Radiobutton(self.filter_frame, text=n, value=n, variable=self.filter_var,
                            command=self._build_params).pack(anchor="w")
        self._build_params()

    def _build_params(self):
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_vars = {}
        spec = filters.FILTERS[self.filter_var.get()]
        for r, (key, label, default) in enumerate(spec.params):
            ttk.Label(self.param_frame, text=label + ":").grid(row=r, column=0, sticky="e")
            v = tk.StringVar(value=f"{default:g}")
            self.param_vars[key] = v
            ttk.Entry(self.param_frame, textvariable=v, width=9).grid(row=r, column=1, padx=4, pady=1)
        self._refresh_controls()

    def _refresh_controls(self):
        loaded = self.kind is not None
        audio = self.kind == "audio"
        def st(w, on):
            w.state(["!disabled" if on else "disabled"])
        st(self.apply_btn, loaded)
        st(self.reset_btn, self.result is not None)
        playable = audio and winsound is not None
        st(self.play_o, playable)
        st(self.play_f, playable and self.result is not None)
        st(self.send_o_btn, loaded and self.on_send is not None)
        st(self.send_btn, self.result is not None and self.on_send is not None)

    # ------------------------------------------------------------- loading
    @guarded
    def browse(self):
        path = filedialog.askopenfilename(
            title="Open noisy audio or image",
            filetypes=[("Audio / image", "*.wav *.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff"), ("All files", "*.*")])
        if path:
            self.load_file(path)

    def load_file(self, path):
        """Load a file for filtering; on failure log ERROR and keep the previous state."""
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".wav":
                w = audio_io.load_wav(path)
                data, kind, fs = w.samples, "audio", float(w.fs)
                info = f"WAV, {w.n_channels} ch, {data.shape[1]} samples, Fs={fs:g} Hz"
            elif ext in IMAGE_EXTS:
                data, kind, fs = audio_io.load_image_color(path), "image", 1.0
                info = f"image, {data.shape[0]}x{data.shape[1]} px, colour"
            else:
                raise audio_io.AudioIOError(f"unsupported file type '{ext}'")
        except audio_io.AudioIOError as exc:
            self.log.error(f"{os.path.basename(path)}: {exc}")
            return False
        if kind != self.kind:
            self.kind = kind
            self._set_filter_choices(kind)
        self.kind, self.path, self.fs, self.original, self.result, self.applied = kind, path, fs, data, None, None
        self.in_field.set(path)
        self.info_var.set(info)
        self._refresh_controls()
        self._draw()
        self.log.info(f"file loaded: {os.path.basename(path)} ({info})")
        return True

    # ----------------------------------------------------------- filtering
    @guarded
    def apply(self):
        if self.kind is None:
            self.log.error("no input file loaded")
            return
        name = self.filter_var.get()
        try:
            params = {k: float(v.get()) for k, v in self.param_vars.items()}
        except ValueError:
            self.log.error("all parameters must be numbers")
            return
        try:
            result = filters.run_pipeline(self.original, self.fs, [(name, params)])
        except ValueError as exc:
            self.log.error(f"{name}: {exc}")
            return
        self.result, self.applied = result, (name, params)
        self._refresh_controls()
        self._draw()
        self.log.info(f"{name} applied: " + ", ".join(f"{k}={v:g}" for k, v in params.items()))

    def reset(self):
        self.result, self.applied = None, None
        self._refresh_controls()
        self._draw()
        self.log.info("result cleared")

    def _base(self):
        return os.path.splitext(os.path.basename(self.path))[0]

    def result_name(self):
        """Original name plus the filter tag, e.g. 'c_scale_s400r5000_notch_380-420_o4'."""
        return f"{self._base()}_{filters.filter_tag(*self.applied)}"

    def _for_spectrum(self, data):
        """The spectrum tab analyses grey images, so colour is converted for it only."""
        return audio_io.to_gray(data) if self.kind == "image" else data

    @guarded
    def send_original(self):
        if self.kind is None or self.on_send is None:
            return
        self.on_send(self._for_spectrum(self.original), self.fs, os.path.basename(self.path),
                     "wav" if self.kind == "audio" else "image")
        self.log.info(f"sent original {os.path.basename(self.path)} to Power Spectrum tab")

    @guarded
    def send_filtered(self):
        if self.result is None or self.on_send is None:
            return
        label = self.result_name()
        self.on_send(self._for_spectrum(self.result), self.fs, label, "wav" if self.kind == "audio" else "image")
        self.log.info(f"sent filtered result {label} to Power Spectrum tab")

    @guarded
    def play(self, filtered):
        data = self.result if filtered else self.original
        if winsound is None or data is None:
            self.log.info("playback is only available on Windows")
            return
        # winsound cannot play async from memory, so play a temp file (replaced on every call)
        winsound.PlaySound(None, winsound.SND_PURGE)
        if self._play_path and os.path.exists(self._play_path):
            try:
                os.remove(self._play_path)
            except OSError:
                pass
        fd, self._play_path = tempfile.mkstemp(suffix=".wav", prefix="nf_play_")
        os.close(fd)
        audio_io.save_wav(self._play_path, data, self.fs)
        winsound.PlaySound(self._play_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        self.log.info("playing " + ("filtered" if filtered else "original"))

    # -------------------------------------------------------------- saving
    def save(self, path=None):
        """Save the filtered result; with path=None a save dialog is shown."""
        try:
            if self.result is None:
                self.log.error("nothing to save: apply a filter first")
                return False
            ext = ".wav" if self.kind == "audio" else ".png"
            if path is None:
                base = self.result_name()
                ft = [("WAV audio", "*.wav")] if self.kind == "audio" else [("PNG image", "*.png"), ("BMP image", "*.bmp")]
                path = filedialog.asksaveasfilename(title="Save filtered", defaultextension=ext, filetypes=ft,
                                                    initialfile=f"{base}{ext}")
                if not path:
                    self.log.info("save cancelled")
                    return False
            if not os.path.splitext(path)[1]:
                path += ext
            if self.kind == "audio":
                audio_io.save_wav(path, self.result, self.fs)
            else:
                audio_io.save_image(path, self.result)
            self.out_field.set(os.path.abspath(path))
            self.log.info(f"file saved: {os.path.abspath(path)}")
            return True
        except Exception as exc:  # noqa: BLE001
            self.log.error(f"save failed: {exc}")
            return False

    # ------------------------------------------------------------- drawing
    def _draw(self):
        self.fig.clf()
        if self.kind is None:
            ax = self.fig.add_subplot(111)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.text(0.5, 0.5, "Load a .wav or image file (Browse...)", ha="center", va="center", transform=ax.transAxes)
        else:
            for i, (title, d) in enumerate([("Before (original)", self.original), ("After (filtered)", self.result)]):
                ax = self.fig.add_subplot(1, 2, i + 1) if self.kind == "image" else self.fig.add_subplot(2, 1, i + 1)
                ax.set_title(title, fontsize=9)
                if d is None:
                    ax.set_xticks([])
                    ax.set_yticks([])
                    ax.text(0.5, 0.5, "apply a filter", ha="center", va="center", transform=ax.transAxes)
                elif self.kind == "image":
                    ax.imshow(np.clip(d, 0, 1), cmap="gray" if d.ndim == 2 else None, vmin=0, vmax=1)
                    ax.axis("off")
                else:
                    x = np.atleast_2d(d)[0]
                    s = max(1, len(x) // MAX_PLOT_POINTS)
                    ax.plot(np.arange(0, len(x), s) / self.fs, x[::s], lw=0.5)
                    ax.set_ylim(-1, 1)
                    ax.set_xlabel("Time (s)")
        self.fig.tight_layout()
        self.canvas.draw_idle()

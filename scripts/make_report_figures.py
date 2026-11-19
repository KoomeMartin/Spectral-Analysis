"""Regenerate the report figures and the numbers quoted in the report.

Run from the Lab 3 folder:  python scripts/make_report_figures.py
Reads data/ and Submission/, writes latex/images/. Uses the app's own DSP modules.
"""
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import audio_io  # noqa: E402
import filters  # noqa: E402
import powerspec_dsp as dsp  # noqa: E402

DATA, SUB, OUT = (os.path.join(ROOT, d) for d in ("data", "Submission", os.path.join("latex", "images")))
os.makedirs(OUT, exist_ok=True)
CMAP = LinearSegmentedColormap.from_list("blue_red", ["blue", "red"])
FS = 16000
plt.rcParams.update({"font.size": 9, "axes.titlesize": 9})


def wav(path):
    return audio_io.load_wav(path).samples[0]


def snr(clean, y):
    n = min(len(clean), len(y))
    clean, y = clean[:n], y[:n]
    return 10 * np.log10(clean.var() / np.mean((y - clean) ** 2))


def spec_db(x, N, window, floor, ref=None):
    S = dsp.block_powers(x, N, window).T
    ref = S.max() if ref is None else ref
    with np.errstate(divide="ignore"):
        db = 10 * np.log10(np.maximum(S, 0) / ref)
    return np.maximum(np.where(np.isfinite(db), db, floor), floor), ref, S.shape[1]


def draw_spec(ax, x, N, window, floor, fmax, ref=None, title=None):
    db, ref, M = spec_db(x, N, window, floor, ref)
    im = ax.imshow(db, origin="lower", aspect="auto", cmap=CMAP, vmin=floor, vmax=0, interpolation="nearest",
                   extent=[0, M * N / FS, 0, FS / 2])
    ax.set_ylim(0, fmax)
    ax.set_ylabel("Frequency (Hz)")
    if title:
        ax.set_title(title)
    return im, ref


def copy_submission(src, dst):
    shutil.copy(os.path.join(SUB, src), os.path.join(OUT, dst))


# ---------------------------------------------------------------- Part I
def part1():
    copy_submission("c_scale_spectrogram.png", "p1_cscale_N2048.png")
    copy_submission("music_spectograph_128_blocks.png", "p1_music_N128.png")
    copy_submission("music_spectograph_16384_blocks.png", "p1_music_N16384.png")
    x = wav(os.path.join(DATA, "c_scale.wav"))

    # block size on the spectrogram
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True)
    for ax, N in zip(axes, (256, 8192)):
        im, _ = draw_spec(ax, x, N, "Rectangular", -40, 700,
                          title=f"N = {N}  (bin width {FS / N:g} Hz, block {1000 * N / FS:g} ms)")
    axes[-1].set_xlabel("Time (s)")
    fig.colorbar(im, ax=axes, label="dB")
    fig.savefig(os.path.join(OUT, "p1_cscale_N256_N8192.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)

    # single blocks: block size, then windows (steady block and transition block)
    def block_spectrum(N, window, t):
        P = dsp.block_powers(x, N, window)
        return dsp.freq_axis(N, FS), P[int(t * FS // N)]

    fig, ax = plt.subplots(figsize=(9, 3.4))
    for N, style in ((256, "-"), (2048, "-"), (8192, "-")):
        f, p = block_spectrum(N, "Rectangular", 2.5)
        ax.plot(f, np.maximum(10 * np.log10(p / p.max()), -60), style, lw=1.2, label=f"N = {N}")
    ax.set(xlim=(100, 600), ylim=(-62, 2), xlabel="Frequency (Hz)", ylabel="Power (dB re peak)")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_title("Single block at t = 2.5 s (330 Hz note), Rectangular window")
    fig.savefig(os.path.join(OUT, "p1_cscale_single_blocksize.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)

    N = 2048
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, (t, title) in zip(axes, ((2.5, "Steady block (block 20, 2.43 to 2.56 s)"),
                                    (4.0, "Transition block (block 32, 3.97 to 4.10 s)"))):
        curves = {w: block_spectrum(N, w, t) for w in ("Rectangular", "Hamming", "Hanning")}
        ref = max(c[1].max() for c in curves.values())
        for w, (f, p) in curves.items():
            ax.plot(f, np.maximum(10 * np.log10(np.maximum(p, 1e-30) / ref), -80), lw=1.2, label=w)
        ax.set(xlim=(100, 700), ylim=(-82, 2), xlabel="Frequency (Hz)", title=title)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Power (dB re peak)")
    axes[0].legend()
    fig.savefig(os.path.join(OUT, "p1_cscale_windows.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------- Part II audio
CASES = [  # key, noisy file, clean file, label, filter name, params, saved file or None, fmax
    ("cscale_nb", "c_scale_nb700-2000r8000", "c_scale", "Lowpass 600 Hz, order 4", "Lowpass", dict(cutoff=600, order=4),
     "c_scale_nb700-2000r8000_lowpass_c600_o4.wav", 4000),
    ("cscale_p1", "c_scale_p1r5000", "c_scale", "Lowpass 1000 Hz, order 4", "Lowpass", dict(cutoff=1000, order=4),
     "c_scale_p1r5000_lowpass_c1000_o4.wav", 8000),
    ("cscale_s400", "c_scale_s400r5000", "c_scale", "Notch 390 to 410 Hz, order 4", "Notch (band-reject)",
     dict(f_lo=390, f_hi=410, order=4), "c_scale_s400r5000_notch_390-410_o4.wav", 1000),
    ("music_nb400", "music_nb400-700r2000", "music", "Notch 400 to 700 Hz, order 4", "Notch (band-reject)",
     dict(f_lo=400, f_hi=700, order=4), "music_nb400-700r2000_notch_400-700_o4.wav", 2000),
    ("music_nb5000", "music_nb5000-7999r3000", "music", "Lowpass 3000 Hz, order 4", "Lowpass", dict(cutoff=3000, order=4),
     "music_nb5000-7999r3000_lowpass_c3000_o4.wav", 8000),
    ("music_p01", "music_p01r500", "music", "Median, window 3, threshold 0.01", "Median + threshold",
     dict(window=3, threshold=0.01), None, 8000),
    ("music_p05", "music_p05r2000", "music", "Median, window 3, threshold 0.001", "Median + threshold",
     dict(window=3, threshold=0.001), None, 8000),
    ("music_s120", "music_s120r7000", "music", "Notch 100 to 200 Hz, order 4", "Notch (band-reject)",
     dict(f_lo=100, f_hi=200, order=4), "music_s120r7000_notch_100-200_o4.wav", 1000),
    ("music_s350", "music_s350r5000", "music", "Notch 320 to 400 Hz, order 4", "Notch (band-reject)",
     dict(f_lo=320, f_hi=400, order=4), "music_s350r5000_notch_320-400_o4.wav", 1000),
]


def part2_audio():
    rows = []
    for key, noisy_name, clean_name, label, fname, params, saved, fmax in CASES:
        clean = wav(os.path.join(DATA, clean_name + ".wav"))
        noisy = wav(os.path.join(DATA, noisy_name + ".wav"))
        if saved and os.path.exists(os.path.join(SUB, saved)):
            filt, src = wav(os.path.join(SUB, saved)), "saved file"
        else:
            filt, src = filters.run_pipeline(noisy[None], FS, [(fname, params)])[0], "recomputed"
        fig, axes = plt.subplots(2, 1, figsize=(9, 5.0), sharex=True)
        _, ref = draw_spec(axes[0], noisy, 2048, "Hanning", -80, fmax, title="Before: " + noisy_name)
        im, _ = draw_spec(axes[1], filt, 2048, "Hanning", -80, fmax, ref=ref, title="After: " + label)
        axes[1].set_xlabel("Time (s)")
        fig.colorbar(im, ax=axes, label="dB re maximum of the noisy file")
        fig.savefig(os.path.join(OUT, f"p2_{key}.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)
        rows.append((noisy_name, label, snr(clean, noisy), snr(clean, filt), src))
    print("\nAUDIO (SNR vs clean, dB)")
    for r in rows:
        print(f"  {r[0]:28} {r[1]:36} {r[2]:6.1f} -> {r[3]:6.1f}  [{r[4]}]")


# --------------------------------------------------------------- Part II images
def part2_images():
    def run(img, name, **p):
        return np.clip(filters.run_pipeline(img, 1, [(name, p)]), 0, 1)

    def psnr(a, b):
        return 10 * np.log10(1 / np.mean((a - b) ** 2))

    pairs = [("photo", "photo_p1_r200", (170, 330, 400, 640)), ("text", "text_p1_r200", (85, 175, 60, 400))]
    for clean_name, noisy_name, (r0, r1, c0, c1) in pairs:
        clean = audio_io.load_image_color(os.path.join(DATA, clean_name + ".png"))
        noisy = audio_io.load_image_color(os.path.join(DATA, noisy_name + ".bmp"))
        variants = [("Clean", clean), ("Noisy", noisy), ("Median 3", run(noisy, "Median", size=3)),
                    ("Median 5", run(noisy, "Median", size=5)), ("Gaussian, sigma 1", run(noisy, "Gaussian", sigma=1)),
                    ("Gaussian, sigma 2", run(noisy, "Gaussian", sigma=2))]
        fig, axes = plt.subplots(2, 3, figsize=(10, 6.4 if clean_name == "photo" else 4.4))
        for ax, (t, im) in zip(axes.ravel(), variants):
            ax.imshow(im[r0:r1, c0:c1], interpolation="nearest")
            ax.set_title(t if t == "Clean" else f"{t}  (PSNR {psnr(clean, im):.1f} dB)")
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, f"p2_img_{clean_name}_compare.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)

    print("\nIMAGES (PSNR vs clean, dB, whole image)")
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.2))
    for ax, (clean_name, noisy_name) in zip(axes.ravel(), (("photo", "photo_p1_r200"), ("photo", "photo_p05_r100"),
                                                           ("text", "text_p1_r200"), ("text", "text_p05_r100"))):
        clean = audio_io.load_image_color(os.path.join(DATA, clean_name + ".png"))
        noisy = audio_io.load_image_color(os.path.join(DATA, noisy_name + ".bmp"))
        saved = os.path.join(SUB, noisy_name + "_median_k3.png")
        med = audio_io.load_image_color(saved) if os.path.exists(saved) else run(noisy, "Median", size=3)
        row = [psnr(clean, noisy), psnr(clean, med)] + [psnr(clean, run(noisy, n, **p)) for n, p in
              (("Median", dict(size=5)), ("Gaussian", dict(sigma=1)), ("Gaussian", dict(sigma=2)))]
        print(f"  {noisy_name:16} noisy {row[0]:.1f} | median3 {row[1]:.1f} | median5 {row[2]:.1f} | "
              f"gauss1 {row[3]:.1f} | gauss2 {row[4]:.1f}  [{'saved' if os.path.exists(saved) else 'recomputed'}]")
        ax.imshow(med)
        ax.set_title(f"{noisy_name}, median 3")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "p2_img_median3_all.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    part1()
    part2_audio()
    part2_images()
    print("\nfigures written to", OUT)

"""Pure filter functions (no tkinter) and a registry the Noise Filter tab builds its UI from."""
from collections import namedtuple

import numpy as np
from scipy import ndimage, signal


def _odd_int(v, name, minimum=1):
    if v != int(v) or int(v) < minimum or int(v) % 2 == 0:
        raise ValueError(f"{name} must be an odd integer >= {minimum}")
    return int(v)


def _order(v):
    if v != int(v) or int(v) < 1 or int(v) > 20:
        raise ValueError("order must be an integer 1..20")
    return int(v)


def median_threshold(x, window, threshold):
    """Replace samples that differ from the running median by more than threshold."""
    window = _odd_int(window, "window")
    if threshold < 0:
        raise ValueError("threshold must be >= 0")
    m = ndimage.median_filter(x, size=window, mode="nearest")
    return np.where(np.abs(x - m) > threshold, m, x)


def notch(x, fs, f_lo, f_hi, order):
    """Zero-phase Butterworth band-reject between f_lo and f_hi Hz."""
    if f_lo <= 0:
        raise ValueError("lower must be > 0 Hz (to remove everything below a frequency, use Highpass)")
    if f_hi <= f_lo:
        raise ValueError(f"upper ({f_hi:g}) must be greater than lower ({f_lo:g})")
    if f_hi >= fs / 2:
        raise ValueError(f"upper must be below Fs/2 ({fs / 2:g} Hz); to remove everything above a frequency, use Lowpass")
    sos = signal.butter(_order(order), [f_lo, f_hi], "bandstop", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def lowpass(x, fs, cutoff, order):
    """Zero-phase Butterworth lowpass at cutoff Hz."""
    if not 0 < cutoff < fs / 2:
        raise ValueError(f"cutoff must be between 0 and Fs/2 ({fs / 2:g} Hz)")
    sos = signal.butter(_order(order), cutoff, "lowpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def highpass(x, fs, cutoff, order):
    """Zero-phase Butterworth highpass at cutoff Hz (a small cutoff removes the DC offset)."""
    if not 0 < cutoff < fs / 2:
        raise ValueError(f"cutoff must be between 0 and Fs/2 ({fs / 2:g} Hz)")
    sos = signal.butter(_order(order), cutoff, "highpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def image_gaussian(img, sigma):
    """Gaussian blur with the given sigma (pixels)."""
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    return ndimage.gaussian_filter(img, sigma)


def image_median(img, size):
    """Median filter with an odd square kernel."""
    return ndimage.median_filter(img, size=_odd_int(size, "size"), mode="nearest")


def image_mean(img, size):
    """Mean (box) filter with an odd square kernel."""
    return ndimage.uniform_filter(img, size=_odd_int(size, "size"), mode="nearest")


Filter = namedtuple("Filter", "kind params fn")  # params: [(key, label, default)]

FILTERS = {
    "Median + threshold": Filter("audio", [("window", "Window (odd)", 5), ("threshold", "Threshold (0-1)", 0.05)],
                                 lambda x, fs, p: median_threshold(x, p["window"], p["threshold"])),
    "Notch (band-reject)": Filter("audio", [("f_lo", "Lower (Hz)", 350), ("f_hi", "Upper (Hz)", 450), ("order", "Order", 4)],
                                  lambda x, fs, p: notch(x, fs, p["f_lo"], p["f_hi"], p["order"])),
    "Lowpass": Filter("audio", [("cutoff", "Cutoff (Hz)", 4000), ("order", "Order", 4)],
                      lambda x, fs, p: lowpass(x, fs, p["cutoff"], p["order"])),
    "Highpass": Filter("audio", [("cutoff", "Cutoff (Hz)", 20), ("order", "Order", 4)],
                       lambda x, fs, p: highpass(x, fs, p["cutoff"], p["order"])),
    "Gaussian": Filter("image", [("sigma", "Sigma", 1.0)], lambda x, fs, p: image_gaussian(x, p["sigma"])),
    "Median": Filter("image", [("size", "Size (odd)", 3)], lambda x, fs, p: image_median(x, p["size"])),
    "Mean": Filter("image", [("size", "Size (odd)", 3)], lambda x, fs, p: image_mean(x, p["size"])),
}


def run_pipeline(data, fs, steps):
    """Apply [(filter_name, params)] in order; audio is [n_ch, L], image is [r, c] or [r, c, 3]."""
    out = np.asarray(data, dtype=float)
    for name, params in steps:
        f = FILTERS[name]
        if f.kind == "audio":
            out = np.vstack([f.fn(ch, fs, params) for ch in np.atleast_2d(out)])
        elif out.ndim == 3:  # colour image: filter each channel separately
            out = np.dstack([f.fn(out[..., c], fs, params) for c in range(out.shape[2])])
        else:
            out = f.fn(out, fs, params)
    return out


def _n(v):
    """Format a number for a file name (no dots)."""
    return f"{v:g}".replace(".", "p")


_TAGS = {  # filter -> function(params) -> list of tag parts
    "Median + threshold": lambda p: ["medthr", "w" + _n(p["window"]), "t" + _n(p["threshold"])],
    "Notch (band-reject)": lambda p: ["notch", f"{_n(p['f_lo'])}-{_n(p['f_hi'])}", "o" + _n(p["order"])],
    "Lowpass": lambda p: ["lowpass", "c" + _n(p["cutoff"]), "o" + _n(p["order"])],
    "Highpass": lambda p: ["highpass", "c" + _n(p["cutoff"]), "o" + _n(p["order"])],
    "Gaussian": lambda p: ["gauss", "s" + _n(p["sigma"])],
    "Median": lambda p: ["median", "k" + _n(p["size"])],
    "Mean": lambda p: ["mean", "k" + _n(p["size"])],
}


def filter_tag(name, params):
    """Return a file-name-safe tag such as 'notch_380-420_o4' or 'medthr_w5_t0p05'."""
    return "_".join(_TAGS[name](params))

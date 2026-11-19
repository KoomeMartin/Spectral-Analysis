"""Pure DSP for the Power Spectrum tab (no tkinter): transform, windows, blocking, dB."""
import math

import numpy as np
from scipy.signal import get_window as _get_window

WINDOWS = {"Rectangular": "boxcar", "Hamming": "hamming", "Hanning": "hann"}
MAX_SAMPLES = 100_000_000


def tmatrix(N):
    """Return the N x N real orthonormal sinusoidal transform matrix (testing only)."""
    n = np.arange(N)
    T = np.empty((N, N))
    T[0] = 1 / math.sqrt(N)
    for k in range(1, N // 2):
        T[k] = math.sqrt(2 / N) * np.cos(2 * np.pi * k * n / N)
    T[N // 2] = np.cos(np.pi * n) / math.sqrt(N)
    for k in range(N // 2 + 1, N):
        T[k] = math.sqrt(2 / N) * np.sin(2 * np.pi * (N - k) * n / N)
    return T


def transform_blocks(blocks):
    """Apply the orthonormal transform to each row of an M x N array using rfft."""
    blocks = np.atleast_2d(blocks)
    N = blocks.shape[1]
    X = np.fft.rfft(blocks, axis=1)
    c = np.empty(blocks.shape)
    c[:, 0] = X[:, 0].real / math.sqrt(N)
    c[:, N // 2] = X[:, N // 2].real / math.sqrt(N)
    c[:, 1:N // 2] = math.sqrt(2 / N) * X[:, 1:N // 2].real
    c[:, N - 1:N // 2:-1] = -math.sqrt(2 / N) * X[:, 1:N // 2].imag
    return c


def raw_power(coefs):
    """Convert M x N transform coefficients to M x (N/2+1) raw power spectra."""
    N = coefs.shape[1]
    P = np.empty((coefs.shape[0], N // 2 + 1))
    P[:, 0] = coefs[:, 0] ** 2
    P[:, N // 2] = coefs[:, N // 2] ** 2
    P[:, 1:N // 2] = coefs[:, 1:N // 2] ** 2 + coefs[:, N - 1:N // 2:-1] ** 2
    return P


def get_window(name, N):
    """Return the periodic window (Rectangular, Hamming or Hanning) of length N."""
    return _get_window(WINDOWS[name], N, fftbins=True)


def make_blocks(x, N):
    """Split a 1-D stream into M = ceil(L/N) non-overlapping blocks, zero-padding the last."""
    x = np.asarray(x, dtype=float)
    M = max(1, math.ceil(len(x) / N))
    padded = np.zeros(M * N)
    padded[:len(x)] = x
    return padded.reshape(M, N)


def block_powers(x, N, window="Rectangular"):
    """Return the M x (N/2+1) window-normalised linear power spectra of a stream."""
    w = get_window(window, N)
    blocks = make_blocks(x, N) * w
    return raw_power(transform_blocks(blocks)) / (np.sum(w ** 2) / N)


def average_power(P):
    """Average linear power spectra over blocks (never average dB)."""
    return P.mean(axis=0)


def to_db(P, floor):
    """Return (10*log10(P/Pmax) clipped at floor, all_zero flag); max is exactly 0 dB."""
    P = np.asarray(P, dtype=float)
    pmax = P.max()
    if pmax <= 0:
        return np.full(P.shape, float(floor)), True
    with np.errstate(divide="ignore"):
        db = 10 * np.log10(np.maximum(P, 0) / pmax)
    db = np.where(np.isfinite(db), db, floor)
    return np.maximum(db, floor), False


def freq_axis(N, fs):
    """Return the N/2+1 bin frequencies k*fs/N in Hz."""
    return np.arange(N // 2 + 1) * fs / N


def spectrogram_db(P, floor):
    """Return the (N/2+1) x M spectrogram in dB re its global maximum, floored."""
    return to_db(P.T, floor)

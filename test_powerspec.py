"""Acceptance tests E1-E13 for the Power Spectrum tab. Run: python test_powerspec.py"""
import math
import os
import tempfile
import tkinter as tk
import wave

import numpy as np

import powerspec_dsp as dsp

rng = np.random.default_rng(0)


def test_e1_orthonormal():
    for N in (16, 64, 512):
        T = dsp.tmatrix(N)
        assert np.allclose(T @ T.T, np.eye(N), atol=1e-9)


def test_e2_fft_equals_matrix():
    N = 16
    while N <= 4096:
        x = rng.standard_normal(N)
        assert np.allclose(dsp.transform_blocks(x[None])[0], dsp.tmatrix(N) @ x, atol=1e-9), N
        N *= 2


def test_e3_parseval():
    for N in (16, 256):
        x = rng.standard_normal(N)
        P = dsp.block_powers(x, N, "Rectangular")[0]
        assert abs(P.sum() - (x ** 2).sum()) < 1e-9


def test_e4_pure_tone():
    N, k0 = 64, 5
    n = np.arange(N)
    for x in (np.cos(2 * np.pi * k0 * n / N), np.sin(2 * np.pi * k0 * n / N)):
        P = dsp.block_powers(x, N)[0]
        assert abs(P[k0] - (x ** 2).sum()) < 1e-9 and np.argmax(P) == k0
        assert np.delete(P, k0).max() < 1e-9


def test_e5_1khz_peak():
    fs, N = 44100, 1024
    x = np.sin(2 * np.pi * 1000 * np.arange(fs) / fs)
    peak = np.argmax(dsp.average_power(dsp.block_powers(x, N)))
    assert abs(dsp.freq_axis(N, fs)[peak] - 1000) <= fs / N


def test_e6_blocks():
    x = np.ones(1000)
    b = dsp.make_blocks(x, 256)
    assert b.shape == (math.ceil(1000 / 256), 256)
    assert np.all(b[-1, 1000 - 3 * 256:] == 0) and np.all(b[-1, :1000 - 3 * 256] == 1)
    assert dsp.make_blocks(np.ones(5), 16).shape == (1, 16)


def test_e7_windows():
    N = 256
    x = rng.standard_normal(N)
    w = dsp.get_window("Rectangular", N)
    assert np.allclose(dsp.block_powers(x, N, "Rectangular"), dsp.raw_power(dsp.transform_blocks(x[None])))
    dc = np.ones(N)
    ref = dsp.block_powers(dc, N, "Rectangular")[0].sum()
    for name in ("Hamming", "Hanning"):
        tot = dsp.block_powers(dc, N, name)[0].sum()
        assert abs(tot - ref) / ref < 0.05, (name, tot, ref)
    assert w.min() == 1


def test_e8_average_then_db():
    P = np.array([[1.0, 100.0, 1.0], [100.0, 1.0, 1.0]])
    a_then_db = dsp.to_db(dsp.average_power(P), -100)[0]
    db_then_a = dsp.to_db(P, -100)[0].mean(axis=0)
    assert not np.allclose(a_then_db, db_then_a)


def test_e9_db():
    P = np.array([0.0, 1e-9, 0.5, 2.0])
    db, zero = dsp.to_db(P, -40)
    assert db.max() == 0 and db.min() >= -40 and db[0] == -40 and not zero
    assert dsp.to_db(np.zeros(4), -40)[1]


# ---- GUI-level tests (hidden Tk root) -----------------------------------
def _tab():
    from powerspec_tab import PowerSpecTab
    root = tk.Tk()
    root.withdraw()
    return root, PowerSpecTab(root)


def _write_wav(path, fs, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes((x * 20000).astype("<i2").tobytes())


def test_e10_e11_e12_e13_gui():
    root, tab = _tab()
    try:
        # E11 defaults
        assert (tab.N, tab.fs, tab.window, tab.floor, tab.scale, tab.mode, tab.block) == \
               (512, 1.0, "Rectangular", -40.0, "dB", "single", 1)
        assert (tab.f_lo, tab.f_hi) == (0, 0.5)
        d = tempfile.mkdtemp()
        wavp = os.path.join(d, "t.wav")
        _write_wav(wavp, 16000, np.sin(2 * np.pi * 1000 * np.arange(16000 * 2) / 16000))
        assert tab.load_file(wavp)
        # E12 range
        assert (tab.f_lo, tab.f_hi) == (0, 8000)
        tab.lo_var.set("500"); tab.hi_var.set("3000"); tab._on_freq()
        assert tab.ax.get_xlim() == (500, 3000)
        tab.mode_var.set("spectrogram"); tab._on_mode()
        assert tab.ax.get_ylim() == (500, 3000)
        for lo, hi in (("3000", "500"), ("-1", "100"), ("0", "9000"), ("abc", "100")):
            tab.lo_var.set(lo); tab.hi_var.set(hi); tab._on_freq()
            assert (tab.f_lo, tab.f_hi) == (500, 3000)
        errs = tab.log.text.get("1.0", "end").count("ERROR")
        assert errs == 4, errs
        # E10 saving, all three views, then bad path
        for mode, suffix in (("single", "block"), ("average", "average"), ("spectrogram", "spectrogram")):
            tab.mode_var.set(mode); tab._on_mode()
            out = os.path.join(d, f"{mode}.png")
            assert tab.save_png(out)
            with open(out, "rb") as f:
                assert f.read(4) == b"\x89PNG"
            assert suffix in tab._suggest_name()
        before = tab.log.text.get("1.0", "end").count("ERROR")
        assert tab.save_png(os.path.join(d, "no_such_dir", "x.png")) is False
        assert tab.log.text.get("1.0", "end").count("ERROR") == before + 1
        # block entry validation
        tab.mode_var.set("single"); tab._on_mode()
        tab.go_to_block("0"); tab.go_to_block("x"); tab.go_to_block(str(tab.M + 1))
        assert tab.block == 1
        tab.go_to_block("3"); assert tab.block == 3
        # bad file keeps state
        assert tab.load_file(os.path.join(d, "missing.wav")) is False and tab.kind == "wav"
        # E13 path wrapping
        root.geometry("900x700"); root.deiconify(); tab.pack(fill="both", expand=True); root.update()
        h0 = tab.path_field.display.winfo_height()
        tab.path_field.set("C:/" + "very_long_folder_name/" * 10 + "file.wav")
        root.update()
        assert int(tab.path_field.display.cget("wraplength")) > 1
        assert tab.path_field.display.winfo_height() > h0
    finally:
        root.destroy()


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("PASS", name)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, type(e).__name__, e)
    raise SystemExit(1 if fails else 0)

"""Tests for filters.py and audio_io.py. Run: python test_filters.py"""
import os
import struct
import tempfile

import numpy as np

import audio_io
import filters

FS = 8000
t = np.arange(FS) / FS


def rms(x):
    return float(np.sqrt(np.mean(np.square(x))))


def test_median_removes_spike_only():
    x = 0.3 * np.sin(2 * np.pi * 50 * t)
    y = x.copy()
    y[1000] += 0.9
    out = filters.median_threshold(y, 5, 0.1)
    assert abs(out[1000] - x[1000]) < 0.05
    mask = np.ones(len(x), bool); mask[1000] = False
    assert np.array_equal(out[mask], y[mask])


def test_notch_and_lowpass():
    x = np.sin(2 * np.pi * 400 * t) + np.sin(2 * np.pi * 1000 * t)
    n = filters.notch(x, FS, 350, 450, 4)
    spec = np.abs(np.fft.rfft(n)) / (FS / 2)
    assert spec[400] < 0.01 and abs(spec[1000] - 1) < 0.12   # >40 dB down at 400, 1 kHz kept
    lp = filters.lowpass(x, FS, 600, 6)
    spec = np.abs(np.fft.rfft(lp)) / (FS / 2)
    assert spec[1000] < 0.01 and spec[400] > 0.9


def test_highpass_removes_dc_keeps_tone():
    t10 = np.arange(FS * 10) / FS
    tone = np.sin(2 * np.pi * 400 * t10)
    y = filters.highpass(0.05 + tone, FS, 20, 4)
    assert abs(y[FS:-FS].mean()) < 1e-6 and abs(rms(y) - rms(tone)) < 0.01
    assert filters.filter_tag("Highpass", dict(cutoff=20, order=4)) == "highpass_c20_o4"


def test_validation():
    for fn in (lambda: filters.notch(np.zeros(100), FS, 0, 10, 4), lambda: filters.lowpass(np.zeros(100), FS, FS, 4),
               lambda: filters.median_threshold(np.zeros(10), 4, 0.1), lambda: filters.image_median(np.zeros((5, 5)), 2)):
        try:
            fn()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_image_filters_reduce_noise():
    rng = np.random.default_rng(1)
    img = np.full((64, 64), 0.5)
    noisy = img + rng.normal(0, 0.1, img.shape)
    for out in (filters.image_gaussian(noisy, 1.5), filters.image_median(noisy, 3), filters.image_mean(noisy, 3)):
        assert out.std() < noisy.std() / 2


def test_pipeline_multichannel():
    x = np.vstack([np.sin(2 * np.pi * 400 * t), np.sin(2 * np.pi * 1000 * t)])
    y = filters.run_pipeline(x, FS, [("Lowpass", dict(cutoff=700, order=4))])
    assert y.shape == x.shape and rms(y[1]) < 0.05 and rms(y[0]) > 0.6


def test_wav_roundtrip_and_formats():
    d = tempfile.mkdtemp()
    x = np.vstack([0.5 * np.sin(2 * np.pi * 300 * t), 0.25 * np.sin(2 * np.pi * 700 * t)])
    p = os.path.join(d, "a.wav")
    audio_io.save_wav(p, x, FS)
    w = audio_io.load_wav(p)
    assert w.fs == FS and w.n_channels == 2 and np.allclose(w.samples, x, atol=1e-4)
    # hand-built 24-bit and float32 mono files
    for bits, tag in ((24, 1), (32, 3)):
        v = 0.5 * np.sin(2 * np.pi * 300 * t[:800])
        if bits == 24:
            ints = (v * (2 ** 23 - 1)).astype(np.int32)
            data = b"".join(struct.pack("<i", i)[:3] for i in ints)
        else:
            data = v.astype("<f4").tobytes()
        hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack(
            "<IHHIIHH", 16, tag, 1, FS, FS * bits // 8, bits // 8, bits) + b"data" + struct.pack("<I", len(data))
        q = os.path.join(d, f"b{bits}.wav")
        open(q, "wb").write(hdr + data)
        assert np.allclose(audio_io.load_wav(q).samples[0], v, atol=1e-6)
    open(os.path.join(d, "bad.wav"), "wb").write(b"nope")
    try:
        audio_io.load_wav(os.path.join(d, "bad.wav"))
        raise AssertionError
    except audio_io.AudioIOError:
        pass


def test_colour_image_pipeline():
    rng = np.random.default_rng(2)
    img = np.dstack([np.full((32, 32), v) for v in (0.2, 0.5, 0.8)])
    noisy = np.clip(img + rng.normal(0, 0.1, img.shape), 0, 1)
    out = filters.run_pipeline(noisy, 1.0, [("Median", dict(size=3))])
    assert out.shape == (32, 32, 3) and out.std(axis=(0, 1)).max() < noisy.std(axis=(0, 1)).min()
    d = tempfile.mkdtemp(); p = os.path.join(d, "c.png")
    audio_io.save_image(p, out)
    back = audio_io.load_image_color(p)
    assert back.shape == out.shape and np.allclose(back, out, atol=1 / 255)
    assert audio_io.to_gray(back).shape == (32, 32)


def test_tab_flow():
    import tkinter as tk
    from noise_filter_tab import NoiseFilterTab
    root = tk.Tk(); root.withdraw()
    try:
        got = []
        tab = NoiseFilterTab(root, on_send=lambda *a: got.append(a))
        d = tempfile.mkdtemp()
        p = os.path.join(d, "n.wav")
        audio_io.save_wav(p, np.sin(2 * np.pi * 400 * t)[None], FS)
        assert tab.load_file(p)
        tab.filter_var.set("Lowpass"); tab._build_params()
        tab.param_vars["cutoff"].set("100"); tab.apply()
        assert tab.result is not None
        out = os.path.join(d, "o.wav")
        assert tab.save(out) and os.path.getsize(out) > 44
        tab.send_original(); tab.send_filtered()
        assert [g[2] for g in got] == ["n.wav", "n_lowpass_c100_o4"] and got[1][3] == "wav"
        assert tab.result_name() == "n_lowpass_c100_o4"
        tab.param_vars["cutoff"].set("99999"); tab.apply()
        assert "ERROR" in tab.log.text.get("1.0", "end")
    finally:
        root.destroy()


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("PASS", name)
            except Exception as e:  # noqa: BLE001
                fails += 1; print("FAIL", name, type(e).__name__, e)
    raise SystemExit(1 if fails else 0)

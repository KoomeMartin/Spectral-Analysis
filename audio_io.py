"""WAV and image loading/saving (no tkinter)."""
import struct
import wave
from dataclasses import dataclass

import numpy as np
from PIL import Image

MAX_SAMPLES = 100_000_000


class AudioIOError(Exception):
    """Raised for unreadable or unsupported files."""


@dataclass
class WavData:
    samples: np.ndarray  # [n_channels, L], float in -1..1
    fs: int
    n_channels: int
    bits: int
    is_float: bool


def load_wav(path):
    """Parse a WAV file (PCM 8/16/24/32, float32, EXTENSIBLE) into float samples in -1..1."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as exc:
        raise AudioIOError(f"cannot open file: {exc.strerror or exc}") from exc
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise AudioIOError("not a RIFF/WAVE file")
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(raw):
        cid, size = raw[pos:pos + 4], struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        body = pos + 8
        if cid == b"fmt ":
            fmt = raw[body:body + size]
        elif cid == b"data":
            data = raw[body:body + size] if size not in (0, 0xFFFFFFFF) else raw[body:]
            data = data[:len(raw) - body]
            break
        pos = body + size + (size & 1)
    if fmt is None or len(fmt) < 16:
        raise AudioIOError("missing or invalid fmt chunk")
    if data is None:
        raise AudioIOError("missing data chunk")
    tag, n_ch, fs, _, _, bits = struct.unpack("<HHIIHH", fmt[:16])
    if tag == 0xFFFE and len(fmt) >= 26:
        tag = struct.unpack("<H", fmt[24:26])[0]
    if tag not in (1, 3) or n_ch < 1:
        raise AudioIOError(f"unsupported WAV format (tag {tag}, {bits}-bit)")
    is_float = tag == 3
    if is_float and bits != 32:
        raise AudioIOError(f"unsupported float WAV width: {bits}-bit")
    if not is_float and bits not in (8, 16, 24, 32):
        raise AudioIOError(f"unsupported PCM width: {bits}-bit")
    width = bits // 8
    n_frames = len(data) // (width * n_ch)
    if n_frames == 0:
        raise AudioIOError("empty file (no samples)")
    if n_frames > MAX_SAMPLES:
        raise AudioIOError("file too large (> 100 million samples)")
    data = data[:n_frames * width * n_ch]
    if is_float:
        x = np.frombuffer(data, dtype="<f4").astype(float)
    elif bits == 8:
        x = (np.frombuffer(data, dtype=np.uint8).astype(float) - 128) / 128
    elif bits == 16:
        x = np.frombuffer(data, dtype="<i2").astype(float) / 32768
    elif bits == 24:
        b = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(float) / (1 << 23)
    else:
        x = np.frombuffer(data, dtype="<i4").astype(float) / 2 ** 31
    return WavData(x.reshape(n_frames, n_ch).T.copy(), fs, n_ch, bits, is_float)


def save_wav(path, samples, fs):
    """Write [n_channels, L] float samples (-1..1) as 16-bit PCM."""
    samples = np.atleast_2d(samples)
    pcm = (np.clip(samples, -1, 1) * 32767).round().astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(samples.shape[0])
        w.setsampwidth(2)
        w.setframerate(int(fs))
        w.writeframes(pcm.T.tobytes())


def load_image(path):
    """Load an image as a grey-scale float array in 0..1 (shape [rows, cols])."""
    try:
        with Image.open(path) as im:
            g = np.asarray(im.convert("L"), dtype=float) / 255
    except Exception as exc:  # noqa: BLE001
        raise AudioIOError(f"cannot read image: {exc}") from exc
    if g.size == 0:
        raise AudioIOError("empty image")
    return g


def load_image_color(path):
    """Load an image as an RGB float array in 0..1 (shape [rows, cols, 3]); alpha is dropped."""
    try:
        with Image.open(path) as im:
            a = np.asarray(im.convert("RGB"), dtype=float) / 255
    except Exception as exc:  # noqa: BLE001
        raise AudioIOError(f"cannot read image: {exc}") from exc
    if a.size == 0:
        raise AudioIOError("empty image")
    return a


def to_gray(array):
    """Convert an [r, c, 3] RGB array to grey (0.299R + 0.587G + 0.114B); 2-D input passes through."""
    a = np.asarray(array, dtype=float)
    return a if a.ndim == 2 else a @ np.array([0.299, 0.587, 0.114])


def save_image(path, array):
    """Save a 0..1 grey [r, c] or RGB [r, c, 3] array as an image (format from the extension)."""
    a = (np.clip(array, 0, 1) * 255).round().astype(np.uint8)
    Image.fromarray(a, "L" if a.ndim == 2 else "RGB").save(path)

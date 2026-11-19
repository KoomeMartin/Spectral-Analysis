"""Shared Tkinter widgets: LogPane (per-tab log) and PathField (wrapping file path field)."""
import functools
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class LogPane(ttk.Frame):
    """Read-only scrolled log; lines look like 'HH:MM:SS LEVEL: message'."""

    def __init__(self, master, height=6):
        super().__init__(master)
        self.text = ScrolledText(self, height=height, wrap="word", state="disabled",
                                 font=("Courier New", 9))
        self.text.pack(fill="both", expand=True)
        self.text.tag_configure("ERROR", foreground="red")

    def _write(self, level, msg):
        line = f"{time.strftime('%H:%M:%S')} {level}: {msg}\n"
        self.text.configure(state="normal")
        self.text.insert("end", line, level)
        self.text.see("end")
        self.text.configure(state="disabled")

    def info(self, msg):
        self._write("INFO", msg)

    def error(self, msg):
        self._write("ERROR", msg)


class PathField(ttk.Frame):
    """Browse button plus a read-only path display that wraps (mid-word if needed) to its width."""

    def __init__(self, master, on_browse=None, button_text="Browse...", width=24):
        super().__init__(master)
        self.on_browse = on_browse
        self.button = ttk.Button(self, text=button_text, command=self._browse)
        self.button.grid(row=0, column=0, sticky="nw", padx=(0, 4))
        self.display = tk.Label(self, text="", anchor="nw", justify="left", relief="sunken",
                                bg="white", width=width, wraplength=1)
        self.display.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.display.bind("<Configure>", self._on_resize)

    def _browse(self):
        if self.on_browse:
            self.on_browse()

    def _on_resize(self, event):
        # Wrap width tracks the field width, so the whole path stays visible after a resize.
        self.display.configure(wraplength=max(event.width - 6, 1))

    def set(self, path):
        self.display.configure(text=path)

    def get(self):
        return self.display.cget("text")

    def set_enabled(self, enabled):
        self.button.state(["!disabled" if enabled else "disabled"])


def guarded(method):
    """Decorator: log any unexpected exception to self.log instead of crashing the UI."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - last line of defence for UI callbacks
            self.log.error(f"{type(exc).__name__}: {exc}")
    return wrapper

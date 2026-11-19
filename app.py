"""Entry point: the 'Noise Filter' window with a ttk.Notebook of two tabs."""
import tkinter as tk
from tkinter import ttk

from noise_filter_tab import NoiseFilterTab
from powerspec_tab import PowerSpecTab


class NoiseFilterApp:
    def __init__(self, root):
        root.title("Noise Filter")
        root.geometry("1130x790")
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self.ps = PowerSpecTab(self.notebook)
        self.nf = NoiseFilterTab(self.notebook, on_send=self._send_to_spectrum)
        self.notebook.add(self.nf, text="Noise Filter")
        self.notebook.add(self.ps, text="Power Spectrum")

    def _send_to_spectrum(self, data, fs, label, kind):
        self.ps.load_array(data, fs, label, kind)
        self.notebook.select(self.ps)


def main():
    root = tk.Tk()
    NoiseFilterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

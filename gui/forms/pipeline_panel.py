"""
Правая область: блок «Файлы» + блок «Прогресс».
"""

import os
import customtkinter as ctk
import tkinter as tk


class PipelinePanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Файлы
        self.grid_rowconfigure(1, weight=1)  # Прогресс

        self._build_files()
        self._build_progress()

    # ---- Файлы --------------------------------------------------------
    def _build_files(self):
        frm = ctk.CTkFrame(self)
        frm.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        frm.grid_columnconfigure(1, weight=1)
        frm.grid_columnconfigure(2, weight=0)
        for r in range(2):
            frm.grid_rowconfigure(r, weight=0)

        labels = ["Входной PDF:", "Выходная папка:"]
        self._file_entries = {}
        self._file_paths = {}

        for r, label in enumerate(labels):
            ctk.CTkLabel(frm, text=label, width=115, anchor="w").grid(row=r, column=0, sticky="w", padx=(10, 0), pady=3)
            txt = ctk.CTkTextbox(frm, height=22, width=300)
            txt.grid(row=r, column=1, sticky="ew", padx=(5, 5), pady=3)
            txt.configure(state="disabled")
            self._file_entries[label] = txt
            self._file_paths[label] = ""

        # Кнопки
        btn_frame = ctk.CTkFrame(frm)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.btn_pdf = ctk.CTkButton(btn_frame, text="Выбрать PDF", width=110, height=28, font=ctk.CTkFont(size=13),
                                      command=self.browse_pdf)
        self.btn_pdf.grid(row=0, column=0, padx=5, pady=2)
        self.btn_dir = ctk.CTkButton(btn_frame, text="Выбрать папку", width=110, height=28, font=ctk.CTkFont(size=13),
                                      command=self.browse_dir, state="disabled")
        self.btn_dir.grid(row=0, column=1, padx=5, pady=2)

    def _set_file(self, label, path):
        w = self._file_entries[label]
        w.configure(state="normal")
        w.delete("1.0", "end")
        w.insert("1.0", path or "")
        w.configure(state="disabled")
        self._file_paths[label] = path

    @property
    def input_pdf(self):
        return self._file_paths.get("Входной PDF:", "")

    @property
    def output_dir(self):
        return self._file_paths.get("Выходная папка:", "")

    def set_input_pdf(self, path):
        self._set_file("Входной PDF:", path)
        book = os.path.splitext(os.path.basename(path))[0]
        self.set_output_dir(f"/mnt/project/rendered/{book}")
        self.btn_dir.configure(state="normal")

    def set_output_dir(self, path):
        self._set_file("Выходная папка:", path)

    # ---- Прогресс -----------------------------------------------------
    def _build_progress(self):
        frm = ctk.CTkFrame(self)
        frm.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        frm.grid_columnconfigure(0, weight=1)
        for r in range(5):
            frm.grid_rowconfigure(r, weight=0)

        steps = [("Извлечение", 0), ("Перевод", 1), ("Сборка PDF", 2)]
        self._bars = {}
        self._step_labels = {}

        for label, idx in steps:
            ctk.CTkLabel(frm, text=label, width=75, anchor="w").grid(row=idx, column=0, sticky="w", padx=(10, 0), pady=2)
            bar = ctk.CTkProgressBar(frm, orientation="horizontal", height=14)
            bar.grid(row=idx, column=1, sticky="ew", padx=(5, 10), pady=2)
            bar.set(0)
            self._bars[label] = bar

        # Счётчик чанков (под Перевод)
        self.lbl_chunks = ctk.CTkLabel(frm, text="Чанков: -- / --", width=150, anchor="e", font=ctk.CTkFont(size=13))
        self.lbl_chunks.grid(row=3, column=1, sticky="e", padx=(5, 10), pady=2)

        # Активных серверов
        self.lbl_servers = ctk.CTkLabel(frm, text="Серверов: --", width=100, anchor="e", font=ctk.CTkFont(size=13))
        self.lbl_servers.grid(row=4, column=1, sticky="e", padx=(5, 10), pady=2)

    # ---- Public API ---------------------------------------------------
    def set_progress(self, step_name, pct, chunks=None, servers=None):
        bar = self._bars.get(step_name)
        if bar:
            bar.set(pct / 100)
        if chunks:
            cur, total = chunks
            self.lbl_chunks.configure(text=f"Чанков: {cur} / {total} ({pct}%)")
        if servers is not None:
            self.lbl_servers.configure(text=f"Серверов: {servers}")

    def reset(self):
        for bar in self._bars.values():
            bar.set(0)
        self.lbl_chunks.configure(text="Чанков: -- / --")
        self.lbl_servers.configure(text="Серверов: --")

    # ---- File dialogs -------------------------------------------------
    def browse_pdf(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if p:
            self.set_input_pdf(p)

    def browse_dir(self):
        from tkinter import filedialog
        p = filedialog.askdirectory()
        if p:
            self.set_output_dir(p)

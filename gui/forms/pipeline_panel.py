"""
Вкладки пайплайна: Извлечение → Перевод → Сборка PDF.
"""
import os
import customtkinter as ctk


class PipelineTabs(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.tab_ext = self.tabview.add("1. Извлечение")
        self.tab_trn = self.tabview.add("2. Перевод")
        self.tab_pdf = self.tabview.add("3. Сборка PDF")

        self._paths = {}

        self._build_extraction()
        self._build_translation()
        self._build_compile()

    # ---- helpers ----
    def _textentry(self, parent, row, sticky="ew"):
        txt = ctk.CTkTextbox(parent, height=24)
        txt.grid(row=row, column=0, columnspan=2, sticky=sticky, padx=(15, 10), pady=4)
        txt.configure(state="disabled")
        return txt

    def _set_path(self, key, path):
        self._paths[key] = path or ""
        w = getattr(self, f"_txt_{key}", None)
        if w:
            w.configure(state="normal")
            w.delete("1.0", "end")
            w.insert("1.0", path or "")
            w.configure(state="disabled")

    # ---- 1. Извлечение ----
    def _build_extraction(self):
        t = self.tab_ext
        t.grid_columnconfigure(1, weight=1)

        r = 0
        ctk.CTkLabel(t, text="Входной PDF", width=100, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(15, 0), pady=3)
        self._txt_input_pdf = self._textentry(t, r + 1)
        r = 3
        ctk.CTkLabel(t, text="Выходная папка", width=100, anchor="w").grid(
            row=r, column=0, sticky="w", padx=(15, 0), pady=3)
        self._txt_output_dir = self._textentry(t, r + 1)
        r = 5

        btn_frm = ctk.CTkFrame(t)
        btn_frm.grid(row=r, column=0, columnspan=2, sticky="w", padx=(15, 10), pady=5)
        self.btn_pdf = ctk.CTkButton(btn_frm, text="Выбрать PDF", width=120, height=28,
                                      font=ctk.CTkFont(size=13), command=self.browse_pdf)
        self.btn_pdf.grid(row=0, column=0, padx=5)
        self.btn_dir = ctk.CTkButton(btn_frm, text="Выбрать папку", width=120, height=28,
                                      font=ctk.CTkFont(size=13),
                                      command=self.browse_dir, state="disabled")
        self.btn_dir.grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_frm, text="▶ Запустить", width=120, height=28,
                       font=ctk.CTkFont(size=13), fg_color="#42a5f5",
                       command=lambda: self.app.run_step("ext")).grid(row=0, column=2, padx=5)

    # ---- 2. Перевод ----
    def _build_translation(self):
        t = self.tab_trn
        t.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(t, text="Выбранный файл .md", width=100, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(15, 0), pady=3)
        self._txt_md_file = self._textentry(t, 1)

        btn_frm = ctk.CTkFrame(t)
        btn_frm.grid(row=2, column=0, columnspan=2, sticky="w", padx=(15, 10), pady=5)
        ctk.CTkButton(btn_frm, text="Выбрать .md", width=120, height=28,
                       font=ctk.CTkFont(size=13), command=self.browse_md).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frm, text="▶ Запустить", width=120, height=28,
                       font=ctk.CTkFont(size=13), fg_color="#ab47bc",
                       command=lambda: self.app.run_step("trn")).grid(row=0, column=1, padx=5)

    # ---- 3. Сборка PDF ----
    def _build_compile(self):
        t = self.tab_pdf
        t.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(t, text="Переведённый _ru.md", width=100, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(15, 0), pady=3)
        self._txt_ru_md_file = self._textentry(t, 1)

        btn_frm = ctk.CTkFrame(t)
        btn_frm.grid(row=2, column=0, columnspan=2, sticky="w", padx=(15, 10), pady=5)
        ctk.CTkButton(btn_frm, text="Выбрать _ru.md", width=120, height=28,
                       font=ctk.CTkFont(size=13), command=self.browse_ru_md).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frm, text="▶ Собрать PDF", width=120, height=28,
                       font=ctk.CTkFont(size=13), fg_color="#ff9800",
                       command=lambda: self.app.run_step("pdf")).grid(row=0, column=1, padx=5)

    # ---- public API ----
    @property
    def input_pdf(self):
        return self._paths.get("input_pdf", "")

    @property
    def output_dir(self):
        return self._paths.get("output_dir", "")

    @property
    def md_file(self):
        return self._paths.get("md_file", "")

    @property
    def ru_md_file(self):
        return self._paths.get("ru_md_file", "")

    def set_input_pdf(self, path):
        self._set_path("input_pdf", path)
        book = os.path.splitext(os.path.basename(path))[0]
        self.set_output_dir(f"/mnt/project/rendered/{book}")
        self.btn_dir.configure(state="normal")

    def set_output_dir(self, path):
        self._set_path("output_dir", path)

    def set_md_file(self, path):
        self._set_path("md_file", path)
        ru_path = path.replace(".md", "_ru.md")
        self._set_path("ru_md_file", ru_path)
        self._set_path("output_dir", os.path.dirname(path))

    def set_ru_md_file(self, path):
        self._set_path("ru_md_file", path)
        self._set_path("output_dir", os.path.dirname(path))

    def set_progress(self, step, pct, chunks=None, servers=None):
        pass  # прогрессбары убраны

    def reset(self):
        pass  # прогрессбары убраны

    # ---- file dialogs ----
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

    def browse_md(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(filetypes=[("Markdown files", "*.md")])
        if p:
            self.set_md_file(p)

    def browse_ru_md(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(filetypes=[("Markdown files", "*.md")])
        if p:
            self.set_ru_md_file(p)

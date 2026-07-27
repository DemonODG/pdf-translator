"""
Левая панель настроек с вкладками:
- Извлечение (Extraction)
- Перевод (Translation)
- Сборка PDF (Compile)
"""
import tkinter as tk
import customtkinter as ctk


class SettingsPanel(ctk.CTkFrame):
    """Панель настроек с вкладками."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.tab_ext = self.tabview.add("Извлечение")
        self.tab_trn = self.tabview.add("Перевод")
        self.tab_pdf = self.tabview.add("Сборка PDF")

        self.entry_input_pdf   = None
        self.entry_output_dir  = None
        self.entry_server_pool = None
        self.entry_api_key     = None
        self.entry_model_name  = None
        self.entry_fontsize    = None
        self.entry_mainfont    = None
        self.entry_monofont    = None
        self.cb_use_llm        = tk.BooleanVar(value=True)

        self._build_ext()
        self._build_trn()
        self._build_pdf()

    # --- helpers ---
    def _le(self, parent, label, row, entry=None):
        ctk.CTkLabel(parent, text=label, width=80, anchor="e", font=ctk.CTkFont(size=13)).grid(
            row=row, column=0, padx=10, pady=5, sticky="e")
        e = ctk.CTkEntry(parent, height=28, font=ctk.CTkFont(size=13)) if entry is None else entry
        e.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        return e

    # --- tabs ---
    def _build_ext(self):
        t = self.tab_ext; t.grid_columnconfigure(1, weight=1)
        self.entry_input_pdf   = self._le(t, "Input PDF:",    0)
        self.entry_output_dir  = self._le(t, "Output Dir:",   1)
        frm = ctk.CTkFrame(t)
        frm.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(frm, text="Use LLM:", width=80, anchor="e").grid(row=0, column=0, sticky="e")
        ctk.CTkCheckBox(frm, text="", variable=self.cb_use_llm).grid(row=0, column=1, sticky="w")

    def _build_trn(self):
        t = self.tab_trn; t.grid_columnconfigure(1, weight=1)
        self.entry_server_pool = ctk.CTkTextbox(t, height=80)
        self.entry_server_pool.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        t.grid_rowconfigure(0, weight=1)
        self.entry_api_key    = self._le(t, "API Key:",   1)
        self.entry_model_name = self._le(t, "Model Name:", 2)

    def _build_pdf(self):
        t = self.tab_pdf; t.grid_columnconfigure(1, weight=1)
        self.entry_fontsize  = self._le(t, "Font Size:", 0)
        self.entry_mainfont  = self._le(t, "Main Font:", 1)
        self.entry_monofont  = self._le(t, "Mono Font:", 2)

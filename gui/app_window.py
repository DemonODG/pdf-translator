"""
Главное окно приложения PDF Translator.
"""
import os
import customtkinter as ctk

from gui.forms.settings_panel import SettingsPanel
from gui.forms.pipeline_panel import PipelineTabs
from gui.forms.log_panel import LogPanel
from gui.config_loader import ConfigLoader
from gui.pipeline_runner import PipelineRunner


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF Translator")
        self.geometry("950x750")
        self.minsize(950, 750)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.config = ConfigLoader()
        self.runner = PipelineRunner(self)
        self.settings = None
        self._running = False
        self.cb_run_all = ctk.BooleanVar(value=False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=0)   # pipeline tabs (fixed height)
        self.grid_rowconfigure(2, weight=0)   # run controls
        self.grid_rowconfigure(3, weight=1)   # log (scales)

        self._build_header()
        self._build_pipeline()
        self._build_run_controls()
        self._build_log()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----------------------------------------------------------------
    def _build_header(self):
        frm = ctk.CTkFrame(self, height=36)
        frm.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 3))
        frm.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(frm, text="PDF Translator",
                      font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(15, 0))

        self.lbl_status = ctk.CTkLabel(
            frm, text="Готово", font=ctk.CTkFont(size=13), text_color="#cccccc")
        self.lbl_status.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(frm, text="⚙ Настройки", width=110, height=26,
                       command=self._open_settings).grid(
            row=0, column=3, sticky="e", padx=(0, 15))

    # ----------------------------------------------------------------
    def _build_pipeline(self):
        self.pipeline = PipelineTabs(self)
        self.pipeline.app = self
        self.pipeline.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

    # ----------------------------------------------------------------
    def _build_run_controls(self):
        frm = ctk.CTkFrame(self, height=44)
        frm.grid(row=2, column=0, sticky="ew", padx=5, pady=3)
        frm.grid_rowconfigure(0, weight=1)
        frm.grid_columnconfigure(4, weight=1)

        ctk.CTkCheckBox(frm, text="Выполнить все шаги",
                         variable=self.cb_run_all).grid(
            row=0, column=0, padx=(10, 0), sticky="w")

        self.btn_go = ctk.CTkButton(frm, text="▶ Пуск", width=100, height=30,
                                     fg_color="#26a69a",
                                     font=ctk.CTkFont(size=13),
                                     command=self.go,
                                     state="disabled")
        self.btn_go.grid(row=0, column=1, padx=8)

        self.btn_stop = ctk.CTkButton(frm, text="⏹ Стоп", width=100, height=30,
                                       fg_color="#ef5350",
                                       font=ctk.CTkFont(size=13),
                                       command=self.stop_pipeline)
        self.btn_stop.grid(row=0, column=2, padx=8)

        def on_toggle(*_):
            self.btn_go.configure(
                state="normal" if self.cb_run_all.get() else "disabled")
        self.cb_run_all.trace_add("write", on_toggle)

    # ----------------------------------------------------------------
    def _build_log(self):
        self.log = LogPanel(self)
        self.log.grid(row=3, column=0, sticky="nsew", padx=5, pady=(3, 5))

    # ----------------------------------------------------------------
    def _open_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Настройки")
        dialog.geometry("520x480")
        dialog.transient(self)
        dialog.focus()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        self.settings = SettingsPanel(dialog)
        self.settings.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.config.load_into(self)

        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 15))

        ctk.CTkButton(btn_frame, text="Сохранить и закрыть", width=160, height=32,
                       command=lambda: self._close_settings(dialog)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Отмена", width=100, height=32,
                       command=dialog.destroy).pack(side="left", padx=5)

        dialog.update_idletasks()
        dialog.grab_set()

    def _close_settings(self, dialog):
        self.config.collect_from(self)
        self.config.save("all")
        dialog.destroy()
        self.log.write("Конфигурация сохранена", "INFO")

    # ----------------------------------------------------------------
    def set_running(self, state):
        self._running = state
        self.lbl_status.configure(
            text="⏳ Работает..." if state else "Готово",
            text_color="#ffdd00" if state else "#00ff88")
        self.btn_go.configure(state="disabled" if state else ("normal" if self.cb_run_all.get() else "disabled"))
        ctk.CTk.config(self, cursor="watch" if state else "")

    # ----------------------------------------------------------------
    def go(self):
        """Запуск — либо все шаги, либо текущая вкладка."""
        if self.cb_run_all.get():
            self.run_all()
        else:
            tab = self.pipeline.tabview.get()
            if "Извлечение" in tab:
                self.run_step("ext")
            elif "Перевод" in tab:
                self.run_step("trn")
            elif "Сборка" in tab:
                self.run_step("pdf")

    def run_step(self, step):
        if step == "ext":
            self._run_extraction()
        elif step == "trn":
            self._run_translation()
        elif step == "pdf":
            self._run_compile()

    def run_all(self):
        pdf, odir = self.pipeline.input_pdf, self.pipeline.output_dir
        if not pdf:
            self.log.write("Укажите входной PDF", "WARNING"); return
        if not odir:
            self.log.write("Укажите выходную папку", "WARNING"); return
        self.pipeline.reset()
        s = self.settings
        pr = s.entry_page_range.get() if s else ""
        llm = s.cb_use_llm.get() if s else True
        self.runner.run_all(pdf, odir, page_range=pr, use_llm=llm)

    def stop_pipeline(self):
        self.runner.stop()

    def _on_close(self):
        ctk.CTk.config(self, cursor="")
        self.destroy()

    # ----------------------------------------------------------------
    def _run_extraction(self):
        pdf = self.pipeline.input_pdf
        odir = self.pipeline.output_dir
        if not pdf:
            self.log.write("Укажите входной PDF", "WARNING"); return
        if not odir:
            self.log.write("Укажите выходную папку", "WARNING"); return
        self.pipeline.reset()
        s = self.settings
        pr = s.entry_page_range.get() if s else ""
        llm = s.cb_use_llm.get() if s else True
        self.runner.run_extraction(pdf, odir, page_range=pr, use_llm=llm)

    def _run_translation(self):
        md = self.pipeline.md_file
        if not md:
            self.log.write("Выберите файл .md", "WARNING"); return
        self.pipeline.reset()
        self.runner.run_translation(os.path.dirname(md))

    def _run_compile(self):
        ru = self.pipeline.ru_md_file
        if not ru:
            self.log.write("Выберите файл _ru.md", "WARNING"); return
        self.pipeline.reset()
        pdf = ru.replace(".md", ".pdf")
        self.runner.run_compile(ru, pdf)

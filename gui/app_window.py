"""
Главное окно приложения PDF Translator.
"""
import customtkinter as ctk

from gui.forms.settings_panel import SettingsPanel
from gui.forms.pipeline_panel import PipelinePanel
from gui.forms.log_panel import LogPanel
from gui.config_loader import ConfigLoader
from gui.pipeline_runner import PipelineRunner


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF Translator")
        self.geometry("1100x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.config = ConfigLoader()
        self.runner = PipelineRunner(self)
        self.settings = None
        self._running = False

        # Grid: 1 col, 5 rows
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=2)   # main
        self.grid_rowconfigure(2, weight=0)   # controls
        self.grid_rowconfigure(3, weight=1)   # log
        self.grid_rowconfigure(4, weight=0)   # statusbar

        self._build_header()
        self._build_main()
        self._build_controls()
        self._build_log()
        self._build_statusbar()

    # ----------------------------------------------------------------
    def _build_header(self):
        frm = ctk.CTkFrame(self, height=44)
        frm.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 3))
        frm.grid_columnconfigure(3, weight=1)
        frm.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(frm, text="PDF Translator", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(15, 0))

        self.lbl_stage = ctk.CTkLabel(
            frm, text="● Извлечение  →  ○ Перевод  →  ○ Сборка PDF",
            font=ctk.CTkFont(size=14), text_color="#00ff88")
        self.lbl_stage.grid(row=0, column=1, sticky="w", padx=(20, 0))

        self.lbl_status = ctk.CTkLabel(
            frm, text="Готово", font=ctk.CTkFont(size=13), text_color="#cccccc")
        self.lbl_status.grid(row=0, column=2, sticky="e", padx=(20, 0))

        self.lbl_time = ctk.CTkLabel(
            frm, text="", font=ctk.CTkFont(size=13), text_color="#888888")
        self.lbl_time.grid(row=0, column=3, sticky="e", padx=(0, 5))

        ctk.CTkButton(frm, text="⚙ Настройки", width=120, height=28,
                       command=self._open_settings).grid(
            row=0, column=4, sticky="e", padx=(0, 15))

    # ----------------------------------------------------------------
    def _build_main(self):
        self.pipeline = PipelinePanel(self)
        self.pipeline.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    # ----------------------------------------------------------------
    def _build_controls(self):
        frm = ctk.CTkFrame(self, height=44)
        frm.grid(row=2, column=0, sticky="ew", padx=5, pady=3)
        frm.grid_rowconfigure(0, weight=1)
        frm.grid_columnconfigure(5, weight=1)

        btns = [
            ("▶ Всё",       self.run_all,        "#26a69a"),
            ("▶ Извлечение", self.run_extraction, "#42a5f5"),
            ("▶ Перевод",   self.run_translation, "#ab47bc"),
            ("▶ Сборка PDF", self.run_compile,    "#ffa726"),
            ("⏹ Стоп",     self.stop_pipeline,   "#ef5350"),
        ]
        for i, (text, cmd, color) in enumerate(btns):
            ctk.CTkButton(frm, text=text, width=115, height=34, fg_color=color,
                           hover_color=self._darker(color), command=cmd).grid(
                row=0, column=i, padx=8, pady=3, sticky="w")

    @staticmethod
    def _darker(hex_color):
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        return f"#{int(r*0.85):02x}{int(g*0.85):02x}{int(b*0.85):02x}"

    # ----------------------------------------------------------------
    def _build_log(self):
        self.log = LogPanel(self)
        self.log.grid(row=3, column=0, sticky="nsew", padx=5, pady=(3, 5))

    # ----------------------------------------------------------------
    def _build_statusbar(self):
        frm = ctk.CTkFrame(self, height=24)
        frm.grid(row=4, column=0, sticky="ew")
        frm.grid_columnconfigure(2, weight=1)
        frm.grid_rowconfigure(0, weight=1)

        self.lbl_step = ctk.CTkLabel(frm, text="Этап: --", font=ctk.CTkFont(size=12), text_color="#aaaaaa")
        self.lbl_step.grid(row=0, column=0, sticky="w", padx=(10, 0))

        self.lbl_chunks = ctk.CTkLabel(frm, text="Чанков: -- / --", font=ctk.CTkFont(size=12), text_color="#aaaaaa")
        self.lbl_chunks.grid(row=0, column=1, sticky="w", padx=(20, 0))

        self.lbl_srv = ctk.CTkLabel(frm, text="Серверов: --", font=ctk.CTkFont(size=12), text_color="#aaaaaa")
        self.lbl_srv.grid(row=0, column=3, sticky="e", padx=(0, 10))

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
        for btn in self.grid_slaves(row=2)[0].grid_slaves(row=0):
            if isinstance(btn, ctk.CTkButton):
                btn.configure(state=("disabled" if state else "normal"))

    def update_stage(self, text):
        self.lbl_stage.configure(text=text)

    def update_chunks(self, text):
        self.lbl_chunks.configure(text=text)

    def update_servers(self, text):
        self.lbl_srv.configure(text=text)

    # ----------------------------------------------------------------
    def _get_paths(self):
        return self.pipeline.input_pdf, self.pipeline.output_dir

    # ----------------------------------------------------------------
    def run_all(self):
        pdf, odir = self._get_paths()
        if not pdf:
            self.log.write("Укажите входной PDF", "WARNING"); return
        if not odir:
            self.log.write("Укажите выходную папку", "WARNING"); return
        self.pipeline.reset()
        self.update_stage("● Извлечение  →  ○ Перевод  →  ○ Сборка PDF")
        pr = self.settings.entry_page_range.get() if self.settings else ""
        llm = self.settings.cb_use_llm.get() if self.settings else True
        self.runner.run_all(pdf, odir, page_range=pr, use_llm=llm)

    def run_extraction(self):
        pdf, odir = self._get_paths()
        if not pdf:
            self.log.write("Укажите входной PDF", "WARNING"); return
        if not odir:
            self.log.write("Укажите выходную папку", "WARNING"); return
        self.pipeline.reset()
        self.update_stage("● Извлечение  →  ○ Перевод  →  ○ Сборка PDF")
        pr = self.settings.entry_page_range.get() if self.settings else ""
        llm = self.settings.cb_use_llm.get() if self.settings else True
        self.runner.run_extraction(pdf, odir, page_range=pr, use_llm=llm)

    def run_translation(self):
        odir = self.pipeline.output_dir
        self.log.write(f"Перевод: {odir}")
        self.runner.run_translation(odir)

    def run_compile(self):
        self.log.write("Сборка PDF (вручную)")
        self.runner.run_compile("", "")

    def stop_pipeline(self):
        self.runner.stop()
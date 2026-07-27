"""
Загрузка и сохранение конфигурации YAML.

Синхронизирует config/*.yaml с полями SettingsPanel.
Загрузка — через PyYAML (читает любые теги).
Сохранение — через ruamel.yaml (round-trip: сохраняет формат, | блоки, комментарии).
"""
import os
import customtkinter as ctk
import yaml

PROJECT = "/mnt/project"
T_CFG = os.path.join(PROJECT, "config", "translation_config.yaml")
P_CFG = os.path.join(PROJECT, "config", "pandoc_metadata.yaml")


class ConfigLoader:
    def __init__(self):
        self.translation = {}
        self.pandoc = {}
        self.load("all")  # Загружаем конфиг при инициализации

    # ---------------------------------------------------------------
    def load(self, which="all"):
        if which in ("all", "translation"):
            self.translation = self._read(T_CFG)
        if which in ("all", "pandoc"):
            self.pandoc = self._read(P_CFG)

    def save(self, which="all"):
        """Round-trip сохранение через ruamel.yaml — не ломает | блоки."""
        if which in ("all", "translation"):
            self._roundtrip_save(T_CFG, self.translation)
        if which in ("all", "pandoc"):
            self._roundtrip_save(P_CFG, self.pandoc)

    # ---------------------------------------------------------------
    def load_into(self, app):
        """YAML → GUI."""
        self.load("all")
        s = app.settings
        t = self.translation
        p = self.pandoc

        def put(entry, val):
            if entry:
                entry.delete("1.0" if isinstance(entry, ctk.CTkTextbox) else 0, "end")
                entry.insert(
                    "1.0" if isinstance(entry, ctk.CTkTextbox) else 0,
                    val or ""
                )

        put(s.entry_input_pdf,   "")
        put(s.entry_output_dir,  t.get("target_folder", ""))
        put(s.entry_server_pool, "\n".join(t.get("server_pool", [])))
        put(s.entry_api_key,     t.get("api_key", ""))
        put(s.entry_model_name,  t.get("model_name", ""))
        s.cb_use_llm.set(t.get("use_llm", True))
        put(s.entry_fontsize,    p.get("fontsize", "12pt"))
        put(s.entry_mainfont,    p.get("mainfont", "Times New Roman"))
        put(s.entry_monofont,    p.get("monofont", "DejaVu Sans Mono"))

    def collect_from(self, app):
        """GUI → YAML."""
        s = app.settings

        def get(entry):
            if entry is None:
                return ""
            if isinstance(entry, ctk.CTkTextbox):
                return entry.get("1.0", "end").strip()
            return entry.get().strip()

        self.translation["server_pool"] = [
            x.strip() for x in get(s.entry_server_pool).split("\n") if x.strip()
        ]
        self.translation["api_key"]       = get(s.entry_api_key)
        self.translation["model_name"]    = get(s.entry_model_name)
        self.translation["use_llm"]       = s.cb_use_llm.get()
        self.translation["target_folder"] = get(s.entry_output_dir)

        self.pandoc["fontsize"] = get(s.entry_fontsize) or "12pt"
        self.pandoc["mainfont"] = get(s.entry_mainfont) or "Times New Roman"
        self.pandoc["monofont"] = get(s.entry_monofont) or "DejaVu Sans Mono"

    # ---------------------------------------------------------------
    @staticmethod
    def _read(path):
        if not os.path.isfile(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _roundtrip_save(path, new_values):
        """
        Round-trip сохранение через ruamel.yaml.
        Читает файл, обновляет нужные ключи, пишет обратно —
        сохраняет формат, | блоки, комментарии, порядок ключей.
        """
        if not os.path.isfile(path):
            return

        from ruamel.yaml import YAML
        ru = YAML()
        ru.preserve_quotes = True

        # Читаем файл как ruamel-документ (RoundTrip mapping)
        with open(path, "r", encoding="utf-8") as f:
            doc = ru.load(f)

        if not doc:
            return

        # Обновляем ключи
        for key, val in new_values.items():
            doc[key] = val

        # Пишем обратно — ruamel сохраняет формат
        with open(path, "w", encoding="utf-8") as f:
            ru.dump(doc, f)

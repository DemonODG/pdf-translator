"""
Нижняя панель логов с цветной подсветкой уровней:
  INFO      — зелёный
  WARNING   — жёлтый
  ERROR     — красный
  CRITICAL  — красный (яркий)

Реализация: tkinter.Text с tag_config — multi-color без доп. зависимостей.
Thread-safe: write() использует threading.Lock +.after() для UI-обновления.
"""

import threading
import tkinter as tk

import customtkinter as ctk


LEVEL_COLORS = {
    "INFO":     "#00ff88",
    "WARNING":  "#ffdd00",
    "ERROR":    "#ff4444",
    "CRITICAL": "#ff0000",
}


class LogPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._lock = threading.Lock()
        self._auto_scroll = True
        self._buffer = []  # накопитель для thread-safe write

        self._build()
        self._poll_buffer()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Кнопка прокрутки
        btn_bar = ctk.CTkFrame(self, height=26)
        btn_bar.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))
        btn_bar.grid_rowconfigure(0, weight=1)
        btn_bar.grid_columnconfigure(0, weight=1)

        self._scroll_btn = ctk.CTkButton(
            btn_bar, text="⬇ Прокрутить вниз", width=130, height=20, font=ctk.CTkFont(size=10),
            command=self._toggle_scroll,
        )
        self._scroll_btn.grid(row=0, column=0, sticky="e", padx=(10, 10))

        # Text + Scrollbar
        text_frame = ctk.CTkFrame(self)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        self._text = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#2b2b2b",
            fg="#cccccc",
            insertbackground="white",
            state="disabled",
        )
        self._text.grid(row=0, column=0, sticky="nsew")

        sb = tk.Scrollbar(text_frame, command=self._text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._text.configure(yscrollcommand=sb.set)

        # Цветные теги
        for level, color in LEVEL_COLORS.items():
            self._text.tag_configure(level, foreground=color)

        self._text.bind("<Configure>", lambda _: self._auto_scroll_to_end())

    # ------------------------------------------------------------------
    def write(self, message, level="INFO"):
        """Thread-safe: буферизует сообщение, ._poll_buffer вытолкнёт в GUI."""
        with self._lock:
            self._buffer.append((message, level))

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
        with self._lock:
            self._buffer.clear()

    def _toggle_scroll(self):
        self._auto_scroll = not self._auto_scroll
        self._scroll_btn.configure(
            text="⏸ Автопрокрутка" if not self._auto_scroll else "⬇ Прокрутить вниз"
        )

    def _auto_scroll_to_end(self):
        if self._auto_scroll:
            self._text.see("end")

    # ------------------------------------------------------------------
    def _poll_buffer(self):
        """Каждые 200 ms сливает буфер в Text-виджет из main thread."""
        lines = []
        with self._lock:
            lines.extend(self._buffer)
            self._buffer.clear()

        if lines:
            self._text.configure(state="normal")
            for message, level in lines:
                tag = level if level in LEVEL_COLORS else "INFO"
                self._text.insert("end", message + "\n", tag)
            self._text.configure(state="disabled")
            if self._auto_scroll:
                self._text.see("end")

        self._text.after(200, self._poll_buffer)

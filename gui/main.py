"""
Точка входа GUI приложения PDF Translator.

Создаёт главное окно и запускает event-loop CustomTkinter.
"""

from gui.app_window import AppWindow


def main():
    """Запуск GUI приложения."""
    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()

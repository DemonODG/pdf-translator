import logging
import re


# Подключаемся к единому логгеру пайплайна
logger = logging.getLogger("translator")


def clean_and_prepare_english_text(content):
    """
    Вызывается ДО перевода. Вырезает бегущие колонтитулы главы,
    очищает технические br-теги и трансформирует маркеры страниц в \newpage.
    """
    logger.info("-> Запускаю предобработку и чистку английского текста...")

    # 1. Трансформация маркеров страниц {66}------ в \newpage для XeLaTeX
    content = re.sub(
        r'\{(\d+)\}-+\s*\n',
        r'\n\n\\newpage\n\\centerline{\\footnotesize\\color{gray}--- Страница \1 ---}\n\n',
        content
    )

    # 2. Удаление бегущих английских колонтитулов (Chapter X...)
    content = re.sub(r'#{2,4}\s*(?:<span id="page-\d+-\d+"></span>)?\s*(?:\*\*|)?Chapter\s+\d+.*?\n',
                     '\n', content, flags=re.IGNORECASE)
    content = re.sub(
        r'(?:\n|^)Chapter\s+\d+\s+[^#\n]{1,60}\n', '\n', content, flags=re.IGNORECASE)

    # 3. Чистка тегов <br> и лишних пробелов из таблиц
    content = re.sub(r'(?i)<br\s*/?>', ' ', content)
    content = re.sub(r' +', ' ', content)

    return content


def fix_russian_footnotes(final_text):
    """
    Вызывается ПОСЛЕ перевода и снятия всех заглушек.
    Универсальный, 100% безопасный фикс сносок. Поддерживает и формат <sup>,
    и формат внутренних якорей (#page-3-1) из книги про эмбеддинги.
    """
    logger.info("-> Финальная очистка и верстка сносок на русском языке...")

    # 1. Находим в готовом русском тексте маркеры <sup>1</sup> и превращаем их в [^1]
    final_text = re.sub(r'<sup>(\d+)</sup>', r'[^\1]', final_text)

    # Исправляем маркеры в тексте: (#page-3-1) -> [^1]
    # Паттерн ищет [цифра](любой текст с #page)
    final_text = re.sub(
        r'\[(\d+)\]\((?:#page-[^\)]+|[^\)]+#page-[^\)]+)\)', r'[^\1]', final_text)

    # --- УНИВЕРСАЛЬНЫЙ СБОРЩИК ОПРЕДЕЛЕНИЙ СНОСОК ---
    # 2. Находим строки определений сносок в подвалах (которые модель перевела как <sup>1</sup> или [^1])
    # и превращаем их в идеальный стандарт Pandoc, ПРИНУДИТЕЛЬНО изолируя пустыми строками \n\n
    def clean_universal_footnote_def(m):
        num = m.group(1)      # Номер сноски
        raw_tail = m.group(2)  # Весь текст сноски целиком

        # Сохраняем весь переведенный текст, убирая только висячие пробелы
        clean_text = raw_tail.strip()

        # Возвращаем идеальную разметку Pandoc, жестко изолированную пустыми строками \n\n
        return f"\n\n[^{num}]: {clean_text}\n\n"

    # Регулярка гибко отсекает префиксы span, sup или квадратные скобки в начале строки подвала
    footnote_def_pattern = r'(?:\n|^)(?:<span[^>]+></span>)?\s*(?:<sup>|\[\^)?(\d+)(?:</sup>|\])?(?::)?\s*(.*)'
    final_text = re.sub(footnote_def_pattern,
                        clean_universal_footnote_def, final_text)

    # Итоговое сглаживание случайных тройных переносов строк
    final_text = re.sub(r'\n{3,}', '\n\n', final_text)

    return final_text

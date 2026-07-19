import argparse
import itertools
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
# Определяем путь к папке scripts, где лежит translate_marker.py
scripts_dir = Path(__file__).resolve().parent

# Добавляем её в sys.path, чтобы Python знал, где искать пакет utils
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))
import autopep8
import requests
from tqdm import tqdm
import yaml
import logging
from utils.network import ThreadSafeCycle, check_active_servers, load_translation_config
from utils.compiler import assemble_markdown_with_config, compile_md_to_pdf
from utils.segmentation import smart_split_markdown, apply_placeholders, restore_placeholders
from utils.text_processor import clean_and_prepare_english_text, fix_russian_footnotes


# Настройка сквозного логирования для всего пайплайна
log_format = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# Лог в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)

# Лог в файл истории
file_handler = logging.FileHandler("/mnt/project/pipeline.log", encoding="utf-8")
file_handler.setFormatter(log_format)

logger = logging.getLogger("translator")
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


# === 1. ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (ДЛЯ ПОТОКОВ) ===
# Объявляем их на уровне модуля, чтобы функции внутри параллельных потоков имели к ним прямой доступ
ACTIVE_SERVERS = []
server_balancer = None

# Параметры LLM, которые будут динамически заполнены из YAML при старте
API_KEY = ""
MODEL_NAME = ""
SYSTEM_PROMPT = ""

# === 2. БЛОК ОПРЕДЕЛЕНИЯ КЛАССОВ И ФУНКЦИЙ ===

def parse_arguments(default_target_folder):
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Пайплайн автоматического перевода технических книг."
    )

    # Добавляем опцию -d / --dir, по умолчанию подставляем путь из YAML
    parser.add_argument(
        "-d",
        "--dir",
        type=str,
        default=default_target_folder,
        help="Путь к целевой папке с книгой (переопределяет значение из конфигурационного файла)",
    )

    return parser.parse_args()


def translate_chunk_parallel(item):
    """Принимает кортеж (индекс, кусок_текста), переводит его и возвращает

    (индекс, переведенный_текст) для сохранения порядка.
    """
    index, text_chunk = item
    if not text_chunk.strip():
        return index, text_chunk

    # Балансировщик выдаст первому потоку адрес ПК, а второму — адрес ноутбука
    url = next(server_balancer)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text_chunk},
        ],
        "top_p": 0.95,
        "max_tokens": 4096,
        "repeat_penalty": 1.0,
        "temperature": 0.1,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=120
        )
        response.raise_for_status()
        result_json = response.json()
        translated_text = result_json["choices"][0]["message"]["content"].strip()
        return index, translated_text
    except Exception as e:
        print(
            f"\n[Ошибка на сервере {url} | Блок #{index}]: {e}",
            file=sys.stderr,
        )
        return index, text_chunk


def process_and_translate(content):
    """
    Полностью разгруженная функция параллельного перевода книги.
    Вся грязная работа со строками и регулярками ушла во внешние модули.
    """
    # 1. Предобработка английского текста (чистка колонтитулов, пагинация)
    content = clean_and_prepare_english_text(content)

    # Шаг 1: Изолируем элементы от LLM и сглаживаем \n{3,} (всё внутри модуля)
    content, placeholders = apply_placeholders(content)

    # Шаг 2: Разбиваем текст на безопасные по размеру куски через внешний модуль
    chunks = smart_split_markdown(content, max_chars=6000)

    # Нумеруем чанки, чтобы после параллельной обработки собрать их строго по порядку
    indexed_chunks = list(enumerate(chunks))

    # Количество воркеров подстраивается автоматически на основе активных серверов
    MAX_WORKERS = len(ACTIVE_SERVERS)

    # ЗАПИСЫВАЕМ СТАТУС КЛАСТЕРА В СТАНДАРТНЫЙ ЛОГ
    logger.info(f"-> Начинаю параллельный перевод (Воркеров: {MAX_WORKERS}, Активных серверов: {len(ACTIVE_SERVERS)})...")
    logger.info(f"-> Всего блоков для перевода: {len(chunks)}")

    # Запускаем пул потоков
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(
            tqdm(
                executor.map(translate_chunk_parallel, indexed_chunks),
                total=len(chunks),
                desc="Параллельный перевод книги",
            )
        )

    # Сортируем результаты по индексу, чтобы восстановить исходный порядок текста книги
    results.sort(key=lambda x: x[0])
    translated_chunks = [text for index, text in results]

    final_text = "\n\n".join(translated_chunks)

    # Шаг 3: Возвращаем оригинальный код и формулы на свои места (всё внутри модуля utils/segmentation)
    final_text = restore_placeholders(final_text, placeholders)

    # 6. Финальная издательская верстка сносок под Pandoc Markdown
    final_text = fix_russian_footnotes(final_text)

    return final_text


def translate_markdown_file(folder_path, config, config_pandoc_path):
    """Основная функция управления процессом."""
    path = Path(folder_path)
    if not path.exists():
        print(f"[Ошибка]: Папка '{folder_path}' не найдена.")
        return

    md_files = [f for f in path.glob("*.md") if not f.stem.endswith("_ru")]

    if not md_files:
        print(f"[Ошибка]: В папке '{folder_path}' нет файлов .md.")
        return

    print(f"📚 Найдено файлов для перевода: {len(md_files)}")

    for input_md_file in md_files:

        print(
            f"\n{'='*40}\n📖 ОБРАБОТКА ФАЙЛА: {input_md_file.name}\n{'='*40}"
        )

        output_md_file = input_md_file.with_name(f"{input_md_file.stem}_ru.md")
        output_pdf_file = input_md_file.with_name(
            f"{input_md_file.stem}_ru.pdf"
        )

        with open(input_md_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Перевод англоязычного md
        translated_content = process_and_translate(content)

        # 3. Добавляем блок настроек pandoc в md-файл из yaml-config
        assemble_markdown_with_config(
            translated_content, config_pandoc_path, output_md_file
        )
        print(f"✅ Переведенный Markdown сохранен: {output_md_file.name}")

#        # 4: Сборка финального PDF через Pandoc (XeLaTeX)



# === 3. ТОЧКА ВХОДА ---
if __name__ == "__main__":
    CONFIG_PATH_TRANSLATION = "/mnt/project/config/translation_config.yaml"
    # Путь к конфигурационному файлу для сборки Pandoc
    CONFIG_FILE_PANDOC = "/mnt/project/config/pandoc_metadata.yaml"

    try:
        # Шаг 1: Загружаем базовый конфиг из YAML
        base_config = load_translation_config(CONFIG_PATH_TRANSLATION)

        # Шаг 2: Парсим аргументы командной строки (-d)
        args = parse_arguments(base_config.get("target_folder"))
        target_folder = args.dir

        # Шаг 3: Инициализируем глобальные переменные для параллельных потоков воркера
        API_KEY = base_config["api_key"]
        MODEL_NAME = base_config["model_name"]
        SYSTEM_PROMPT = base_config["system_prompt"]

        # Шаг 4: Динамически определяем список РАБОЧИХ серверов
        ACTIVE_SERVERS = check_active_servers(base_config["server_pool"])

        # Шаг 5: Инициализируем ПОТОКОБЕЗОПАСНЫЙ балансировщик
        server_balancer = ThreadSafeCycle(ACTIVE_SERVERS)

        print(
            "[SUCCESS] Конфигурация и потокобезопасный балансировщик успешно запущены."
        )

        # Шаг 6: Запускаем основной процесс перевода
        translate_markdown_file(target_folder, base_config, CONFIG_FILE_PANDOC)

    except Exception as e:
        print(f"[CRITICAL ERROR] Скрипт аварийно завершился: {e}")
        sys.exit(1)


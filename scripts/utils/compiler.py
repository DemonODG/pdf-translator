import logging
import subprocess
import sys
from pathlib import Path

# Подключаемся к единому логгеру пайплайна
logger = logging.getLogger("translator")

def assemble_markdown_with_config(translated_text, config_path, output_file_path):
    """
    Чисто текстовая склейка YAML-конфига и тела книги.
    Сохраняет вертикальные черты '|' в первозданном виде без искажений PyYAML.
    """
    try:
        # Читаем конфиг как сырой текст, сохраняя структуру на 100%
        with open(config_path, "r", encoding="utf-8") as config_file:
            raw_yaml_content = config_file.read()

        # Очищаем текст от возможных лишних маркеров '---', если они есть в файле
        clean_yaml = raw_yaml_content.strip().strip("---").strip()

        # Собираем итоговый текст Markdown
        final_md_content = f"---\n{clean_yaml}\n---\n\n{translated_text}"

        # Записываем готовый файл на диск
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(final_md_content)
            
        logger.info(f"✅ [SUCCESS] Документ успешно собран с конфигом '{config_path}'")
        return True
    except FileNotFoundError:
        logger.error(f"[ERROR] Конфигурационный файл не найден по пути: {config_path}")
        return False
    except Exception as e:
        logger.error(f"[ERROR] Непредвиденная ошибка при сборке: {e}")
        return False


def compile_md_to_pdf(output_md_file, output_pdf_file, path):
    """
    Автономная функция для сборки финального PDF через Pandoc (XeLaTeX).
    Вырезана из основного процесса для обеспечения модульности пайплайна.
    """
    output_md_path = Path(output_md_file)
    output_pdf_path = Path(output_pdf_file)
    work_dir = Path(path)

    logger.info("-> Запускаю сборку финального PDF книги...")
    pandoc_command = [
        "pandoc",
        str(output_md_path),
        "-o",
        str(output_pdf_path),
        "--pdf-engine=xelatex",
        "--highlight-style=pygments",  # Оригинальный стиль подсветки синтаксиса
        f"--resource-path={work_dir}",
    ]

    try:
        # Запускаем сборку из целевой папки, чтобы подтянулись PNG-картинки
        subprocess.run(pandoc_command, cwd=str(work_dir), check=True)
        logger.info(f"🎉 Книга полностью готова! PDF собран: {output_pdf_path.name}")
        return True
    except FileNotFoundError:
        logger.error("[Внимание]: Pandoc или XeLaTeX не найдены в системе. PDF не собран.")
        logger.error("Сам перевод сохранен в формате Markdown (.md) в той же папке.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"[Ошибка Pandoc]: Ошибка компиляции PDF. Код: {e.returncode}")
        return False

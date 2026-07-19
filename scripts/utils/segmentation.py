import logging
import re
import autopep8


# Подключаемся к единому логгеру пайплайна
logger = logging.getLogger("translator")

def smart_split_markdown(md_text, max_chars=6000):
    """
    Бережно режет Markdown-текст книги на порции до max_chars символов.
    Если один блок превышает лимит, он аккуратно пилится по одиночным \n (для таблиц)
    или по точкам/предложениям (для сплошного текста).
    """
    blocks = md_text.strip().split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0

    for block in blocks:
        if not block.strip():
            continue
            
        # Если ОДИН абзац/таблица больше лимита, бережно пилим его внутри
        if len(block) > max_chars:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # ОПРЕДЕЛЯЕМ ТИП КРУПНОГО БЛОКА:
            # Если внутри много одиночных переносов строк, значит это таблица/оглавление/список
            if block.count("\n") > 3:
                sub_elements = block.split("\n")
                join_char = "\n"
            else:
                # Если это просто аномально длинный сплошной текст — режем по предложениям
                sub_elements = re.split(r'(?<=[.!?])\s+', block)
                join_char = " "
                
            sub_chunk = []
            sub_len = 0
            for item in sub_elements:
                if not item.strip():
                    continue
                if len(item) > max_chars:
                    if sub_chunk:
                        chunks.append(join_char.join(sub_chunk))
                        sub_chunk = []
                        sub_len = 0
                    chunks.append(item)
                    continue
                
                if sub_len + len(item) > max_chars:
                    if sub_chunk:
                        chunks.append(join_char.join(sub_chunk))
                    sub_chunk = [item]
                    sub_len = len(item)
                else:
                    sub_chunk.append(item)
                    sub_len += len(item) + len(join_char)
            
            # Сохраняем хвостик подблока, если он остался
            if sub_chunk:
                chunks.append(join_char.join(sub_chunk))
            continue

        # Стандартная сборка чанков из обычных абзацев
        if current_length + len(block) > max_chars:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [block]
            current_length = len(block)
        else:
            current_chunk.append(block)
            current_length += len(block) + 2

    # Сохраняем финальный хвостик всей книги
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks


def apply_placeholders(content):
    """
    Находит в тексте блоки кода и математические формулы и временно
    заменяет их на уникальные текстовые заглушки, полностью изолируя от LLM.
    """
    placeholders = {}
    counter = 0

    # Паттерны для поиска элементов, которые нельзя переводить
    patterns = {
        "CODE_BLOCK": r"(```[\s\S]*?```)",           # Многострочный код
        "MATH_DISPLAY": r"(\$\$[\s\S]*?\$\$(?:\n)?)", # Формулы на отдельной строке
        "MATH_INLINE": r"(\$[^\$\n]+?\$)",           # Формулы внутри строки
        "INLINE_CODE": r"(`[^`\n]+?`)",              # Инлайн код
    }

    for key, pattern in patterns.items():
        matches = re.findall(pattern, content)
        for match in matches:
            placeholder = f"__{key}_{counter}__"
            placeholders[placeholder] = match
            content = content.replace(match, placeholder, 1)
            counter += 1

    # === НАШЕ СГЛАЖИВАНИЕ ДВОЙНЫХ ПЕРЕНОСОВ СТРОК ===
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content, placeholders


def fix_broken_indentation(code_text):
    """
    Автоматически восстанавливает базовые отступы для def и docstrings.
    Оригинальный проверенный алгоритм.
    """
    lines = code_text.splitlines()
    inside_function = False
    inside_docstring = False
    processed_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            processed_lines.append(line)
            continue
        if stripped.startswith("def ") or stripped.startswith("class "):
            inside_function = True
            inside_docstring = False
            processed_lines.append(stripped)
            continue
        if inside_function and (
            stripped.startswith('"""') or stripped.startswith("'''")
        ):
            if stripped.count('"""') % 2 != 0 or stripped.count("'''") % 2 != 0:
                inside_docstring = not inside_docstring
            processed_lines.append("    " + stripped)
            continue
        if inside_docstring:
            processed_lines.append("    " + stripped)
            continue
        if inside_function and not line.startswith("    "):
            processed_lines.append("    " + stripped)
            if stripped.startswith("return "):
                inside_function = False
            continue
        processed_lines.append(line)
    return "\n".join(processed_lines)


def restore_placeholders(translated_content, placeholders):
    """
    Возвращает оригинальные блоки кода и формулы на свои места по словарю заглушек.
    Производит хирургическую очистку кода от артефактов Marker (,→) и полирует по PEP 8.
    """
    logger.info("-> Восстановление защищенного кода и формул...")
    
    for placeholder, original_content in reversed(list(placeholders.items())):
        # Если это многострочный блок кода, чиним в нем отступы и убираем мусор Marker
        if "__CODE_BLOCK_" in placeholder:
            try:
                lines = original_content.split("\n")
                fence_start = lines[0].strip()  # например, ```
                fence_end = lines[-1].strip()    # ```
                pure_code_lines = lines[1:-1]

                # 1. Принудительно добавляем python к "голым" кавычкам
                if fence_start == "```":
                    fence_start = "```python"

                is_python = "python" in fence_start.lower()

                # 2. Очищаем строки от артефактов нумерации Marker
                cleaned_lines = []
                for line in pure_code_lines:
                    # Удаляем артефакты переноса строк (,→ и , →)
                    line = re.sub(r"^\s*,\s*→\s*", "", line)
                    line = re.sub(r"^\s*,→\s*", "", line)

                    # Если в строке только число — полностью её игнорируем
                    if re.match(r"^\s*\d+\s*$", line):
                        continue

                    # Если строка начинается с номера (например, "11 # Print") — убираем цифру
                    clean_line = re.sub(r"^\s*\d+[\s\.\|\:]\s*", "", line)
                    cleaned_lines.append(clean_line)

                repaired_pure_code = "\n".join(cleaned_lines)

                # 3. Восстанавливаем отступы через ТВОЮ родную функцию и полируем через autopep8
                if is_python and repaired_pure_code.strip():
                    repaired_pure_code = fix_broken_indentation(repaired_pure_code)
                    repaired_pure_code = autopep8.fix_code(
                        repaired_pure_code, options={"max_line_length": 85}
                    )
                    
                # Собираем красивый блок обратно в Markdown-формат
                repaired_block = f"{fence_start}\n{repaired_pure_code.rstrip()}\n{fence_end}"
                translated_content = translated_content.replace(placeholder, repaired_block)
            except Exception as e:
                logger.error(f"[ВНИМАНИЕ] Ошибка при восстановлении блока кода {placeholder}: {e}")
                translated_content = translated_content.replace(placeholder, original_content)
        else:
            # Для формул и инлайн-кода оставляем всё в оригинальном виде
            translated_content = translated_content.replace(placeholder, original_content)

    return translated_content

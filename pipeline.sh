# Проверка количества аргументов
if [ "$#" -ne 3 ]; then
    echo "Использование: $0 <path_to_input_pdf> <output_path> [page_range]"
    echo "Пример: $0 /mnt/project/raw_data/book.pdf /mnt/project/rendered/book/ 0-20"
    exit 1
fi

INPUT_PDF=$1
USER_OUTPUT_PATH=$2
PAGE_RANGE=$3

# Проверка существования входного файла
if [ ! -f "$INPUT_PDF" ]; then
    echo "Ошибка: Входной файл $INPUT_PDF не найден."
    exit 1
fi

# Извлекаем имя книги из пути (например, /path/to/book.pdf -> book)
BOOK_NAME=$(basename "$INPUT_PDF" .pdf)

# Логика определения базовой директории для marker_single:
# Если пользователь передает путь, содержащий имя книги (например, /mnt/project/rendered/book/),
# мы берем родительскую директорию (/mnt/project/rendered/), чтобы marker_single 
# создал внутри неё папку с именем книги.
# В противном случае используем указанный путь как базовый.

if [[ "$USER_OUTPUT_PATH" == *"$BOOK_NAME"* ]]; then
    BASE_DIR=$(dirname "$USER_OUTPUT_PATH")
else
    BASE_DIR="$USER_OUTPUT_PATH"
fi

# Очистка BASE_DIR от лишних слешей в конце, если они есть (например, /path/to/dir/ -> /path/to/dir)
BASE_DIR="${BASE_DIR%/}"

# Рабочая директория, где будут храниться все результаты для этой книги
# Теперь корректно формируется даже если BASE_DIR уже содержит путь к папке книги
if [[ "$BASE_DIR" == *"$BOOK_NAME"* ]]; then
    WORKING_DIR="$BASE_DIR"
else
    WORKING_DIR="$BASE_DIR/$BOOK_NAME"
fi

echo "=== Начало конвейера перевода для книги: $BOOK_NAME ==="
echo "Входной файл: $INPUT_PDF"
echo "Рабочая директория: $WORKING_DIR"
echo "Базовая директория для marker_single: $BASE_DIR"
echo "Параметр страницы (page_range): ${PAGE_RANGE:-none}"

# Создаем рабочую директорию
mkdir -p "$WORKING_DIR"

# --- ШАГ 1: ИЗВЛЕЧЕНИЕ (Extraction) ---
echo "--- Шаг 1: Извлечение контента через marker-pdf ---"
# Важно передать именно BASE_DIR в качестве output_dir, чтобы marker_single создал папку $BOOK_NAME
XDG_CACHE_HOME="/mnt/project/models" \
MARKER_STRIP_LINE_BREAKS="0" \
marker_single "$INPUT_PDF" \
--timeout 3600 \
--output_dir "$BASE_DIR" \
--drop_repeated_text \
--output_format markdown \
--use_llm \
--llm_service marker.services.openai.OpenAIService \
--OpenAIService_openai_image_format jpeg \
--openai_api_key "local" \
--openai_base_url "http://127.0.0.1:8081/v1" \
--openai_model "local-model" \
${PAGE_RANGE:+--page_range "$PAGE_RANGE"}

if [ $? -ne 0 ]; then
    echo "Ошибка на этапе извлечения контента."
    exit 1
fi

# --- ШАГ 2: ПЕРЕВОД (Translation) ---
echo "--- Шаг 2: Перевод чанков через translate_marker.py ---"
# Скрипт translate_marker.py ожидает директорию с извлеченным контентом
python3 scripts/translate_marker.py --dir "$WORKING_DIR"

if [ $? -ne 0 ]; then
    echo "Ошибка на этапе перевода."
    exit 1
fi

# --- ШАГ 3: СБОРКА И РЕНДЕРИНГ (Assembly & Rendering) ---
echo "--- Шаг 3: Сборка и генерация PDF через Pandoc ---"

# Ищем файл с переведенным текстом.
# Ищем файл, содержащий "_ru.md" в рабочей директории
RESULT_MD=$(ls "$WORKING_DIR"/*_ru.md 2>/dev/null | head -n 1)

# Если не нашли с суффиксом _ru.md, берем стандартный final_translation.md
if [ -z "$RESULT_MD" ]; then
    RESULT_MD="$WORKING_DIR/final_translation.md"
fi

if [ ! -f "$RESULT_MD" ]; then
    echo "Ошибка: Не удалось найти финальный Markdown файл в $WORKING_DIR"
    exit 1
fi

echo "Рендеринг файла: $RESULT_MD"
pandoc "$RESULT_MD" \
-o "$WORKING_DIR/${BOOK_NAME}_ru.pdf" \
--pdf-engine=xelatex \
--highlight-style=pygments \
--resource-path="$WORKING_DIR"

if [ $? -eq 0 ]; then
    echo "=== Успешно завершен конвейер! Файл готов: $WORKING_DIR/${BOOK_NAME}_ru.pdf ==="
else
    echo "Ошибка на этапе рендеринга PDF."
    exit 1
fi

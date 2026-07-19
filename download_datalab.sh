#!/bin/bash

# Базовый URL хранилища моделей Datalab, который вы нашли
BASE_URL="https://models.datalab.to"
# Целевая папка для моделей
TARGET_DIR="/mnt/project/models/datalab/models"

# Юзер-агент обычного браузера, чтобы сервер не блокировал и не вешал закачку
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Функция для безопасного скачивания файлов (конфиги и тяжелые веса моделей)
download_file() {
    local model_path=$1
    local file_name=$2
    local target_dir="$TARGET_DIR/$model_path"
    
    mkdir -p "$target_dir"
    
    if [ ! -f "$target_dir/$file_name" ]; then
        echo "Скачиваем $model_path/$file_name..."
        # Используем wget с поддержкой докачки (-c), повторов (-t) и имитацией браузера
        wget --user-agent="$UA" -c -t 5 -O "$target_dir/$file_name" "$BASE_URL/$model_path/$file_name"
    else
        echo "Файл $file_name уже существует, пропускаем."
    fi
}

echo "=== Начало загрузки моделей Datalab ==="

# 1. Модель Разметки (Layout)
download_file "layout/2025_09_23" "config.json"
download_file "layout/2025_09_23" "model.safetensors"
download_file "layout/2025_09_23" "preprocessor_config.json"
download_file "layout/2025_09_23" "processor_config.json"
download_file "layout/2025_09_23" "special_tokens_map.json"
download_file "layout/2025_09_23" "specials.json"
download_file "layout/2025_09_23" "specials_dict.json"
download_file "layout/2025_09_23" "tokenizer_config.json"
download_file "layout/2025_09_23" "training_args.bin"
download_file "layout/2025_09_23" "vocab_math.json"

# 2. Модель детекции ошибок OCR
download_file "ocr_error_detection/2025_02_18" "config.json"
download_file "ocr_error_detection/2025_02_18" "model.safetensors"
download_file "ocr_error_detection/2025_02_18" "tokenizer.json"
download_file "ocr_error_detection/2025_02_18" "tokenizer_config.json"
download_file "ocr_error_detection/2025_02_18" "vocab.txt"

# 3. Модель распознавания таблиц
download_file "table_recognition/2025_02_18" "config.json"
download_file "table_recognition/2025_02_18" "model.safetensors"
download_file "table_recognition/2025_02_18" "preprocessor_config.json"

# 4. Детектор текста (Text Detection)
download_file "text_detection/2025_05_07" "config.json"
download_file "text_detection/2025_05_07" "model.safetensors"
download_file "text_detection/2025_05_07" "preprocessor_config.json"
download_file "text_detection/2025_05_07" "training_args.bin"

# 5. Распознавание текста (Text Recognition / OCR)
download_file "text_recognition/2025_09_23" "config.json"
download_file "text_recognition/2025_09_23" "model.safetensors"
download_file "text_recognition/2025_09_23" "preprocessor_config.json"
download_file "text_recognition/2025_09_23" "processor_config.json"
download_file "text_recognition/2025_09_23" "special_tokens_map.json"
download_file "text_recognition/2025_09_23" "specials.json"
download_file "text_recognition/2025_09_23" "specials_dict.json"
download_file "text_recognition/2025_09_23" "tokenizer_config.json"
download_file "text_recognition/2025_09_23" "training_args.bin"
download_file "text_recognition/2025_09_23" "vocab_math.json"

echo "=== Все модели Datalab успешно загружены и разложены по папкам в $TARGET_DIR ==="

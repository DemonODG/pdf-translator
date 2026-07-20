# English-to-Russian PDF Translation Pipeline

Конвейер для автоматизированного перевода англоязычной технической литературы (включая книги по программированию) на русский язык с сохранением исходной структуры, формул и блоков кода.

## 🚀 Основные функции
- **Точное извлечение текста**: Конвертация PDF в Markdown с помощью `marker-pdf` и LLM-коррекция разметки.
- **Параллельный перевод**: Разделение текста на чанки и многопоточная обработка на кластере серверов.
- **Глубокая очистка текста**: Изоляция кода и формул через плейсхолдеры, удаление мусора и нормализация сносок.
- **Автоматическая сборка**: Объединение переведенных частей в единый Markdown-файл с внедрением метаданных верстки.
- **Профессиональный рендеринг**: Прямая конвертация Markdown в PDF через Pandoc (движок XeLaTeX) с сохранением типографики.

## 💡 Офлайн-режим для OCR

- Ранее `marker_single` пре первом запуске пыталась скачать гигабайты весов моделей из интернета в процессе работы, что вызывало долгие задержки. 
  download_datalab.sh скачивает все необходимые OCR-модели (Datalab) в локальный каталог проекта `models/datalab/`, обеспечивая работу `marker_single` без задержек при первом запуске.

## 🛠 Основные архитектурные решения

### 1. Распределенная обработка (Cluster-Ready)
- **Балансировка нагрузки**: Механизмы `check_active_servers` и `ThreadSafeCycle` позволяют распределять запросы между несколькими серверами (например, локальный ПК + удаленный сервер) в реальном времени.
- **Многопоточность**: Использование `ThreadPoolExecutor` для параллельного выполнения запросов к API перевода.

### 2. Интеллектуальная подготовка контента (Preprocessing)
- **Очистка текста**: Функция `clean_and_prepare_english_text` удаляет технический мусор, пагинацию и колонтитулы перед отправкой в LLM.
- **Изоляция элементов**: Функции `apply_placeholders` и `restore_placeholders` защищают блоки кода и формулы. Они заменяются временными метками, что предотвращает их искажение или перевод моделью.
- **Умное разбиение**: Функция `smart_split_markdown` делит текст на чанки объемом до 6000 символов, строго учитывая границы заголовков и не разрывая логические блоки.

### 3. Качественная сборка и верстка (Post-processing)
- **Коррекция сносок**: Функция `fix_russian_footnotes` адаптирует формат русских сносок для корректной обработки компилятором.
- **Управление метаданными**: Функция `assemble_markdown_with_config` внедряет YAML-конфигурацию (автор, название, шрифты, стили) прямо в итоговый Markdown-файл.
- **Компиляция**: Функция `compile_md_to_pdf` автоматически собирает финальный PDF-документ с помощью Pandoc и движка `xelatex`.

---

## 🛠 Установка и развертывание

Для развертывания конвейера выполните следующие шаги:

### 1. Установка системных зависимостей
Для работы парсеров, OCR и компиляции финального PDF требуются системные утилиты. Установите их через менеджер пакетов:
```bash
sudo apt-get update && sudo apt-get install -y \
  pandoc \
  texlive-xetex \
  texlive-fonts-recommended \
  texlive-plain-generic \
  tesseract-ocr \
  poppler-utils
```

### 2. Установка Python-зависимостей
Создайте изолированное виртуальное окружение и установите необходимые библиотеки:
```bash
python3 -m venv hermes_env
source hermes_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Настройки подключения к модели перевода
Настройки подключения к API модели перевода (endpoint) централизованно управляются в файле конфигурации:
`config/translation_config.yaml`

Основные параметры для настройки:
- **server_pool**: Список адресов серверов для распределенного параллельного перевода чанков текста.
- **API_KEY**: Ваш секретный ключ для доступа к API.
- **model_name**: Идентификатор модели, используемой для перевода.
- **SYSTEM_PROMPT**: Инструкции для модели, определяющие стиль и качество перевода.
- **target_folder**: Отвечает за директорию по умолчанию для перевода скрипта translate_marker.py, если не задан параметр командной строки.

### 4. Предварительная загрузка OCR-моделей (Обязательно)
Чтобы конвейер не зависал при первом запуске, скачайте все 5 моделей Datalab в локальный кэш с помощью скрипта:
```bash
bash /mnt/project/download_datalab.sh
```
*Убедитесь, что скрипт сохраняет модели в директорию `/mnt/project/models/datalab/`.*

*Если загрузка ocr моделей продолжает зависать, проверьте настройки дополнительных dns в системе. Помогает `автоматические настройки`*

### 5. Извлечение текста из PDF (Extraction)
Запустите `marker-pdf` с обязательным указанием пути к локальному кэшу моделей через `XDG_CACHE_HOME`:
```bash
XDG_CACHE_HOME="/mnt/project/models" \
MARKER_STRIP_LINE_BREAKS="0" \
marker_single /mnt/project/raw_data/embeddings.pdf \
  --timeout 3600 \
  --output_dir /mnt/project/rendered/ \
  --drop_repeated_text \
  --output_format markdown \
  --use_llm \
  --llm_service marker.services.openai.OpenAIService \
  --OpenAIService_openai_image_format jpeg \
  --openai_api_key "local" \
  --openai_base_url "http://127.0.0.1:8081/v1" \
  --openai_model "local-model"
```

---

## 📂 Структура проекта

```text

├── models/                     # Локальное хранилище весов OCR-моделей (Datalab)
│   └── datalab/                # Подпапки моделей (layout, text_recognition и др.)
├── raw_data/                   # Исходные данные (оригинальные PDF-файлы)
│   └── [book_name].pdf        
├── rendered/                   # Результаты извлечения и финальной сборки
│   └── [book_name]/            # Индивидуальная папка для каждой книги
│       ├── [book_name].md      # Исходный MD-файл, извлеченный из PDF через marker
│       ├── [book_name]_ru.md   # Финальный склеенный перевод всей книги (Markdown)
│       └── [book_name]_ru.pdf  # Итоговый скомпилированный PDF-файл на русском языке
├── scripts/                    # Скрипты автоматизации конвейера
│   ├── translate_marker.py    # Основной оркестратор пайплайна (перевод и сборка)
│   ├── utils/                  # Модульные утилиты
│   │   ├── segmentation.py     # Разрезание текста на чанки и работа с плейсхолдерами
│   │   ├── text_processor.py   # Очистка текста, форматирование кода и обработка сносок
│   │   ├── compiler.py         # Сборка структуры и финальная верстка через Pandoc
│   │   └── network.py          # Работа с кластером серверов и балансировщик нагрузки
│   ├── backup/                 # Резервные копии критически важных скриптов
│   └── old/                    # Архив устаревших версий кода
├── config/                     # Конфигурационные файлы проекта
│   ├── translation_config.yaml  # Параметры LLM, адреса серверов и системный промпт
│   ├── pandoc_metadata.yaml     # Параметры верстки для Pandoc (шрифты, поля LaTeX)
│   └── marker_correction_prompt.txt # Промпт для исправления ошибок извлечения PDF
├── qwen3.6-from-translate.txt  # Рекомендации по запуску LLM для эндпоинта перевода
├── qwen3.6-from_marker.txt     # Рекомендации по запуску LLM для эндпоинта разметки
├── pipeline.log                # Файл системного логирования процессов
├── pipeline.sh                 # Единый скрипт запуска конвейера (Pipeline)
├── download_datalab.sh         # Скрипт предварительной загрузки моделей OCR
├── conv_pdf.md                 # Документация текущего плана действий (Workflow)
├── requirements.txt            # Список всех Python-зависимостей проекта
└── README.md                   # Общее описание проекта и инструкции по развертыванию
```

---

## 📖 Основные шаги перевода (Workflow)

Для перевода англоязычного PDF-файла на русский язык следуйте согласованному плану из 3 пунктов:

### 1. Извлечение (Extraction)
Преобразование PDF в Markdown с использованием локального набора OCR-моделей от `datalab-to` (`marker-pdf`) и локального LLM-совместимого OpenAI эндпоинта для высокоточной коррекции ошибок распознавания структуры и текста «на лету».
```bash
XDG_CACHE_HOME="/mnt/project/models" \
MARKER_STRIP_LINE_BREAKS="0" \
marker_single /mnt/project/raw_data/embeddings.pdf \
  --timeout 3600 \
  --output_dir /mnt/project/rendered/ \
  --drop_repeated_text \
  --output_format markdown \
  --use_llm \
  --llm_service marker.services.openai.OpenAIService \
  --OpenAIService_openai_image_format jpeg \
  --openai_api_key "local" \
  --openai_base_url "http://127.0.0.1:8081/v1" \
  --openai_model "local-model"
```

### 2. Перевод (Translation)
Интеллектуальное разбиение текста на чанки и их параллельный перевод через локальный OpenAI-совместимый LLM-endpoint с сохранением контекста, структуры кода и формул.
```bash
python scripts/translate_marker.py --dir /mnt/project/rendered/embeddings
```

### 3. Сборка и Рендеринг (Assembly & Rendering)
Объединение всех переведенных фрагментов в единый Markdown-файл с внедрением метаданных верстки и финальная генерация PDF через Pandoc (движок XeLaTeX).
```bash
pandoc /mnt/project/rendered/embeddings/embeddings_ru.md \
  -o /mnt/project/rendered/embeddings/embeddings_ru.pdf \
  --pdf-engine=xelatex \
  --highlight-style=pygments \
  --resource-path=/mnt/project/rendered/embeddings
```

## 🚀 Автоматизация и запуск (Pipeline)

Для полной автоматизации процесса перевода книги «под ключ» используется bash-скрипт `pipeline.sh`. Он последовательно запускает извлечение разметки, конвертацию и перевод текста, избавляя от необходимости выполнять каждый шаг вручную.

### Справка по использованию

Чтобы посмотреть формат запуска, выполните команду с флагом `--help`:

```bash
./pipeline.sh --help
```

**Вывод команды:**
```text
Использование: ./pipeline.sh <path_to_input_pdf> <output_path> [page_range]
Пример: ./pipeline.sh /mnt/project/raw_data/book.pdf /mnt/project/rendered/book/ 0-20
```


### Пример запуска

Для запуска полного цикла обработки англоязычной книги и сохранения результата в структурированную папку перевода выполните:

```bash
./pipeline.sh /mnt/project/raw_data/book.pdf /mnt/project/rendered/book/
```

Для запуска полного цикла обработки первых 21 страниц англоязычной книги и сохранения результата в структурированную папку перевода выполните:

```bash
./pipeline.sh /mnt/project/raw_data/book.pdf /mnt/project/rendered/book/ 0-20
```

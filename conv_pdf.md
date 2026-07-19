# План конвертации и перевода PDF
Для перевода англоязычного PDF-файла на русский язык следуйте согласованному плану из 3 пунктов:

1. **Извлечение (Extraction):** Преобразование PDF в Markdown с использованием фирменного набора OCR-моделей от `datalab-to` (`marker-pdf`) и локального LLM-совместимого OpenAI e>
   ```bash
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

2. **Перевод (Translation):** Интеллектуальное разбиение текста на чанки и их параллельный перевод через локальный OpenAI-совместимый LLM-endpoint с сохранением контекста, структ>
   ```bash
   python scripts/translate_marker.py \
   --dir /mnt/project/rendered/embeddings
   ```

3. **Сборка и Рендеринг (Assembly & Rendering):** Объединение всех переведенных фрагментов в единый Markdown-файл с внедрением метаданных верстки и финальная генерация PDF через >
   ```bash
   pandoc /mnt/project/rendered/embeddings/embeddings_ru.md \
   -o /mnt/project/rendered/embeddings/embeddings_ru.pdf \
   --pdf-engine=xelatex \
   --highlight-style=pygments \
   --resource-path=/mnt/project/rendered/embeddings
   ```


"""
Запуск шагов пайплайна через subprocess.

Обёртка над:
  marker_single        — извлечение
  scripts/translate_marker.py  — перевод
  pandoc               — сборка PDF

Читает stdout/stderr в отдельном потоке, парсит tqdm-строки,
отправляет строки в GUI-лог и обновляет прогресс через callback-ы.
"""

import re
import os
import subprocess
import threading

STEP_LABELS = {"ext": "Извлечение", "trn": "Перевод", "pdf": "Сборка PDF"}

PROJECT = "/mnt/project"


class PipelineRunner:
    def __init__(self, app):
        self.app = app
        self.process = None
        self._stop = threading.Event()

    # ----------------------------------------------------------------
    @property
    def running(self):
        return self.process is not None and self.process.poll() is None

    # ----------------------------------------------------------------
    def run_extraction(self, input_pdf, output_dir, page_range="", use_llm=True):
        """Шаг 1 — marker_single."""
        base_dir = os.path.dirname(output_dir) if os.path.basename(output_dir) else output_dir

        cmd = [
            "marker_single", input_pdf,
            "--timeout", "3600",
            "--output_dir", base_dir,
            "--drop_repeated_text",
            "--output_format", "markdown",
        ]
        if use_llm:
            ep = self.app.config.translation.get(
                "llm_endpoint", "http://127.0.0.1:8081/v1"
            )
            cmd.extend([
                "--use_llm",
                "--llm_service", "marker.services.openai.OpenAIService",
                "--OpenAIService_openai_image_format", "jpeg",
                "--openai_api_key", "local",
                "--openai_base_url", ep,
                "--openai_model", "local-model",
            ])
        if page_range:
            cmd.extend(["--page_range", page_range])

        env = os.environ.copy()
        env["XDG_CACHE_HOME"] = os.path.join(PROJECT, "models")
        env["MARKER_STRIP_LINE_BREAKS"] = "0"

        self._run(cmd, step="ext", env=env)

    # ----------------------------------------------------------------
    def run_translation(self, target_dir):
        """Шаг 2 — translate_marker.py."""
        cmd = ["python3", os.path.join(PROJECT, "scripts", "translate_marker.py"),
               "--dir", target_dir]
        self._run(cmd, step="trn")

    # ----------------------------------------------------------------
    def run_compile(self, md_path, output_pdf):
        """Шаг 3 — pandoc."""
        work_dir = os.path.dirname(md_path)
        cmd = [
            "pandoc", md_path,
            "-o", output_pdf,
            "--pdf-engine=xelatex",
            "--highlight-style=pygments",
            f"--resource-path={work_dir}",
        ]
        self._run(cmd, step="Сборка PDF", cwd=work_dir)

    # ----------------------------------------------------------------
    def run_all(self, input_pdf, output_dir, page_range="", use_llm=True):
        """Полный пайплайн: 1 → 2 → 3."""
        self.app.log.write(f"Полный пайплайн: {os.path.basename(input_pdf)}")

        self.run_extraction(input_pdf, output_dir, page_range, use_llm)
        if self._stop.is_set():
            self.app.log.write("Прервано пользователем на шаге Извлечение", "WARNING")
            return

        book = os.path.splitext(os.path.basename(input_pdf))[0]
        base = os.path.dirname(output_dir) if os.path.basename(output_dir) == book else output_dir
        target = os.path.join(base, book)

        self.run_translation(target)
        if self._stop.is_set():
            self.app.log.write("Прервано пользователем на шаге Перевод", "WARNING")
            return

        md = os.path.join(target, f"{book}_ru.md")
        pdf = os.path.join(target, f"{book}_ru.pdf")
        self.run_compile(md, pdf)
        self.app.log.write(f"Готово: {pdf}")

    # ----------------------------------------------------------------
    def stop(self):
        self._stop.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.app.log.write("Процесс остановлен", "WARNING")

    # ----------------------------------------------------------------
    def _run(self, cmd, step, cwd=None, env=None):
        self._stop.clear()
        label = STEP_LABELS.get(step, step)
        self.app.log.write(f"\n=== {label}: {' '.join(cmd[:3])}... ===")
        self.app.set_running(True)

        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, cwd=cwd, env=env,
        )

        threading.Thread(target=self._reader, args=(step,), daemon=True).start()

    # ----------------------------------------------------------------
    def _reader(self, step):
        assert self.process is not None  # always set in _run before _reader
        out = self.process.stdout
        err = self.process.stderr

        # Читаем stderr в фоне (отдельный поток)
        def read_err():
            for line in err:
                if self._stop.is_set():
                    break
                level = "ERROR" if "error" in line.lower() else "WARNING"
                self.app.log.write(line.rstrip(), level)

        threading.Thread(target=read_err, daemon=True).start()

        for line in out:
            if self._stop.is_set():
                break
            raw = line.rstrip()

            # tqdm
            m = self._parse_tqdm(raw)
            if m and step == "trn":
                cur, total, pct = m
                self.app.pipeline.set_progress(step, pct, chunks=(cur, total))
                continue

            # Логируем остальные строки
            level = self._detect_level(raw)
            self.app.log.write(raw, level)

        # Конец процесса
        self.process.wait()
        if self._stop.is_set():
            self.app.log.write(f"{step} прерван", "WARNING")
        else:
            rc = self.process.returncode
            self.app.log.write(f"{step} завершен (exit={rc})")
            self.app.pipeline.set_progress(step, 100 if rc == 0 else 0)

        self.process = None
        self.app.set_running(False)

    # ----------------------------------------------------------------
    @staticmethod
    def _parse_tqdm(line):
        """Парсит tqdm-строку:  'Параллельный перевод книги:  47%|████▋   | 108/231'."""
        m = re.search(r"(\d+)%.*?(\d+)/(\d+)", line)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
        return None

    @staticmethod
    def _detect_level(line):
        if "[ERROR]" in line or "[CRITICAL]" in line:
            return "ERROR"
        if "[WARNING]" in line:
            return "WARNING"
        return "INFO"

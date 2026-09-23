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
    def run_extraction(self, input_pdf, output_dir, page_range="", use_llm=True, on_done=None):
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

        self._run(cmd, step="ext", env=env, on_done=on_done)

    # ----------------------------------------------------------------
    def run_translation(self, target_dir, on_done=None):
        """Шаг 2 — translate_marker.py."""
        cmd = ["python3", os.path.join(PROJECT, "scripts", "translate_marker.py"),
               "--dir", target_dir]
        self._run(cmd, step="trn", on_done=on_done)

    # ----------------------------------------------------------------
    def run_compile(self, md_path, output_pdf, on_done=None):
        """Шаг 3 — pandoc."""
        work_dir = os.path.dirname(md_path)
        cmd = [
            "pandoc", md_path,
            "-o", output_pdf,
            "--pdf-engine=xelatex",
            "--highlight-style=pygments",
            f"--resource-path={work_dir}",
        ]
        self._run(cmd, step="pdf", cwd=work_dir, on_done=on_done)

    # ----------------------------------------------------------------
    def run_all(self, input_pdf, output_dir, page_range="", use_llm=True):
        """Полный пайплайн: 1 → 2 → 3 (callback-цепочка, не блокирует Tk)."""
        self.app.log.write(f"Полный пайплайн: {os.path.basename(input_pdf)}")

        book = os.path.splitext(os.path.basename(input_pdf))[0]
        base = os.path.dirname(output_dir) if os.path.basename(output_dir) == book else output_dir
        target = os.path.join(base, book)
        md = os.path.join(target, f"{book}_ru.md")
        pdf = os.path.join(target, f"{book}_ru.pdf")

        # Обратная цепочка: compile → trn → ext (последний созданный — первый вызванный)
        def step_compile_done():
            self.app.log.write(f"Готово: {pdf}")

        def step_compile():
            if self._stop.is_set():
                self.app.log.write("Прервано на Сборка PDF", "WARNING")
                step_compile_done()
                return
            self.run_compile(md, pdf, on_done=step_compile_done)

        def step_trn():
            if self._stop.is_set():
                self.app.log.write("Прервано на Перевод", "WARNING")
                step_compile_done()
                return
            self.run_translation(target, on_done=step_compile)

        def step_ext():
            if self._stop.is_set():
                self.app.log.write("Прервано на Извлечение", "WARNING")
                step_compile_done()
                return
            self.run_extraction(input_pdf, output_dir, page_range, use_llm, on_done=step_trn)

        step_ext()

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
    def _run(self, cmd, step, cwd=None, env=None, on_done=None):
        self._stop.clear()
        self._on_done = on_done
        label = STEP_LABELS.get(step, step)
        self.app.log.write(f"\n=== {label}: {' '.join(cmd[:3])}... ===")
        self.app.set_running(True)

        try:
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, cwd=cwd, env=env,
            )
        except Exception as exc:
            self.app.log.write(f"ОШИБКА запуска {label}: {exc}", "ERROR")
            self.app.set_running(False)
            return

        # Reader читает stdout/stderr в фоне
        threading.Thread(target=self._reader, args=(step,), daemon=True).start()

        # Опрос завершения через Tk after() — не блокирует event loop
        self._poll_process()

    # ----------------------------------------------------------------
    def _poll_process(self):
        """Опос/process.poll() через Tk after() — GUI обновляется."""
        if self.process is None or self.process.poll() is not None:
            self._finish_step()
            return
        self.app.after(100, self._poll_process)

    # ----------------------------------------------------------------
    def _finish_step(self):
        """Вызывается когда process.poll() != None (процесс завершился)."""
        if self.process is None:
            return
        rc = self.process.returncode
        if self._stop.is_set():
            self.app.log.write("Шаг прерван", "WARNING")
        else:
            self.app.log.write(f"Шаг завершен (exit={rc})")
        self.process = None
        self.app.set_running(False)

        # Продолжаем цепочку run_all если есть callback
        cb = self._on_done
        self._on_done = None
        if cb:
            self.app.after(0, cb)

    # ----------------------------------------------------------------
    def _reader(self, step):
        """Читает stdout/stderr запущенного процесса и пишет в GUI-лог."""
        proc = self.process
        if proc is None:
            return
        try:
            out = proc.stdout
            err = proc.stderr
            if out is None or err is None:
                self.app.log.write("ОШИБКА: stdout/stderr потока None", "ERROR")
                return

            # Читаем stderr в фоне (отдельный поток)
            def read_err():
                try:
                    for line in err:
                        if self._stop.is_set():
                            break
                        level = "ERROR" if "error" in line.lower() else "WARNING"
                        self.app.log.write(line.rstrip(), level)
                except Exception as exc:
                    self.app.log.write(f"ОШИБКА чтения stderr: {exc}", "ERROR")

            threading.Thread(target=read_err, daemon=True).start()

            for line in out:
                if self._stop.is_set():
                    break
                raw = line.rstrip()

                # tqdm — обновляем прогресс, не дублируя строку в логе
                m = self._parse_tqdm(raw)
                if m and step == "trn":
                    cur, total, pct = m
                    self.app.pipeline.set_progress(step, pct, chunks=(cur, total))
                    continue

                # Логируем остальные строки
                level = self._detect_level(raw)
                self.app.log.write(raw, level)
        except Exception as exc:
            self.app.log.write(f"ОШИБКА {STEP_LABELS.get(step, step)}: {exc}", "ERROR")

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

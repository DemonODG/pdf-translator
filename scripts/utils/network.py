import os
import logging
import threading
import itertools
import requests
import yaml

# Подключаемся к единому логгеру пайплайна
logger = logging.getLogger("translator")

class ThreadSafeCycle:
    """Потокобезопасный круговой балансировщик серверов."""
    def __init__(self, iterable):
        self.cycle = itertools.cycle(iterable)
        self.lock = threading.Lock()

    def __next__(self):
        with self.lock:
            return next(self.cycle)


def load_translation_config(config_path):
    """Загружает настройки перевода из YAML файла."""
    if not os.path.exists(config_path):
        logger.error(f"Конфигурационный файл перевода не найден: {config_path}")
        raise FileNotFoundError(f"[ERROR] Конфигурационный файл перевода не найден: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Ошибка синтаксиса в YAML конфигурации: {e}")
            raise


def check_active_servers(server_pool):
    """Проверяет доступность серверов и возвращает список живых URL."""
    active_servers = []
    logger.info("-> Проверка доступности вычислительных серверов...")
    
    for url in server_pool:
        try:
            # Твоя оригинальная замена эндпоинта для проверки корня сервера
            base_url = url.replace("/v1/chat/completions", "/")
            response = requests.get(base_url, timeout=2)
            if response.status_code == 200:
                active_servers.append(url)
                logger.info(f"   [ОК] Сервер доступен: {url}")
            else:
                logger.warning(f"   [ВНИМАНИЕ] Сервер вернул код {response.status_code}: {url}")
        except requests.RequestException:
            logger.error(f"   [ОФФЛАЙН] Сервер недоступен: {url}")

    # Твоя бронебойная страховка локального хоста
    if not active_servers:
        logger.warning("-> Внимание: ни один сервер не ответил. Использую локальный хост.")
        active_servers = ["http://localhost:8081/v1/chat/completions"]

    return active_servers

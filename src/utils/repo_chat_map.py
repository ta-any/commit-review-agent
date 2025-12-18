# src/utils/repo_chat_mapping.py

import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

# Путь к JSON-файлу относительно этого файла (utils/)
_DATA_FILE = Path(__file__).parent.parent / "json" / "mappings.json"

# Создаём директорию json/ при импорте, если её нет
_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
logger.debug(f"📁 Папка для маппингов убедительно создана: {_DATA_FILE.parent}")

def _load_data() -> Dict[str, Dict[str, int]]:
    """Загружает данные из json/mappings.json """
    if not _DATA_FILE.exists():
        logger.debug(f"📂 Файл {_DATA_FILE} не найден — возвращаем пустой словарь")
        return {}

    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"✅ Загружено {len(data)} записей из {_DATA_FILE}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON в {_DATA_FILE}: {e}")
        return {}
    except Exception as e:
        logger.exception(f"💥 Неожиданная ошибка при загрузке {_DATA_FILE}: {e}")
        return {}

def _save_data(data: Dict[str, Dict[str, int]]) -> None:
    """Сохраняет данные в json/mappings.json."""
    try:
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"💾 Сохранено {len(data)} записей в {_DATA_FILE}")
    except Exception as e:
        logger.exception(f"💥 Ошибка при сохранении в {_DATA_FILE}: {e}")

def is_repo_id_registered(repo_id: int) -> bool:
    """Проверяет, зарегистрирован ли repo_id."""
    registered = repo_id in [record["repo_id"] for record in _load_data().values()]
    logger.debug(f"🔍 Проверка регистрации repo_id={repo_id}: {'✅ да' if registered else '❌ нет'}")
    return registered

def get_chat_id(repo_id: int) -> Optional[int]:
    """Возвращает chat_id по repo_id или None."""
    data = _load_data()
    for record in data.values():
        if record["repo_id"] == repo_id:
            chat_id = record["chat_id"]
            logger.debug(f"📩 Найден chat_id={chat_id} для repo_id={repo_id}")
            return chat_id
    logger.warning(f"⚠️ chat_id не найден для repo_id={repo_id}")
    return None

def add_mapping(repo_id: int, chat_id: int) -> None:
    """Добавляет новую связку repo_id ↔ chat_id."""
    data = _load_data()
    new_key = f"id_{repo_id}"
    if new_key in data:
        logger.info(f"🔄 Обновление существующей записи: {new_key} → repo_id={repo_id}, chat_id={chat_id}")
    else:
        logger.info(f"🆕 Добавление новой записи: {new_key} → repo_id={repo_id}, chat_id={chat_id}")
    data[new_key] = {"repo_id": repo_id, "chat_id": chat_id}
    _save_data(data)
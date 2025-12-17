# import hashlib
# import hmac
# import json 
# from typing import Dict, Any
# from fastapi import Request, Response, status
# from loguru import logger
# import httpx
# from urllib.parse import quote

# GITHUB_API_BASE = "https://api.github.com"

# async def fetch_file_contents(
#     owner: str,
#     repo: str,
#     commit_sha: str,
#     file_paths: list[str],
#     github_token: str,
# ) -> str:
#     """
#     Получает содержимое файлов из определённого коммита на GitHub.
    
#     :param owner: Владелец репозитория (например, "ta-any")
#     :param repo: Название репозитория (например, "test_commit")
#     :param commit_sha: SHA коммита (полный)
#     :param file_paths: Список путей к файлам (например, ["main.py"])
#     :param github_token: Токен GitHub для авторизации
#     :return: Строка с содержимым всех файлов в формате --- FILE: ... ---
#     """
#     headers = {
#         "Authorization": f"token {github_token}",
#         "Accept": "application/vnd.github.v3+json",
#     }
#     all_content = []

#     async with httpx.AsyncClient(timeout=30.0) as client:
#         # 1. Проверяем репозиторий
#         repo_url = f"https://api.github.com/repos/{owner}/{repo}"
#         repo_resp = await client.get(repo_url, headers=headers)
#         if repo_resp.status_code != 200:
#             return f"❌ Репозиторий {owner}/{repo} не найден: {repo_resp.status_code}"
        
#         # 2. Проверяем коммит
#         commit_url = f"{repo_url}/commits/{commit_sha}"
#         commit_resp = await client.get(commit_url, headers=headers)
#         if commit_resp.status_code != 200:
#             return f"❌ Коммит {commit_sha} не найден. Полный список: {repo_url}/commits"
        
#         # 3. Получаем файлы
#         for file_path in file_paths:
#             url = f"{repo_url}/contents/{quote(file_path)}?ref={commit_sha}"
            
#             logger.debug(f"📥 Запрашиваем файл: {file_path} @ {commit_sha[:7]}")
            
#             try:
#                 response = await client.get(url, headers=headers)
#                 if response.status_code == 200:
#                     data = response.json()
#                     # Декодируем base64 содержимое
#                     import base64
#                     content = base64.b64decode(data["content"]).decode("utf-8")
#                     all_content.append(f"--- FILE: {file_path} ---\n{content}\n--- END FILE: {file_path} ---\n")
#                 else:
#                     logger.warning(f"⚠️ Не удалось загрузить {file_path}: {response.status_code} {response.text}")
#                     all_content.append(f"--- FILE: {file_path} ---\n<ERROR: failed to fetch>\n--- END FILE ---\n")
#             except Exception as e:
#                 logger.error(f"💥 Ошибка при получении {file_path}: {e}")
#                 all_content.append(f"--- FILE: {file_path} ---\n<ERROR: {str(e)}>\n--- END FILE ---\n")

#     return "\n".join(all_content)

# def verify_signature(payload_body: bytes, signature_header: str, secret: bytes) -> bool:
#     """Проверяет подпись вебхука GitHub."""
#     logger.info("🔍 Начинаем проверку подписи...")
#     logger.debug(f"📋 Signature header: {signature_header[:50]}...")
    
#     if not signature_header.startswith("sha256="):
#         logger.warning("❌ Нет sha256 подписи")
#         return False
    
#     try:
#         sha_name, signature = signature_header.split("=", 1)
#         logger.debug(f"📋 Разобранная подпись: sha_name={sha_name}, signature_len={len(signature)}")
#     except ValueError:
#         logger.error("❌ Ошибка разбора signature header")
#         return False
    
#     if sha_name != "sha256":
#         logger.warning(f"❌ Неправильный тип подписи: {sha_name}")
#         return False

#     logger.debug(f"🔐 Секрет загружен: {len(secret)} байт")
#     mac = hmac.new(secret, msg=payload_body, digestmod=hashlib.sha256)
#     expected_signature = mac.hexdigest()
    
#     # Подробная отладка
#     logger.info(f"📊 Payload размер: {len(payload_body)} байт")
#     logger.info(f"🔍 Expected: {expected_signature[:16]}...")
#     logger.info(f"🔍 Received: {signature[:16]}...")
#     logger.debug(f"🔍 Expected full: {expected_signature}")
#     logger.debug(f"🔍 Received full: {signature}")
    
#     is_valid = hmac.compare_digest(expected_signature, signature)
#     logger.info(f"✅ Подпись {'валидна' if is_valid else 'НЕВАЛИДНА'}")
    
#     return is_valid


# def parse_push_event(event: Dict[str, Any]) -> Dict[str, Any]:
#     """Парсит push событие GitHub."""
#     logger.debug("📋 Парсим push событие...")
    
#     repo_name = event.get("repository", {}).get("full_name", "unknown")
#     pusher = event.get("pusher", {}).get("name", "unknown")
#     head_commit = event.get("head_commit", {})
    
#     commit_id = head_commit.get("id", "")[:7] if head_commit.get("id") else "unknown"
#     commit_url = head_commit.get("url", "#") if head_commit.get("url") else "#"
#     modified_files = head_commit.get("modified", [])
    
#     logger.debug(f"📂 Repo: {repo_name}, Pusher: {pusher}")
#     logger.debug(f"💾 Commit: {commit_id}, URL: {commit_url}")
#     logger.debug(f"📄 Modified files ({len(modified_files)}): {modified_files}")
    
#     return {
#         "repo_name": repo_name,
#         "pusher": pusher,
#         "commit_id": commit_id,
#         "commit_url": commit_url,
#         "modified_files": modified_files
#     }


# async def handle_github_webhook(request: Request, secret: bytes, token:str):
#     """Обработка GitHub webhook с большими payloads."""
#     logger.info("🚀 Получен webhook запрос")
    
#     # Читаем ВЕСЬ body с лимитом
#     payload_body = await request.body()
#     logger.info(f"📨 Полный payload: {len(payload_body)} байт")
    
#     signature = request.headers.get("X-Hub-Signature-256", "")
#     logger.info(f"🔑 GitHub signature-256: {signature}")

#     # Проверяем подпись ПЕРЕД парсингом
#     if not verify_signature(payload_body, signature, secret):
#         logger.error("🛑 Подпись НЕВАЛИДНА → 401")
#         return Response(status_code=status.HTTP_401_UNAUTHORIZED)

#     # Парсим JSON (теперь точно пройдёт)
#     try:
#         event = json.loads(payload_body.decode('utf-8'))  # Ручной парсинг
#         logger.success("✅ JSON распарсен!")
#     except Exception as e:
#         logger.error(f"❌ JSON ошибка: {e}")
#         return Response(status_code=400)

#     event_type = request.headers.get("x-github-event", "unknown").lower()  
#     logger.info(f"📢 Event: {event_type}")
    
#     # if event_type != "push":
#     #     return {"status": "ignored", "event": event_type}

#     # # Парсинг push (работает с реальным GitHub payload)
#     # repo_name = event.get("repository", {}).get("full_name", "unknown")
#     # pusher = event.get("pusher", {}).get("name", "unknown")
#     # head_commit = event.get("head_commit", {})
    
#     # commit_id = head_commit.get("id", "")[:7]
#     # modified_files = head_commit.get("modified", [])
    
#     # logger.info(f"📥 PUSH: {repo_name} от {pusher} (commit {commit_id})")
#     # logger.info(f"📄 Файлы: {modified_files}")
    
#     # return {
#     #     "status": "review_queued",
#     #     "repo": repo_name,
#     #     "commit": commit_id,
#     #     "files": len(modified_files)
#     # }

#     if event_type != "push":
#         return {"status": "ignored", "event": event_type}

#     # === СБОР И ЗАГРУЗКА СОДЕРЖИМОГО ФАЙЛОВ ===
#     # Собираем все файлы: added + modified (удалённые нас не интересуют)
#     all_changed_files = set()
#     for commit in event.get("commits", []):
#         all_changed_files.update(commit.get("added", []))
#         all_changed_files.update(commit.get("modified", []))
#     all_changed_files = list(all_changed_files)

#     logger.info(f"📂 Всего файлов для загрузки: {len(all_changed_files)}")

#     # Извлекаем owner и repo из full_name ("ta-any/test_commit")
#     repo_full_name = event["repository"]["full_name"]
#     owner, repo = repo_full_name.split("/", 1)

#     commit_sha = event["after"]  # полный SHA коммита

#     # Получаем содержимое файлов
#     file_contents = await fetch_file_contents(
#         owner=owner,
#         repo=repo,
#         commit_sha=commit_sha,
#         file_paths=all_changed_files,
#         github_token=token,
#     )

#     logger.info("✅ Содержимое файлов получено (предварительный просмотр):")
#     logger.debug(file_contents[:500] + ("..." if len(file_contents) > 500 else ""))

#     repo_name = event.get("repository", {}).get("full_name", "unknown")
#     commit_id = event["after"][:7]

#     return {
#         "status": "review_queued",
#         "repo": repo_name,
#         "commit": commit_id,
#         "files": len(all_changed_files),
#         "file_contents": file_contents  # ← опционально, если нужно передать дальше
#     }


# ↑ Все импорты сверху (принцип 1)
import base64
import hashlib
import hmac
import json
from typing import Dict, Any, List
from fastapi import Request, Response, status
from loguru import logger
import httpx
from urllib.parse import quote

GITHUB_API_BASE = "https://api.github.com"

def _parse_signature(signature_header: str) -> tuple[str, str] | None:
    """Разбор подписи (принцип 4, <20 строк)."""
    if not signature_header.startswith("sha256="):
        logger.debug("📋 Подпись не начинается с 'sha256='")
        return None
    try:
        parts = signature_header.split("=", 1)
        logger.debug(f"🔑 Разобрана подпись: тип='{parts[0]}', длина хеша={len(parts[1])}")
        return parts
    except ValueError:
        logger.error("❌ Ошибка при разборе signature header")
        return None

def verify_signature(payload_body: bytes, signature_header: str, secret: bytes) -> bool:
    """Проверяет подпись (1 выход, 40 строк)."""
    logger.info("🔍 Начинаем проверку подписи GitHub webhook")
    parts = _parse_signature(signature_header)
    if not parts or parts[0] != "sha256":
        logger.warning(f"❌ Неверный формат подписи: {signature_header[:50]}...")
        return False
    
    signature = parts[1]
    mac = hmac.new(secret, payload_body, hashlib.sha256)
    expected = mac.hexdigest()
    
    logger.info(f"🔍 Expected: {expected[:16]}... | Received: {signature[:16]}...")
    is_valid = hmac.compare_digest(expected, signature)
    logger.info(f"✅ Подпись {'валидна' if is_valid else 'НЕВАЛИДНА'}")
    return is_valid

async def _get_repo_info(client: httpx.AsyncClient, headers: Dict[str, str], 
                        owner: str, repo: str) -> tuple[str, str] | None:
    """Валидация repo+commit → repo_url, error_msg (принцип 4)."""
    logger.debug(f"🌐 Запрашиваем метаданные репозитория: {owner}/{repo}")
    repo_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    
    repo_resp = await client.get(repo_url, headers=headers)
    if repo_resp.status_code != 200:
        msg = f"❌ Репозиторий {owner}/{repo}: {repo_resp.status_code}"
        logger.error(msg)
        return None, msg
    
    logger.debug(f"✅ Репозиторий {owner}/{repo} найден")
    return repo_url, ""

async def _fetch_one_file(client: httpx.AsyncClient, headers: Dict[str, str], 
                         repo_url: str, file_path: str, commit_sha: str) -> str:
    """Один файл → один блок (принцип 5, 1 выход)."""
    url = f"{repo_url}/contents/{quote(file_path)}?ref={commit_sha}"
    logger.debug(f"📥 Запрашиваем файл: {file_path} @ {commit_sha[:7]}")
    
    try:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            logger.debug(f"✅ Успешно загружен: {file_path} ({len(content)} символов)")
            return f"--- FILE: {file_path} ---\n{content}\n--- END FILE ---\n"
        else:
            logger.warning(f"⚠️ Не удалось загрузить {file_path}: {resp.status_code}")
            return f"--- FILE: {file_path} ---\n<ERROR: {resp.status_code}>\n--- END FILE ---\n"
    except Exception as e:
        logger.error(f"💥 Ошибка при загрузке {file_path}: {e}")
        return f"--- FILE: {file_path} ---\n<ERROR: {e}>\n--- END FILE ---\n"

async def fetch_file_contents(owner: str, repo: str, commit_sha: str, 
                             file_paths: List[str], github_token: str) -> str:
    """Главная (35 строк, вложенность=3)."""
    logger.info(f"📂 Запрошено содержимое {len(file_paths)} файлов из {owner}/{repo}@{commit_sha[:7]}")
    if not file_paths:
        logger.warning("📭 Список файлов пуст — возвращаем пустую строку")
        return ""

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    all_content: List[str] = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        repo_url, error = await _get_repo_info(client, headers, owner, repo)
        if error:
            return error
        
        logger.info(f"🔄 Начинаем загрузку файлов...")
        for file_path in file_paths:
            content = await _fetch_one_file(client, headers, repo_url, file_path, commit_sha)
            all_content.append(content)
    
    logger.success(f"✅ Загружено {len(file_paths)} файлов")
    return "\n".join(all_content)

async def handle_github_webhook(request: Request, secret: bytes, token: str) -> Response | Dict:
    """Главная webhook (45 строк)."""
    logger.info("🚀 Получен GitHub webhook")
    
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    logger.debug(f"🔑 Подпись: {signature[:50]}...")

    if not verify_signature(payload, signature, secret):
        logger.error("🛑 Отклонено: подпись не прошла проверку")
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    
    try:
        event = json.loads(payload.decode('utf-8'))
        logger.success("✅ JSON успешно распарсен")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON: {e}")
        return Response(status_code=400)
    
    event_type = request.headers.get("x-github-event", "").lower()
    logger.info(f"📢 Тип события: {event_type}")
    if event_type != "push":
        logger.info("⏭️ Игнорируем: событие не 'push'")
        return {"status": "ignored"}
    
    # Собираем файлы из всех коммитов
    files = set()
    commits = event.get("commits", [])
    logger.debug(f"🧾 Найдено коммитов: {len(commits)}")
    for commit in commits:
        added = commit.get("added", [])
        modified = commit.get("modified", [])
        files.update(added)
        files.update(modified)
        logger.debug(f"  → +{len(added)} added, +{len(modified)} modified")
    
    if not files:
        logger.warning("📭 Нет изменённых или добавленных файлов в push")
        return {"status": "review_queued", "repo": event["repository"]["full_name"], "commit": event["after"][:7], "files": 0, "contents": ""}

    owner, repo_name = event["repository"]["full_name"].split("/", 1)
    logger.info(f"📦 Репозиторий: {owner}/{repo_name}, коммит: {event['after'][:7]}")

    contents = await fetch_file_contents(owner, repo_name, event["after"], list(files), token)
    
    logger.success(f"📤 Возвращаем результат: {len(files)} файлов, {len(contents)} символов")
    return {
        "status": "review_queued",
        "repo": event["repository"]["full_name"],
        "commit": event["after"][:7],
        "files": len(files),
        "contents": contents
    }
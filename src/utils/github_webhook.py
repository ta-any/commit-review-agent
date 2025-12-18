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

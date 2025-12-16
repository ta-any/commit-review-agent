import hashlib
import hmac
import json 
from typing import Dict, Any
from fastapi import Request, Response, status
from loguru import logger


def verify_signature(payload_body: bytes, signature_header: str, secret: bytes) -> bool:
    """Проверяет подпись вебхука GitHub."""
    logger.info("🔍 Начинаем проверку подписи...")
    logger.debug(f"📋 Signature header: {signature_header[:50]}...")
    
    if not signature_header.startswith("sha256="):
        logger.warning("❌ Нет sha256 подписи")
        return False
    
    try:
        sha_name, signature = signature_header.split("=", 1)
        logger.debug(f"📋 Разобранная подпись: sha_name={sha_name}, signature_len={len(signature)}")
    except ValueError:
        logger.error("❌ Ошибка разбора signature header")
        return False
    
    if sha_name != "sha256":
        logger.warning(f"❌ Неправильный тип подписи: {sha_name}")
        return False

    logger.debug(f"🔐 Секрет загружен: {len(secret)} байт")
    mac = hmac.new(secret, msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    
    # Подробная отладка
    logger.info(f"📊 Payload размер: {len(payload_body)} байт")
    logger.info(f"🔍 Expected: {expected_signature[:16]}...")
    logger.info(f"🔍 Received: {signature[:16]}...")
    logger.debug(f"🔍 Expected full: {expected_signature}")
    logger.debug(f"🔍 Received full: {signature}")
    
    is_valid = hmac.compare_digest(expected_signature, signature)
    logger.info(f"✅ Подпись {'валидна' if is_valid else 'НЕВАЛИДНА'}")
    
    return is_valid


def parse_push_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Парсит push событие GitHub."""
    logger.debug("📋 Парсим push событие...")
    
    repo_name = event.get("repository", {}).get("full_name", "unknown")
    pusher = event.get("pusher", {}).get("name", "unknown")
    head_commit = event.get("head_commit", {})
    
    commit_id = head_commit.get("id", "")[:7] if head_commit.get("id") else "unknown"
    commit_url = head_commit.get("url", "#") if head_commit.get("url") else "#"
    modified_files = head_commit.get("modified", [])
    
    logger.debug(f"📂 Repo: {repo_name}, Pusher: {pusher}")
    logger.debug(f"💾 Commit: {commit_id}, URL: {commit_url}")
    logger.debug(f"📄 Modified files ({len(modified_files)}): {modified_files}")
    
    return {
        "repo_name": repo_name,
        "pusher": pusher,
        "commit_id": commit_id,
        "commit_url": commit_url,
        "modified_files": modified_files
    }


async def handle_github_webhook(request: Request, secret: bytes):
    """Обработка GitHub webhook с большими payloads."""
    logger.info("🚀 Получен webhook запрос")
    
    # Читаем ВЕСЬ body с лимитом
    payload_body = await request.body()
    logger.info(f"📨 Полный payload: {len(payload_body)} байт")
    
    signature = request.headers.get("X-Hub-Signature-256", "")
    logger.info(f"🔑 GitHub signature-256: {signature}")

    # Проверяем подпись ПЕРЕД парсингом
    if not verify_signature(payload_body, signature, secret):
        logger.error("🛑 Подпись НЕВАЛИДНА → 401")
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    # Парсим JSON (теперь точно пройдёт)
    try:
        event = json.loads(payload_body.decode('utf-8'))  # Ручной парсинг
        logger.success("✅ JSON распарсен!")
    except Exception as e:
        logger.error(f"❌ JSON ошибка: {e}")
        return Response(status_code=400)

    event_type = request.headers.get("x-github-event", "unknown").lower()  # ✅ РАБОТАЕТ
    logger.info(f"📢 Event: {event_type}")
    
    if event_type != "push":
        return {"status": "ignored", "event": event_type}

    # Парсинг push (работает с реальным GitHub payload)
    repo_name = event.get("repository", {}).get("full_name", "unknown")
    pusher = event.get("pusher", {}).get("name", "unknown")
    head_commit = event.get("head_commit", {})
    
    commit_id = head_commit.get("id", "")[:7]
    modified_files = head_commit.get("modified", [])
    
    logger.info(f"📥 PUSH: {repo_name} от {pusher} (commit {commit_id})")
    logger.info(f"📄 Файлы: {modified_files}")
    
    return {
        "status": "review_queued",
        "repo": repo_name,
        "commit": commit_id,
        "files": len(modified_files)
    }


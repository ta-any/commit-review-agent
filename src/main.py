# src/main.py

from dotenv import load_dotenv
import os

load_dotenv()  # ← ЗАГРУЖАЕМ .env до всего остального

from fastapi import FastAPI, Request
from src.utils.github_webhook import handle_github_webhook
from src.utils.mistral_client import get_long_completion
from src.utils.telegram_notifier import notify_telegram_review, send_code_review
from loguru import logger

logger.add("webhook_debug.log", rotation="10 MB")  
app = FastAPI(title="AI Code Reviewer Bot")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET").encode("utf-8")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@app.post("/")
async def root_webhook(request: Request):
    try:
        data_result = await handle_github_webhook(request, GITHUB_WEBHOOK_SECRET, GITHUB_TOKEN)
        if data_result.get("status") == "review_queued":
            success = await notify_telegram_review(
                repo_name=data_result['repo'],
                commit_id=data_result['commit'],
                files_count=data_result['files']
            )
            if success:
                logger.success("📱 Telegram уведомление отправлено!")
            
            code = data_result.get("contents") or "<FAILED TO FETCH FILE CONTENTS>"
            prompt = f"Проанализируй следующий код:\n\n{code}" 
            review = await get_long_completion(prompt)
            
            # Отправляем результат
            await send_code_review(review)

        return {"status": "ok"}
    except Exception as e:
        logger.exception("💥 Ошибка в webhook обработчике")
        return {"status": "error", "detail": str(e)}, 500





# from dotenv import load_dotenv
# import os

# load_dotenv()  # ← ЗАГРУЖАЕМ .env до всего остального

# import aiohttp
# from fastapi import FastAPI, Request
# from src.utils.github_webhook import handle_github_webhook, verify_signature, fetch_file_contents
# from src.utils.mistral_client import get_long_completion
# from loguru import logger

# logger.add("webhook_debug.log", rotation="10 MB")  
# app = FastAPI(title="AI Code Reviewer Bot")

# GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET").encode("utf-8")
# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
# chat_id = os.getenv("TELEGRAM_CHAT_ID")


# async def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
#     """
#     Асинхронно отправляет сообщение в Telegram бот.
    
#     Args:
#         bot_token: Токен бота от @BotFather
#         chat_id: ID чата (пользователя/группы/канала)
#         message: Текст сообщения
    
#     Returns:
#         True если отправлено успешно
#     """
#     url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
#     payload = {
#         "chat_id": chat_id,
#         "text": message,
#         "parse_mode": "HTML"  # Поддерживает <b>, <i>, <code>, ссылки
#     }
    
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
#                 result = await response.json()
                
#                 if result.get("ok"):
#                     print(f"✅ Сообщение отправлено: {result['result']['message_id']}")
#                     return True
#                 else:
#                     print(f"❌ Ошибка Telegram: {result.get('description', 'Unknown error')}")
#                     return False
                    
#     except aiohttp.ClientError as e:
#         print(f"❌ Network error: {e}")
#         return False
#     except Exception as e:
#         print(f"❌ Unexpected error: {e}")
#         return False

# # Пример использования в FastAPI:
# async def notify_telegram_review(repo_name: str, commit_id: str, files_count: int):
#     """Уведомление о запуске code review."""
    
#     if not bot_token or not chat_id:
#         print("⚠️ Telegram credentials не настроены")
#         return False
    
#     message = f"""
# 🚀 <b>Code Review запущен!</b>

# 📂 Репозиторий: <b>{repo_name}</b>
# 💾 Коммит: <code>{commit_id}</code>
# 📄 Файлов для анализа: <b>{files_count}</b>

# ⏳ Анализ запущен...
#     """.strip()
    
#     return await send_telegram_message(bot_token, chat_id, message)

# # Интеграция в ваш webhook (добавьте в handle_github_webhook):
# @app.post("/")
# async def root_webhook(request: Request):
#     try:
#         data_result = await handle_github_webhook(request, GITHUB_WEBHOOK_SECRET, GITHUB_TOKEN)
#         if data_result.get("status") == "review_queued":
#             success = await notify_telegram_review(
#                 repo_name=data_result['repo'],
#                 commit_id=data_result['commit'],
#                 files_count=data_result['files']
#             )
#             if success:
#                 logger.success("📱 Telegram уведомление отправлено!")
            
#             code = data_result.get("contents")
#             logger.info(f"Code from gitHub {code}")
            
#             if code is None:
#                 code = "<FAILED TO FETCH FILE CONTENTS>"

#             prompt = f"Проанализируй следующий код:\n\n{code}" 

#             review = await get_long_completion(prompt)
#             return await send_telegram_message(bot_token, chat_id, review)

#         return {"status": "ok"}
#     except Exception as e:
#         logger.exception("💥 Ошибка в webhook обработчике")
#         return {"status": "error", "detail": str(e)}, 500

# @app.post("/webhook/github")
# async def github_webhook(request: Request):
#     return await root_webhook(request)

# @app.get("/")
# async def health_check():
#     return {"status": "AI Code Reviewer Bot is running!"}


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





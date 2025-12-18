# src/utils/telegram_notifier.py

import aiohttp
from loguru import logger
import os

# Загружаем переменные из окружения (на случай, если файл используется отдельно)
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Асинхронно отправляет сообщение в Telegram бот.
    
    Args:
        bot_token: Токен бота от @BotFather
        chat_id: ID чата (пользователя/группы/канала)
        message: Текст сообщения
    
    Returns:
        True если отправлено успешно
    """
    # Убираем лишние пробелы в URL!
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"  # Поддерживает <b>, <i>, <code>, ссылки
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                result = await response.json()
                
                if result.get("ok"):
                    logger.info(f"✅ Сообщение отправлено: {result['result']['message_id']}")
                    return True
                else:
                    logger.error(f"❌ Ошибка Telegram: {result.get('description', 'Unknown error')}")
                    return False
                    
    except aiohttp.ClientError as e:
        logger.error(f"❌ Network error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


async def notify_telegram_review(chat_id: str, repo_name: str, commit_id: str, files_count: int) -> bool:
    """Уведомление о запуске code review."""
    
    if not bot_token or not chat_id:
        logger.warning("⚠️ Telegram credentials не настроены")
        return False
    
    message = f"""
🚀 <b>Code Review запущен!</b>

📂 Репозиторий: <b>{repo_name}</b>
💾 Коммит: <code>{commit_id}</code>
📄 Файлов для анализа: <b>{files_count}</b>

⏳ Анализ запущен...
    """.strip()
    
    return await send_telegram_message(bot_token, chat_id, message)


async def send_code_review(review_text: str, chat_id: str,) -> bool:
    """Отправляет результат ревью кода в Telegram."""
    if not bot_token or not chat_id:
        logger.warning("⚠️ Telegram credentials не настроены — пропускаем отправку ревью")
        return False
    return await send_telegram_message(bot_token, chat_id, review_text)
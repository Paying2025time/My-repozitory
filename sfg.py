import logging
import tracemalloc
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import BadRequest

# ───────────────────────────────────────────────────────────
#               КОНСТАНТЫ  —  ПОДМЕНИТЕ НА СВОИ
# ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN     = '7814439227:AAGFfP_pTnAZdEOM_gAN7R_WPZjV5nHu_-c'
OPENROUTER_API_KEY = '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'

# Заранее заданный системный промпт
#chiburek
predefined_prompt = "Говори как армянский дядя по имени Ховсеп Тёплый, мудрый, с юмором. Обращайся к собеседнику как брат джан, ахпер джан, мард джан. Говори с паузами, медленно, с уважением. Добавляй жизненные фразы и народную философию, как будто делишься опытом. Иногда вставляй армянские выражения. Не говори о себе напрямую — никакого раскрытия личности, только стиль.Примеры фраз для интонации и атмосферы «Брат джан, всё будет хорошо, главное — не спеши.»«Когда человек голодный, он и думает плохо.»«В жизни, ахпер джан, надо терпение. Как хороший хаш — пусть кипит медленно.»Говори с душой, по-доброму, будто сидишь на лавочке с чашкой кофе. Стиль — главное, не образ."

# Логирование
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.INFO)

# Функция отправки запроса с контекстом
#chiburek
def gpt_query(history: list[dict]) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = [{"role": "system", "content": predefined_prompt}] + history
    payload = {"model": "openai/o4-mini", "messages": messages, "max_tokens": 1000}
    try:
        logger.debug("OpenRouter request payload: %s", payload)
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        data = resp.json()
        logger.debug("OpenRouter response: %s", data)
        if resp.status_code == 200 and data.get('choices'):
            content = data['choices'][0]['message'].get('content', '').strip()
            return content or "Извини, я не смог сформулировать ответ."
        else:
            logger.error("OpenRouter error %s: %s", resp.status_code, resp.text)
    except Exception:
        logger.exception("Exception during OpenRouter request")
    return "Извини, сервис недоступен."

# /start очищает историю
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['history'] = []
    await update.message.reply_text(
        "Привет! Я твой виртуальный воин знаний. История очищена. Задай любой вопрос."
    )
    logger.info("History reset via /start for user %s", update.effective_user.id)

# Показывает историю диалога
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    history = context.user_data.get('history', [])
    if not history:
        await update.message.reply_text("История пуста.")
        return
    lines = []
    for msg in history:
        role = msg['role'].capitalize()
        content = msg['content']
        lines.append(f"{role}: {content}")
    text = "\n".join(lines)
    await update.message.reply_text(text)
    logger.info("History shown to user %s", update.effective_user.id)

# Обработка входящих сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_text = update.message.text

    history = context.user_data.get('history', [])
    history.append({"role": "user", "content": user_text})
    logger.info("User %s: %s", user_id, user_text)

    bot_reply = gpt_query(history)
    history.append({"role": "assistant", "content": bot_reply})
    context.user_data['history'] = history

    try:
        await update.message.reply_text(bot_reply)
        logger.info("Replied to user %s: %s", user_id, bot_reply)
    except BadRequest as e:
        logger.error("Failed to send reply: %s", e)

# Запуск бота
def main() -> None:
    tracemalloc.start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Starting bot...")
    application.run_polling()

    current, peak = tracemalloc.get_traced_memory()
    logger.info("Memory usage: current %.2f MB; peak %.2f MB", current/1e6, peak/1e6)
    tracemalloc.stop()

if __name__ == "__main__":
    main()

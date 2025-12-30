import asyncio
import nest_asyncio
nest_asyncio.apply()
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode
import os
from dotenv import load_dotenv
import random
import openai
from openai import OpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json

# ------------------- Load Tokens -------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai.api_key)

# ------------------- Track Active Users -------------------
active_usernames = set()


# File to store usernames
USER_FILE = "users.json"

# Load usernames on startup
def load_usernames():
    global active_usernames
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            active_usernames.update(json.load(f))
        print(f"✅ Loaded {len(active_usernames)} usernames.")
    except FileNotFoundError:
        print("📁 No saved user file found. Starting fresh.")
    except Exception as e:
        print("❌ Failed to load usernames:", e)

# Save usernames to file
def save_usernames():
    try:
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(list(active_usernames), f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(active_usernames)} usernames.")
    except Exception as e:
        print("❌ Failed to save usernames:", e)


async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user and user.username:
        if user.username not in active_usernames:
            active_usernames.add(user.username)
            save_usernames()  # Save immediately when a new one is added
            
# ------------------- Start Command -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Chat ID: {update.effective_chat.id}")
    await update.message.reply_text("سلام! من ربات گروه مدیریت استرسم 😊")

# ------------------- GPT Question Generator -------------------

themes = [
    "Ask a poetic and dreamy question about how emotions feel.",
    "Ask a funny and light-hearted question related to everyday stress.",
    "Ask a deep and reflective question about how someone handles anxiety.",
    "Ask a metaphorical question that turns stress into a symbol or image.",
    "Ask a journal-style question that helps people explore their thoughts.",
    "Ask a question like a calm friend inviting someone to breathe and share.",
    "Ask a creative question using colors or seasons to describe emotions.",
    "Ask a question that encourages gratitude and noticing small joys.",
    "Ask a question that compares stress to weather or natural forces.",
    "Ask a question that helps someone reconnect with their inner peace.",
    "Ask a playful ‘what if’ question that invites imagination and emotion.",
    "Ask a nostalgic question about comforting memories during hard times.",
    "Ask a gentle and warm question that could be part of a daily check-in.",
    "Ask a surreal question, like something from a dream or fantasy.",
    "Ask a short, thought-provoking quote-style question.",
    "Ask a music-related question about songs that help during stress.",
    "Ask a sensory question — taste, smell, sound — linked to feelings.",
    "Ask a question about how someone would comfort a friend who's anxious.",
    "Ask a storytelling-style question, like ‘Imagine you’re on a calm island…’",
    "Ask a self-care question disguised as a game or playful challenge."
]


async def generate_question():
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content":  (
            "You are a supportive Telegram bot for stress relief...\n"
            + random.choice(themes) + "\n"
            "Write the question in Persian (Farsi), casual and safe."
            )
                }
            ],
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ GPT Error:", e)
        return "وقتی استرس داری، معمولاً چه کاری بهت کمک می‌کنه؟"



async def generate_funny_reply(user_text: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a hilarious and sarcastic Telegram bot. "
                        "Whenever someone replies to your question, you react with a short and funny comment in Persian (Farsi). "
                        "Be playful, maybe a little dramatic, but never rude or inappropriate. "
                        "Act like a witty friend responding in group chat."
                    )
                },
                {
                    "role": "user",
                    "content": f"پاسخ کاربر: {user_text}\n\nجواب کوتاه، بامزه و فارسی بده:"
                }
            ],
            temperature=0.9
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ GPT funny reply error:", e)
        return "😂 جوابت خیلی خاص بود، مرسی!"
# ------------------- /ask Command -------------------
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        await update.message.reply_text("این دستور فقط توی گروه کار می‌کنه.")
        return

    question = await generate_question()
    try:
        usernames = list(active_usernames)
        mentions = [f"@{u}" for u in random.sample(usernames, min(3, len(usernames)))]
    except Exception:
        mentions = []

    message = f"{question}\n\n📣 {' '.join(mentions)}"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

# ------------------- Scheduled Ask -------------------
async def ask_group(app):
    try:
        # chat_id = -1003675950022  # Replace this with your real group chat ID
        chat_id = -1003501761776
        question = await generate_question()

        usernames = list(active_usernames)
        mentions = [f"@{u}" for u in random.sample(usernames, min(3, len(usernames)))]

        message = f"🧠 سوال امروز:\n{question}\n\n📣 {' '.join(mentions)}"
        await app.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)

    except Exception as e:
        print("❌ Scheduler ask_group error:", e)


async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("💬 Got a message...")

    msg = update.message
    if msg.reply_to_message:
        print("↩️ It is a reply!")

    if msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id:
        print("✅ It's a reply to the bot. Generating funny reply...")

        user_text = msg.text
        funny_response = await generate_funny_reply(user_text)
        await msg.reply_text(funny_response)

# ------------------- Start the Bot -------------------
async def main():
    load_usernames()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_users))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_reply))

    from datetime import datetime, timedelta

    # 🔧 Schedule test: run 1 minute from now
    run_time = datetime.now() + timedelta(minutes=1)
    # Scheduler (AFTER app is defined!)
    scheduler = AsyncIOScheduler()
# 🔄 Correct async scheduler for your ask_group()
    scheduler.add_job(
        ask_group,
        trigger='date',
        run_date=run_time,
        args=[app]  # pass the app like this
    )
    # scheduler.add_job(
    #     lambda: asyncio.create_task(ask_group(app)),
    #     trigger='cron',
    #     hour='9,21',
    #     minute=0
    # )
    scheduler.start()

    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
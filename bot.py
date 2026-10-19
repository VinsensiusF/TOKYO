"""TOKYO on Telegram. Uses long polling, so it needs no domain or open port."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import config
from core import assistant
from core.voice import wav_to_ogg

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tokyo.bot")


async def _guard(update: Update) -> bool:
  """Only you may use TOKYO: it can read and write your calendar."""
  chat_id = update.effective_chat.id
  if chat_id in config.ALLOWED_CHAT_IDS:
    return True
  await update.effective_message.reply_text(
      f"Not authorized. Your chat ID is {chat_id}; add it to ALLOWED_CHAT_IDS in .env.")
  return False


def _state(ctx: ContextTypes.DEFAULT_TYPE):
  data = ctx.chat_data
  return data.setdefault("history", []), data.get("lang", config.DEFAULT_LANG)


def _remember(ctx, user_text: str, reply: assistant.Reply) -> None:
  history = ctx.chat_data.setdefault("history", [])
  history += [{"role": "user", "content": user_text},
              {"role": "assistant", "content": reply.text}]
  del history[:-12]
  ctx.chat_data["lang"] = reply.lang


async def _send_voice(update: Update, reply: assistant.Reply) -> None:
  await update.effective_chat.send_action(ChatAction.RECORD_VOICE)
  ogg = await asyncio.to_thread(lambda: wav_to_ogg(assistant.speak(reply)))
  await update.effective_message.reply_voice(voice=ogg)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
  if not await _guard(update):
    return
  text = update.message.text
  history, lang = _state(ctx)
  await update.effective_chat.send_action(ChatAction.TYPING)
  reply = await asyncio.to_thread(assistant.ask_text, text, list(history), lang)
  _remember(ctx, text, reply)
  await update.message.reply_text(reply.text)
  if ctx.chat_data.get("voice_always"):
    await _send_voice(update, reply)


async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
  if not await _guard(update):
    return
  history, lang = _state(ctx)
  await update.effective_chat.send_action(ChatAction.TYPING)
  file = await (update.message.voice or update.message.audio).get_file()
  audio = bytes(await file.download_as_bytearray())
  reply = await asyncio.to_thread(assistant.ask_voice, audio, list(history), lang)
  if reply.heard:
    _remember(ctx, reply.heard, reply)
    await update.message.reply_text(f"🎙️ {reply.heard}\n\n{reply.text}")
  else:
    await update.message.reply_text(reply.text)
  await _send_voice(update, reply)  # talk to it -> it talks back


async def cmd_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
  if not await _guard(update):
    return
  ctx.chat_data["voice_always"] = not ctx.chat_data.get("voice_always")
  state = "ON" if ctx.chat_data["voice_always"] else "OFF"
  await update.message.reply_text(f"🔊 Voice replies for text messages: {state}")


async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
  if not await _guard(update):
    return
  ctx.chat_data["history"] = []
  await update.message.reply_text("🧹 Memory cleared.")


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
  if await _guard(update):
    await update.message.reply_text(
        "⚡ TOKYO online. Type or send a voice note in Indonesian, English or Spanish.\n"
        "/voice toggles spoken replies for text, /reset clears memory.")


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
  log.exception("Handler error", exc_info=ctx.error)
  if isinstance(update, Update) and update.effective_message:
    await update.effective_message.reply_text(f"⚠️ {type(ctx.error).__name__}: {ctx.error}")


def main():
  if not config.TELEGRAM_TOKEN:
    raise SystemExit("TELEGRAM_TOKEN is missing in .env")
  app = Application.builder().token(config.TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", cmd_start))
  app.add_handler(CommandHandler("voice", cmd_voice))
  app.add_handler(CommandHandler("reset", cmd_reset))
  app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
  app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
  app.add_error_handler(on_error)
  app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()

import re
import os
import asyncio
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from loguru import logger
import config
from downloader import MediaDownloader, get_video_info
from converter import AudioConverter

logger.add("bot.log", rotation="10 MB", retention="7 days", level="INFO")

URL_PATTERN = re.compile(
    r'https?://'
    r'(?:(?:[A-Z_a-z0-9-]+\.)+[A-Z]{2,}|(?:\d{1,3}\.){3}\d{1,3})'
    r'(?:/[^ ]*)?',
    re.IGNORECASE
)

SELECTING_FORMAT = range(1)


class AudioBot:
    def __init__(self):
        self.downloader = MediaDownloader(config.TEMP_DIR)
        self.converter = AudioConverter()
        self.user_tasks = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🎵 *Audio Downloader Bot*\n\n"
            "Send me any media URL (YouTube, Instagram, etc.) and I'll convert it to audio!\n\n"
            "Supported: YouTube, Instagram, Twitter, Facebook, and 1000+ sites\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show help\n"
            "/cancel - Cancel current operation",
            parse_mode="Markdown"
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📖 *How to use:*\n\n"
            "1. Send me a media URL\n"
            "2. Choose audio format (MP3/WAV)\n"
            "3. Wait for download & conversion\n"
            "4. Receive your audio file!\n\n"
            "🎯 *Supported sites:* YouTube, Instagram, Twitter, Facebook, TikTok, and many more!",
            parse_mode="Markdown"
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.user_tasks:
            self.user_tasks[user_id].cancel()
            del self.user_tasks[user_id]
        await update.message.reply_text("❌ Operation cancelled.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    def validate_url(self, text):
        match = URL_PATTERN.search(text)
        if match:
            return match.group(0)
        return None
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        url = self.validate_url(text)
        if not url:
            await update.message.reply_text("❌ Invalid URL. Please send a valid link.")
            return
        
        info_msg = await update.message.reply_text("🔍 Fetching video info...")
        
        try:
            info = get_video_info(url)
            if not info:
                await info_msg.edit_text("❌ Could not fetch video info. The URL might be unsupported.")
                return
            
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            if duration > 3600:
                await info_msg.edit_text(
                    f"⚠️ Video is longer than 1 hour ({duration//60} min).\n"
                    "Processing may take long time. Send /cancel to abort.\n\n"
                    "Choose audio format:",
                    reply_markup=self._format_keyboard()
                )
            else:
                await info_msg.edit_text(
                    f"🎬 *{title}*\nDuration: {duration//60}:{duration%60:02d}\n\n"
                    "Choose audio format:",
                    parse_mode="Markdown",
                    reply_markup=self._format_keyboard()
                )
            
            context.user_data['url'] = url
            context.user_data['title'] = title
            return SELECTING_FORMAT
            
        except Exception as e:
            logger.error(f"Error getting info: {e}")
            await info_msg.edit_text(f"❌ Error: {str(e)}")
            return None
    
    def _format_keyboard(self):
        keyboard = [
            [KeyboardButton("MP3 🎵"), KeyboardButton("WAV 🎶")]
        ]
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    async def handle_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        choice = update.message.text
        url = context.user_data.get('url')
        title = context.user_data.get('title', 'audio')
        
        if choice.startswith("MP3"):
            audio_format = "mp3"
        elif choice.startswith("WAV"):
            audio_format = "wav"
        else:
            await update.message.reply_text("Please select MP3 or WAV:", reply_markup=self._format_keyboard())
            return SELECTING_FORMAT
        
        await update.message.reply_text(
            "⬇️ *Downloading...*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        
        try:
            def progress(percent):
                logger.info(f"Download progress: {percent}%")
            
            result = await asyncio.wait_for(
                asyncio.to_thread(self.downloader.download, url, progress),
                timeout=600
            )
            
            downloaded_file = result['file']
            
            await update.message.reply_text("🔄 *Converting to audio...*", parse_mode="Markdown")
            
            safe_title = "".join(c for c in title if c.isalnum() or c in ' -_').strip()[:50]
            
            if audio_format == "mp3":
                final_file = self.converter.convert_to_mp3(downloaded_file, safe_title)
            else:
                final_file = self.converter.convert_to_wav(downloaded_file, safe_title)
            
            file_size = self.converter.get_file_size(final_file)
            
            if file_size > config.MAX_FILE_SIZE:
                await update.message.reply_text(
                    f"❌ File too large ({file_size//(1024*1024)}MB). Telegram limit is 50MB."
                )
                os.remove(final_file)
                return
            
            await update.message.reply_text("📤 *Sending file...*", parse_mode="Markdown")
            
            await update.message.reply_audio(
                audio=open(final_file, 'rb'),
                title=safe_title,
                performer=result.get('uploader', 'Unknown')
            )
            
            os.remove(final_file)
            
            await update.message.reply_text("✅ Done! Send another URL to convert more.")
            
        except asyncio.TimeoutError:
            await update.message.reply_text("❌ Operation timed out. Video may be too long.")
        except Exception as e:
            logger.error(f"Processing error: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
        
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")


def main():
    bot = AudioBot()
    
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_url)],
        states={
            SELECTING_FORMAT: [MessageHandler(filters.TEXT, bot.handle_format)],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)],
    )
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("cancel", bot.cancel))
    application.add_handler(conv_handler)
    
    application.add_error_handler(bot.error_handler)
    
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

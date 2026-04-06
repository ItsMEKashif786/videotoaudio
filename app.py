import os
import re
import asyncio
import subprocess
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler, CallbackQueryHandler

BOT_TOKEN = os.getenv("BOT_TOKEN", "8733769300:AAGhjsNUxDycsH0YbHZ3I65widx5n-7Dvx8")
MAX_FILE_SIZE = 50 * 1024 * 1024
TEMP_DIR = "/tmp"
os.makedirs(TEMP_DIR, exist_ok=True)

URL_PATTERN = re.compile(
    r'https?://(?:(?:[A-Z_a-z0-9-]+\.)+[A-Z]{2,}|(?:\d{1,3}\.){3}\d{1,3})(?:/[^ ]*)?',
    re.IGNORECASE
)

SELECTING_FORMAT = range(1)

DOWNLOAD_FRAMES = ["⬇️", "⬇️⬇️", "⬇️⬇️⬇️"]
CONVERT_FRAMES = ["🔄", "🔁", "🔃"]


def progress_bar(percent, length=12):
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {int(percent)}%"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *Audio Downloader Bot*\n\n"
        "Send me any media URL and I'll convert it to audio!",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Send me a media URL\n"
        "2. Click MP3/WAV or type /mp3 /wav\n"
        "3. Wait for download & conversion\n"
        "4. Receive your audio!",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )


def get_reply_keyboard():
    keyboard = [
        [KeyboardButton("/mp3"), KeyboardButton("/wav")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
         InlineKeyboardButton("🎶 WAV", callback_data="wav")]
    ]
    return InlineKeyboardMarkup(keyboard)


def validate_url(text):
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None


def get_video_info(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
            }
        except:
            return None


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url = validate_url(text)
    if not url:
        await update.message.reply_text("❌ Invalid URL. Please send a valid link.", reply_markup=get_reply_keyboard())
        return None

    info_msg = await update.message.reply_text("🔍 Fetching video info...")

    try:
        info = get_video_info(url)
        if not info:
            await info_msg.edit_text("❌ Could not fetch video info. URL might be unsupported.")
            return None

        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)

        msg = f"🎬 *{title}*\n⏱️ Duration: {duration//60}:{duration%60:02d}\n\n🎛️ Choose audio format:"
        await info_msg.delete()
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_inline_keyboard())

        context.user_data['url'] = url
        context.user_data['title'] = title
        return SELECTING_FORMAT

    except Exception as e:
        await info_msg.edit_text(f"❌ Error: {str(e)}")
        return None


async def handle_format_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    url = context.user_data.get('url')
    title = context.user_data.get('title', 'audio')
    
    if not url:
        await update.message.reply_text("❌ No URL found. Please send a media URL first.", reply_markup=get_reply_keyboard())
        return None
    
    if text == "/mp3":
        audio_format = "mp3"
    elif text == "/wav":
        audio_format = "wav"
    else:
        return None
    
    chat_id = update.message.chat.id
    message_id = update.message.message_id
    bot = context.bot
    
    await update.message.reply_text("⬇️ *Starting download...*", parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/cancel")]], resize_keyboard=True))
    
    try:
        frame = 0
        for _ in range(15):
            try:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id,
                    text=f"{DOWNLOAD_FRAMES[frame % 3]} *Downloading...*\n\n{progress_bar(0)}"
                )
            except:
                pass
            await asyncio.sleep(0.8)
            frame += 1
        
        result = await asyncio.wait_for(
            asyncio.to_thread(download_media, url),
            timeout=600
        )
        downloaded_file = result['file']
        
        safe_title = "".join(c for c in title if c.isalnum() or c in ' -_').strip()[:50]
        
        frame = 0
        for _ in range(20):
            try:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id,
                    text=f"{CONVERT_FRAMES[frame % 3]} *Converting to {audio_format.upper()}...*\n\n{progress_bar(50)}"
                )
            except:
                pass
            await asyncio.sleep(0.6)
            frame += 1
        
        if audio_format == "mp3":
            final_file = convert_to_mp3(downloaded_file, safe_title)
        else:
            final_file = convert_to_wav(downloaded_file, safe_title)
        
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"✅ *Converting complete!*\n\n{progress_bar(100)}"
        )
        
        if os.path.exists(downloaded_file) and downloaded_file != final_file:
            os.remove(downloaded_file)
        
        file_size = os.path.getsize(final_file)
        
        if file_size > MAX_FILE_SIZE:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=f"❌ File too large ({file_size//(1024*1024)}MB). Telegram limit is 50MB."
            )
            os.remove(final_file)
            return ConversationHandler.END
        
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text="📤 *Sending file...*"
        )
        
        await bot.send_audio(
            chat_id=chat_id,
            audio=open(final_file, 'rb'),
            title=safe_title,
            performer=result.get('uploader', 'Unknown')
        )
        
        os.remove(final_file)
        
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text="✅ *Done!* Send another URL to convert more."
        )
        
        await update.message.reply_text("✅ Download complete!", reply_markup=get_reply_keyboard())
        
    except asyncio.TimeoutError:
        await update.message.reply_text("❌ Operation timed out.", reply_markup=get_reply_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=get_reply_keyboard())
    
    return ConversationHandler.END


def download_media(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(TEMP_DIR, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id', 'audio')
        ext = info.get('ext', 'm4a')
        downloaded_file = os.path.join(TEMP_DIR, f"{video_id}.{ext}")
        if not os.path.exists(downloaded_file):
            files = [f for f in os.listdir(TEMP_DIR) if video_id in f]
            if files:
                downloaded_file = os.path.join(TEMP_DIR, files[0])
        return {
            'file': downloaded_file,
            'title': info.get('title', 'audio'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown')
        }


def convert_to_mp3(input_file, title):
    output_file = os.path.join(TEMP_DIR, f"{title}.mp3")
    cmd = ['ffmpeg', '-i', input_file, '-codec:a', 'libmp3lame', '-b:a', '192k', '-preset', 'fast', '-y', output_file]
    subprocess.run(cmd, check=True, capture_output=True)
    if os.path.exists(input_file) and input_file != output_file:
        os.remove(input_file)
    return output_file


def convert_to_wav(input_file, title):
    output_file = os.path.join(TEMP_DIR, f"{title}.wav")
    cmd = ['ffmpeg', '-i', input_file, '-codec:a', 'pcm_s16le', '-preset', 'fast', '-y', output_file]
    subprocess.run(cmd, check=True, capture_output=True)
    if os.path.exists(input_file) and input_file != output_file:
        os.remove(input_file)
    return output_file


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get('url')
    title = context.user_data.get('title', 'audio')

    if choice not in ['mp3', 'wav']:
        return

    audio_format = choice
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    bot = context.bot

    try:
        frame = 0
        for _ in range(15):
            try:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id,
                    text=f"{DOWNLOAD_FRAMES[frame % 3]} *Downloading...*\n\n{progress_bar(0)}"
                )
            except:
                pass
            await asyncio.sleep(0.8)
            frame += 1
        
        result = await asyncio.wait_for(
            asyncio.to_thread(download_media, url),
            timeout=600
        )
        downloaded_file = result['file']
        
        safe_title = "".join(c for c in title if c.isalnum() or c in ' -_').strip()[:50]
        
        frame = 0
        for _ in range(20):
            try:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id,
                    text=f"{CONVERT_FRAMES[frame % 3]} *Converting to {audio_format.upper()}...*\n\n{progress_bar(50)}"
                )
            except:
                pass
            await asyncio.sleep(0.6)
            frame += 1
        
        if audio_format == "mp3":
            final_file = convert_to_mp3(downloaded_file, safe_title)
        else:
            final_file = convert_to_wav(downloaded_file, safe_title)
        
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"✅ *Complete!*\n\n{progress_bar(100)}"
        )
        
        if os.path.exists(downloaded_file) and downloaded_file != final_file:
            os.remove(downloaded_file)

        file_size = os.path.getsize(final_file)

        if file_size > MAX_FILE_SIZE:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=f"❌ File too large ({file_size//(1024*1024)}MB)."
            )
            os.remove(final_file)
            return ConversationHandler.END

        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text="📤 *Sending file...*"
        )

        await bot.send_audio(
            chat_id=chat_id,
            audio=open(final_file, 'rb'),
            title=safe_title,
            performer=result.get('uploader', 'Unknown')
        )

        os.remove(final_file)

        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text="✅ *Done!* Send another URL."
        )

    except asyncio.TimeoutError:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text="❌ Operation timed out."
        )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"❌ Error: {str(e)}"
        )

    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.", reply_markup=get_reply_keyboard())
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url),
            MessageHandler(filters.Regex(r'^/mp3$'), handle_format_command),
            MessageHandler(filters.Regex(r'^/wav$'), handle_format_command),
        ],
        states={
            SELECTING_FORMAT: [
                CallbackQueryHandler(button_callback),
                MessageHandler(filters.Regex(r'^/mp3$'), handle_format_command),
                MessageHandler(filters.Regex(r'^/wav$'), handle_format_command),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex(r'^/cancel$'), cancel_command),
        ],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)

    print("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

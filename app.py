import os
import re
import asyncio
import subprocess
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

LOADING_FRAMES = ["⬇️", "⬇️⬇️", "⬇️⬇️⬇️", "⬇️⬇️⬇️⬇️"]
CONVERT_FRAMES = ["🔄", "🔄🔄", "🔄🔄🔄", "🔄🔄🔄🔄"]
SEND_FRAMES = ["📤", "📤📤", "📤📤📤", "📤📤📤📤"]


def download_media(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(TEMP_DIR, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id', 'audio')
        downloaded_file = os.path.join(TEMP_DIR, f"{video_id}.m4a")
        if not os.path.exists(downloaded_file):
            files = [f for f in os.listdir(TEMP_DIR) if video_id in f and f.endswith('.m4a')]
            if files:
                downloaded_file = os.path.join(TEMP_DIR, files[0])
        return {
            'file': downloaded_file,
            'title': info.get('title', 'audio'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown')
        }


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


def convert_to_mp3(input_file, title):
    output_file = os.path.join(TEMP_DIR, f"{title}.mp3")
    cmd = [
        'ffmpeg', '-i', input_file,
        '-codec:a', 'libmp3lame',
        '-b:a', '192k',
        '-preset', 'fast',
        '-metadata', f'title={title}',
        '-y', output_file
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    if os.path.exists(input_file) and input_file != output_file:
        os.remove(input_file)
    return output_file


def convert_to_wav(input_file, title):
    output_file = os.path.join(TEMP_DIR, f"{title}.wav")
    cmd = [
        'ffmpeg', '-i', input_file,
        '-codec:a', 'pcm_s16le',
        '-preset', 'fast',
        '-metadata', f'title={title}',
        '-y', output_file
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    if os.path.exists(input_file) and input_file != output_file:
        os.remove(input_file)
    return output_file


async def animated_edit(bot, chat_id, message_id, frames, base_text, interval=0.5):
    for i, frame in enumerate(frames * 3):
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=f"{frame} {base_text}"
            )
        except:
            pass
        await asyncio.sleep(interval)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *Audio Downloader Bot*\n\n"
        "Send me any media URL (YouTube, Instagram, etc.) and I'll convert it to audio!",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use:*\n\n"
        "1. Send me a media URL\n"
        "2. Click MP3 or WAV button\n"
        "3. Wait for download & conversion\n"
        "4. Receive your audio file!",
        parse_mode="Markdown"
    )


def validate_url(text):
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None


def format_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
         InlineKeyboardButton("🎶 WAV", callback_data="wav")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url = validate_url(text)
    if not url:
        await update.message.reply_text("❌ Invalid URL. Please send a valid link.")
        return None

    info_msg = await update.message.reply_text("🔍 Fetching video info...")

    try:
        info = get_video_info(url)
        if not info:
            await info_msg.edit_text("❌ Could not fetch video info. URL might be unsupported.")
            return None

        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)

        msg = f"🎬 *{title}*\nDuration: {duration//60}:{duration%60:02d}\n\nChoose audio format:"
        await info_msg.delete()
        sent_msg = await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=format_inline_keyboard())

        context.user_data['url'] = url
        context.user_data['title'] = title
        context.user_data['message_id'] = sent_msg.message_id
        return SELECTING_FORMAT

    except Exception as e:
        await info_msg.edit_text(f"❌ Error: {str(e)}")
        return None


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
        await query.edit_message_text(text="⬇️ *Downloading...*", parse_mode="Markdown")
    except:
        pass

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(download_media, url),
            timeout=600
        )
        downloaded_file = result['file']

        await animated_edit(bot, chat_id, message_id, CONVERT_FRAMES, "*Converting to audio...*", 0.4)

        safe_title = "".join(c for c in title if c.isalnum() or c in ' -_').strip()[:50]

        if audio_format == "mp3":
            final_file = convert_to_mp3(downloaded_file, safe_title)
        else:
            final_file = convert_to_wav(downloaded_file, safe_title)

        file_size = os.path.getsize(final_file)

        if file_size > MAX_FILE_SIZE:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=f"❌ File too large ({file_size//(1024*1024)}MB). Telegram limit is 50MB."
            )
            os.remove(final_file)
            return ConversationHandler.END

        await animated_edit(bot, chat_id, message_id, SEND_FRAMES, "*Sending file...*", 0.3)

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

    except asyncio.TimeoutError:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text="❌ Operation timed out. Video may be too long."
        )
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"❌ Error: {str(e)}"
        )

    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)],
        states={
            SELECTING_FORMAT: [CallbackQueryHandler(button_callback)],
        },
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)

    print("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

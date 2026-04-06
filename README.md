# 🎵 Telegram Audio Downloader Bot

A Telegram bot that converts media URLs to audio files (MP3/WAV). Supports YouTube, Instagram, Twitter, Facebook, and 1000+ sites.

## Features

- ✅ Convert any media URL to MP3 or WAV
- ✅ Supports 1000+ websites (YouTube, Instagram, Twitter, etc.)
- ✅ Progress messages (Downloading → Converting → Sending)
- ✅ File size limit (50MB Telegram cap)
- ✅ Error handling
- ✅ Logging for debugging

## Requirements

- Python 3.9+
- FFmpeg (for audio conversion)

## Local Setup

### 1. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH.

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Bot

```bash
python app.py
```

## Deployment

### Option 1: FPS.ms (Recommended - 100% Free)

1. Push your code to GitHub
2. Go to https://fps.ms/free-telegram-bot-hosting/
3. Connect your GitHub repository
4. Deploy!

The bot will run 24/7 for free.

### Option 2: Render

1. Push to GitHub
2. Go to https://render.com
3. Create Web Service, connect repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `python app.py`

Note: Free tier sleeps after 15 min inactivity.

### Option 3: Docker

```bash
docker build -t telegram-audio-bot .
docker run -d telegram-audio-bot
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help |
| `/cancel` | Cancel operation |

## Usage

1. Send any media URL to the bot
2. Choose MP3 or WAV format
3. Wait for download & conversion
4. Receive your audio file!

## Supported Sites

YouTube, Instagram, Twitter, Facebook, TikTok, SoundCloud, Vimeo, and 1000+ more via yt-dlp.

## Troubleshooting

**Bot won't start:**
- Check bot token in config.py
- Ensure FFmpeg is installed

**"No such file or directory: ffmpeg":**
- Install FFmpeg system-wide or use Docker

**File too large:**
- Telegram limits audio to 50MB
- Video must be under ~1 hour

## License

MIT License

import os
import yt_dlp
from loguru import logger


class MediaDownloader:
    def __init__(self, temp_dir="/tmp"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def download(self, url, progress_callback=None):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'progress_hooks': [self._progress_hook(progress_callback)] if progress_callback else [],
            'quiet': True,
            'no_warnings': True,
            'extractaudio': True,
            'audioformat': 'mp3',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                video_id = info.get('id', 'audio')
                title = info.get('title', 'audio')
                
                ext = info.get('ext', 'm4a')
                downloaded_file = os.path.join(self.temp_dir, f"{video_id}.{ext}")
                
                if not os.path.exists(downloaded_file):
                    files = [f for f in os.listdir(self.temp_dir) if video_id in f]
                    if files:
                        downloaded_file = os.path.join(self.temp_dir, files[0])
                
                logger.info(f"Downloaded: {title}")
                return {
                    'file': downloaded_file,
                    'title': title,
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown')
                }
            except Exception as e:
                logger.error(f"Download failed: {e}")
                raise
    
    def _progress_hook(self, callback):
        def hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    percent = (d['downloaded_bytes'] / total) * 100
                    callback(percent)
            elif d['status'] == 'finished':
                callback(100)
        return hook


def get_video_info(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'thumbnail': info.get('thumbnail'),
            }
        except Exception as e:
            logger.error(f"Failed to get info: {e}")
            return None

import os
import subprocess
from loguru import logger
import config


class AudioConverter:
    def __init__(self):
        self.quality = config.AUDIO_QUALITY
    
    def convert_to_mp3(self, input_file, title="audio"):
        output_file = os.path.join(config.TEMP_DIR, f"{title}.mp3")
        
        cmd = [
            'ffmpeg', '-i', input_file,
            '-q:a', '2',
            '-metadata', f'title={title}',
            '-y',
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Converted to MP3: {output_file}")
            
            if os.path.exists(input_file) and input_file != output_file:
                os.remove(input_file)
            
            return output_file
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise Exception("Audio conversion failed")
    
    def convert_to_wav(self, input_file, title="audio"):
        output_file = os.path.join(config.TEMP_DIR, f"{title}.wav")
        
        cmd = [
            'ffmpeg', '-i', input_file,
            '-acodec', 'pcm_s16le',
            '-metadata', f'title={title}',
            '-y',
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Converted to WAV: {output_file}")
            
            if os.path.exists(input_file) and input_file != output_file:
                os.remove(input_file)
            
            return output_file
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise Exception("Audio conversion failed")
    
    def get_file_size(self, filepath):
        return os.path.getsize(filepath)

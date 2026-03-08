import os
import shutil
from mutagen.id3 import ID3, TXXX, TIT2
from mutagen.mp3 import MP3
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class MetadataManager:
    """
    Injects buyer metadata into audio files [Spec P3 Section C Fix 03].
    Used to trace leaks back to the original downloader.
    """
    @staticmethod
    def inject_buyer_info(file_path, buyer_id, purchase_id, timestamp):
        """
        Injects buyer metadata into an MP3 file (ID3 tags).
        For WAV/other formats, this can be extended.
        """
        try:
            # Create a copy to modify
            temp_path = f"{file_path}.tagged"
            shutil.copy2(file_path, temp_path)
            
            audio = MP3(temp_path, ID3=ID3)
            
            # Add or update ID3 tags
            if audio.tags is None:
                audio.add_tags()
            
            # Custom TXXX frames for buyer info
            audio.tags.add(TXXX(encoding=3, desc="MixMint_Buyer_ID", text=[str(buyer_id)]))
            audio.tags.add(TXXX(encoding=3, desc="MixMint_Purchase_ID", text=[str(purchase_id)]))
            audio.tags.add(TXXX(encoding=3, desc="MixMint_Download_TS", text=[str(timestamp)]))
            
            # Also slightly modify Title to include a hidden marker if needed
            # For now, just tags are enough for forensics
            
            audio.save()
            return temp_path
        except Exception as e:
            logger.error(f"Metadata injection failed: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None

    @staticmethod
    def cleanup_temp_file(temp_path):
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

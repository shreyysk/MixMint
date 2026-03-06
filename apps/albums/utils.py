"""
MixMint Album ZIP Processing Pipeline [Spec §5].

Handles:
- ZIP unzip
- Metadata injection per track
- Re-zip with watermarked files
- Queue-based processing
"""

import os
import zipfile
import tempfile
import shutil
from datetime import datetime

import boto3
from mutagen.id3 import ID3, TPE1, TENC, COMM

from django.conf import settings
from django.utils import timezone

from apps.albums.models import AlbumPack, AlbumTrack


def process_album_zip(album_id):
    """
    Full ZIP processing pipeline [Spec §5]:
    1. Download ZIP from R2
    2. Extract files
    3. Inject metadata per track
    4. Re-zip with watermarked files
    5. Upload back to R2
    6. Create AlbumTrack records
    """
    try:
        album = AlbumPack.objects.get(id=album_id)
    except AlbumPack.DoesNotExist:
        return

    # Update processing status
    album.processing_status = 'processing'
    album.processing_started_at = timezone.now()
    album.save(update_fields=['processing_status', 'processing_started_at'])

    s3 = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    temp_dir = tempfile.mkdtemp(prefix=f'mixmint-album-{album_id}-')
    zip_path = os.path.join(temp_dir, 'original.zip')
    extract_dir = os.path.join(temp_dir, 'extracted')
    output_zip = os.path.join(temp_dir, 'processed.zip')

    try:
        # 1. Download original ZIP from R2
        s3.download_file(settings.AWS_STORAGE_BUCKET_NAME, album.file_key, zip_path)

        # 2. Extract
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # 3. Process each audio file
        track_order = 0
        audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac'}

        for root, dirs, files in os.walk(extract_dir):
            for filename in sorted(files):
                ext = os.path.splitext(filename)[1].lower()
                if ext not in audio_extensions:
                    continue

                track_order += 1
                filepath = os.path.join(root, filename)

                # Inject metadata [Spec §5]
                if ext == '.mp3':
                    _inject_mp3_metadata(filepath, album, track_order)

                # Get file info
                file_size = os.path.getsize(filepath)

                # Create AlbumTrack record
                AlbumTrack.objects.create(
                    album=album,
                    track_order=track_order,
                    title=os.path.splitext(filename)[0],
                    processed_filename=filename,
                    file_size=file_size,
                    format=ext[1:],  # Remove the dot
                )

        # 4. Re-zip processed files
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(extract_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    arcname = os.path.relpath(filepath, extract_dir)
                    zf.write(filepath, arcname)

        # 5. Upload processed ZIP back to R2
        s3.upload_file(output_zip, settings.AWS_STORAGE_BUCKET_NAME, album.file_key)

        # 6. Mark as completed
        album.processing_status = 'completed'
        album.processing_completed_at = timezone.now()
        album.track_count = track_order
        album.save(update_fields=[
            'processing_status', 'processing_completed_at', 'track_count',
        ])

    except Exception as e:
        album.processing_status = 'failed'
        album.processing_error = str(e)
        album.save(update_fields=['processing_status', 'processing_error'])
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _inject_mp3_metadata(filepath, album, track_order):
    """
    Inject MixMint metadata into an MP3 file [Spec §5].
    Adds platform attribution, DJ ID, timestamp, and anti-resale clause.
    """
    try:
        tags = ID3(filepath)
    except Exception:
        tags = ID3()

    tags["TPE1"] = TPE1(encoding=3, text=album.dj.dj_name)
    tags["TENC"] = TENC(encoding=3, text="MixMint Distribution")
    tags["COMM"] = COMM(
        encoding=3, lang='eng', desc='MixMint Metadata',
        text=(
            f"Platform: MixMint | URL: https://mixmint.site | "
            f"DJ_ID: {album.dj.id} | TS: {datetime.now().isoformat()} | "
            f"Source: Album ZIP | Track: {track_order} | "
            f"NOTICE: This file is licensed for personal use only. "
            f"Resale, redistribution, or public performance without "
            f"authorization from the original DJ is strictly prohibited. "
            f"All rights reserved by the original creator."
        )
    )

    try:
        tags.save(filepath)
    except Exception:
        pass  # Non-fatal: continue even if metadata injection fails

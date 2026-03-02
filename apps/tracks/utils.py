import os
import tempfile
import shutil
from datetime import datetime
from mutagen.id3 import ID3, TIT2, TPE1, TALB, COMM, TENC
from django.conf import settings
import boto3


def process_track_metadata(track):
    """
    Applies mandatory MixMint metadata to a single track file.
    Includes platform ownership, DJ attribution, and anti-resale clause [Spec §8].
    """
    s3 = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    temp_dir = tempfile.mkdtemp(prefix=f"mixmint-track-{track.id}-")
    local_path = os.path.join(temp_dir, 'track.mp3')

    try:
        # 1. Download from R2
        s3.download_file(settings.AWS_STORAGE_BUCKET_NAME, track.file_key, local_path)

        # 2. Apply ID3 tags with watermark + anti-resale clause
        try:
            tags = ID3(local_path)
        except:
            tags = ID3()

        tags["TIT2"] = TIT2(encoding=3, text=track.title)
        tags["TPE1"] = TPE1(encoding=3, text=track.dj.dj_name)
        tags["TENC"] = TENC(encoding=3, text="MixMint Distribution")
        tags["COMM"] = COMM(
            encoding=3, lang='eng', desc='MixMint Metadata',
            text=(
                f"Platform: MixMint | URL: https://mixmint.site | "
                f"DJ_ID: {track.dj.id} | TS: {datetime.now().isoformat()} | "
                f"Source: Single Upload | "
                f"NOTICE: This file is licensed for personal use only. "
                f"Resale, redistribution, or public performance without "
                f"authorization from the original DJ is strictly prohibited. "
                f"All rights reserved by the original creator."
            )
        )
        tags.save(local_path)

        # 3. Upload back to R2
        s3.upload_file(local_path, settings.AWS_STORAGE_BUCKET_NAME, track.file_key)

    finally:
        shutil.rmtree(temp_dir)

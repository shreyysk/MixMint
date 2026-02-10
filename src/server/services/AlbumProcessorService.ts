import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import AdmZip from 'adm-zip';
import NodeID3 from 'node-id3';
import archiver from 'archiver';
import { supabaseServer } from '@/lib/supabaseServer';
import { r2 } from '@/lib/r2';
import { GetObjectCommand, PutObjectCommand } from '@aws-sdk/client-s3';
import { getDJStoragePath } from '@/lib/djStorage';

export interface AlbumMetadata {
    platform: string;
    platformUrl: string;
    djId: string;
    djName: string;
    albumId: string;
    albumTitle: string;
    uploadedAt: string;
    uploadSource: string;
}

export class AlbumProcessorService {
    /**
     * Main entry point for processing an uploaded ZIP
     */
    static async processUploadedZip(
        albumId: string, 
        djId: string, 
        originalFileKey: string,
        djName: string,
        albumTitle: string
    ) {
        const tempDir = path.join(os.tmpdir(), `mixmint-${albumId}`);
        const extractPath = path.join(tempDir, 'extracted');
        const originalZipPath = path.join(tempDir, 'original.zip');
        const finalZipPath = path.join(tempDir, 'processed.zip');

        try {
            // 0. Ensure clean start
            await fs.ensureDir(tempDir);
            await fs.ensureDir(extractPath);

            // 1. DOWNLOAD FROM R2
            console.log(`[ALBUM_PROCESSOR] Downloading ${originalFileKey}...`);
            const response = await r2.send(new GetObjectCommand({
                Bucket: process.env.R2_BUCKET_NAME!,
                Key: originalFileKey
            }));
            
            const bodyArray = await response.Body?.transformToByteArray();
            if (!bodyArray) throw new Error("Empty file received from R2");
            await fs.writeFile(originalZipPath, Buffer.from(bodyArray));

            // 2. UNZIP
            console.log(`[ALBUM_PROCESSOR] Unzipping...`);
            const zip = new AdmZip(originalZipPath);
            zip.extractAllTo(extractPath, true);

            // 3. FIND AUDIO FILES
            const audioFiles = await this.getAudioFiles(extractPath);
            console.log(`[ALBUM_PROCESSOR] Found ${audioFiles.length} audio files.`);

            // 4. ADD METADATA
            const metadata: AlbumMetadata = {
                platform: 'MixMint',
                platformUrl: 'https://mixmint.site',
                djId,
                djName,
                albumId,
                albumTitle,
                uploadedAt: new Date().toISOString(),
                uploadSource: 'dj_zip_upload'
            };

            for (const filePath of audioFiles) {
                if (filePath.toLowerCase().endsWith('.mp3')) {
                    await this.addMp3Metadata(filePath, metadata);
                }
                // (WAV/FLAC would need specialized logic or ffmpeg)
            }

            // 5. GENERATE README
            const readmeContent = this.generateReadme(djName, albumTitle, audioFiles.map(f => path.basename(f)));
            await fs.writeFile(path.join(extractPath, 'README_MIXMINT.txt'), readmeContent);

            // 6. REZIP
            console.log(`[ALBUM_PROCESSOR] Creating final ZIP...`);
            await this.createZip(extractPath, finalZipPath);

            // 7. UPLOAD TO R2
            const finalKey = getDJStoragePath(
                djName,
                djId,
                'albums',
                `${albumTitle.replace(/\s+/g, '_')}_processed.zip`
            );

            const finalBuffer = await fs.readFile(finalZipPath);
            await r2.send(new PutObjectCommand({
                Bucket: process.env.R2_BUCKET_NAME!,
                Key: finalKey,
                Body: finalBuffer,
                ContentType: 'application/zip',
                Metadata: {
                    "x-platform": "MixMint",
                    "x-album-id": albumId,
                    "x-dj-id": djId
                }
            }));

            // 8. UPDATE DATABASE
            const stats = await fs.stat(finalZipPath);
            await supabaseServer
                .from('album_packs')
                .update({
                    file_key: finalKey,
                    processing_status: 'completed',
                    processing_completed_at: new Date().toISOString(),
                    track_count: audioFiles.length,
                })
                .eq('id', albumId);

            console.log(`[ALBUM_PROCESSOR] Success. Final Key: ${finalKey}`);
            return { success: true, finalKey };

        } catch (err: unknown) {
            console.error('[ALBUM_PROCESSOR_ERROR]', err);
            const errorMessage = err instanceof Error ? err.message : 'Unknown processing error';
            await supabaseServer
                .from('album_packs')
                .update({
                    processing_status: 'failed',
                    processing_error: errorMessage
                })
                .eq('id', albumId);
            throw err;
        } finally {
            // 9. CLEANUP
            await fs.remove(tempDir).catch((e: unknown) => console.error('[CLEANUP_ERROR]', e));
        }
    }

    /**
     * Option 1: Process tracks and generate a ZIP
     */
    static async processGeneratedZip(
        albumId: string,
        djId: string,
        djName: string,
        albumTitle: string
    ) {
        const tempDir = path.join(os.tmpdir(), `mixmint-gen-${albumId}`);
        const tracksDir = path.join(tempDir, 'tracks');
        const finalZipPath = path.join(tempDir, 'processed.zip');

        try {
            await fs.ensureDir(tempDir);
            await fs.ensureDir(tracksDir);

            // 1. FETCH TRACKS FROM DB
            const { data: tracks, error: trackError } = await supabaseServer
                .from('album_tracks')
                .select('*')
                .eq('album_id', albumId)
                .order('track_order', { ascending: true });

            if (trackError || !tracks || tracks.length === 0) {
                throw new Error("No tracks found for this album session");
            }

            // 2. DOWNLOAD & PROCESS EACH TRACK
            const processedTrackPaths: string[] = [];
            for (const track of tracks) {
                if (!track.original_file_key) continue;

                console.log(`[ALBUM_PROCESSOR] Processing track: ${track.title}`);
                const response = await r2.send(new GetObjectCommand({
                    Bucket: process.env.R2_BUCKET_NAME!,
                    Key: track.original_file_key
                }));

                const bodyArray = await response.Body?.transformToByteArray();
                if (!bodyArray) continue;

                const ext = path.extname(track.original_file_key) || '.mp3';
                const localPath = path.join(tracksDir, `${track.track_order}_${track.title.replace(/\s+/g, '_')}${ext}`);
                await fs.writeFile(localPath, Buffer.from(bodyArray));

                // Add Metadata
                const metadata: AlbumMetadata = {
                    platform: 'MixMint',
                    platformUrl: 'https://mixmint.site',
                    djId,
                    djName,
                    albumId,
                    albumTitle,
                    uploadedAt: new Date().toISOString(),
                    uploadSource: 'system_generated'
                };

                if (localPath.toLowerCase().endsWith('.mp3')) {
                    await this.addMp3Metadata(localPath, metadata);
                }

                processedTrackPaths.push(localPath);
            }

            // 3. GENERATE README
            const readmeContent = this.generateReadme(djName, albumTitle, tracks.map(t => t.title));
            await fs.writeFile(path.join(tracksDir, 'README_MIXMINT.txt'), readmeContent);

            // 4. REZIP
            await this.createZip(tracksDir, finalZipPath);

            // 5. UPLOAD TO R2
            const finalKey = getDJStoragePath(
                djName,
                djId,
                'albums',
                `${albumTitle.replace(/\s+/g, '_')}_generated.zip`
            );

            const finalBuffer = await fs.readFile(finalZipPath);
            await r2.send(new PutObjectCommand({
                Bucket: process.env.R2_BUCKET_NAME!,
                Key: finalKey,
                Body: finalBuffer,
                ContentType: 'application/zip'
            }));

            // 6. UPDATE DATABASE
            await supabaseServer
                .from('album_packs')
                .update({
                    file_key: finalKey,
                    processing_status: 'completed',
                    processing_completed_at: new Date().toISOString(),
                    track_count: processedTrackPaths.length,
                })
                .eq('id', albumId);

            return { success: true, finalKey };

        } catch (err: unknown) {
            console.error('[ALBUM_GEN_ERROR]', err);
            const errorMessage = err instanceof Error ? err.message : 'Unknown generation error';
            await supabaseServer
                .from('album_packs')
                .update({
                    processing_status: 'failed',
                    processing_error: errorMessage
                })
                .eq('id', albumId);
            throw err;
        } finally {
            await fs.remove(tempDir).catch((_e: unknown) => {});
        }
    }

    private static async getAudioFiles(dir: string): Promise<string[]> {
        let results: string[] = [];
        const list = await fs.readdir(dir);
        for (const file of list) {
            const filePath = path.join(dir, file);
            const stat = await fs.stat(filePath);
            if (stat && stat.isDirectory()) {
                results = results.concat(await this.getAudioFiles(filePath));
            } else {
                const ext = path.extname(file).toLowerCase();
                if (['.mp3', '.wav', '.flac'].includes(ext)) {
                    results.push(filePath);
                }
            }
        }
        return results;
    }

    private static async addMp3Metadata(filePath: string, meta: AlbumMetadata) {
        const tags = {
            comment: {
                language: 'eng',
                text: JSON.stringify({
                    platform: meta.platform,
                    url: meta.platformUrl,
                    djId: meta.djId,
                    albumId: meta.albumId,
                    uploadedAt: meta.uploadedAt
                })
            },
            encodedBy: 'MixMint - Professional DJ Marketplace',
            copyright: `Distributed via MixMint (${meta.platformUrl})`,
            artist: meta.djName,
            album: meta.albumTitle
        };
        NodeID3.write(tags, filePath);
    }

    private static generateReadme(djName: string, albumTitle: string, tracks: string[]) {
        return `
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                   🎧 MIXMINT DOWNLOAD 🎧                     ║
║                  https://mixmint.site                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

Album: ${albumTitle}
Artist/DJ: ${djName}
Downloaded: ${new Date().toLocaleDateString()}

═══════════════════════════════════════════════════════════════

📜 TRACK LIST:
${tracks.map((t, i) => `${i + 1}. ${t}`).join('\n')}

═══════════════════════════════════════════════════════════════

⚠️  COPYRIGHT NOTICE:
This content is protected by copyright law. 
Unauthorized distribution, sharing, or resale is strictly prohibited.

This download is licensed for personal use only.
Platform: MixMint (https://mixmint.site)

═══════════════════════════════════════════════════════════════

🔐 DOWNLOAD INFORMATION:
- Your download is tracked and watermarked
- Files contain embedded MixMint metadata
- Sharing this download violates Terms of Service
- Support artists by purchasing legally

═══════════════════════════════════════════════════════════════

Thank you for supporting independent DJs! 🎶
`;
    }

    private static createZip(sourceDir: string, outPath: string): Promise<void> {
        return new Promise((resolve, reject) => {
            const output = fs.createWriteStream(outPath);
            const archive = archiver('zip', { zlib: { level: 9 } });

            output.on('close', () => resolve());
            archive.on('error', (err: Error) => reject(err));

            archive.pipe(output);
            archive.directory(sourceDir, false);
            archive.finalize();
        });
    }
}

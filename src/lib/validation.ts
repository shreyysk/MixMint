/**
 * Magic Byte Validation (Anti-Spoofing)
 * Prevents malicious files renamed to .mp3, .wav, or .zip
 */
export const validateMagicBytes = (buf: Buffer, ext: string): boolean => {
    const hex = buf.toString('hex', 0, 8).toUpperCase();
    const cleanExt = ext.toLowerCase().replace('.', '');
    
    // 1. Archives (ZIP, RAR, 7Z)
    if (cleanExt === 'zip' && hex.startsWith('504B0304')) return true; // PK..
    if (cleanExt === 'rar' && hex.startsWith('52617221')) return true; // Rar!
    if (cleanExt === '7z' && hex.startsWith('377ABC')) return true;   // 7z..
    
    // 2. Audio (MP3, WAV, FLAC)
    if (cleanExt === 'mp3') {
        const isId3 = hex.startsWith('494433'); // ID3 TAG
        const isMp3Frame = hex.startsWith('FFFB') || hex.startsWith('FFF3') || hex.startsWith('FFF2'); // Frame sync
        return isId3 || isMp3Frame;
    }
    
    if (cleanExt === 'wav' && hex.startsWith('52494646')) return true; // RIFF (WAV)
    if (cleanExt === 'flac' && hex.startsWith('664C6143')) return true; // fLaC

    // 3. Images (JPEG, PNG, WEBP) for covers
    if (['jpg', 'jpeg'].includes(cleanExt) && hex.startsWith('FFD8FF')) return true;
    if (cleanExt === 'png' && hex.startsWith('89504E47')) return true;
    if (cleanExt === 'webp' && hex.includes('57454250')) return true; // WEBP is offset but let's check

    // Fallback if extension is not strictly tracked but we want to allow it
    // return true; 
    
    // For specific high-value targets, we return false if not matched
    return false;
};

/**
 * DJ Storage Utilities
 * 
 * Helper functions for generating DJ-specific R2 storage paths.
 * Format: <dj_slug>_<dj_id>/tracks|albums|fan_uploads/<timestamp>-<filename>
 */

/**
 * Converts a DJ name to a URL-safe slug
 * @param fullName - DJ's full name from profiles.full_name
 * @returns Lowercase, hyphenated slug with no special characters
 * 
 * @example
 * getDJSlug("DJ Rahul") // => "dj-rahul"
 * getDJSlug("DJ M!ke $mith") // => "dj-m-ke-smith"
 * getDJSlug("DJ   Cool  Guy") // => "dj-cool-guy"
 */
export function getDJSlug(fullName: string): string {
    return fullName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-") // Replace non-alphanumeric with hyphens
        .replace(/(^-|-$)/g, "");     // Remove leading/trailing hyphens
}

/**
 * Generates the DJ folder name combining slug and ID
 * @param fullName - DJ's full name
 * @param djId - Immutable DJ user ID (from auth.users.id)
 * @returns Folder name in format: <slug>_<id>
 * 
 * @example
 * getDJFolderName("DJ Rahul", "9f3c2a1e") // => "dj-rahul_9f3c2a1e"
 */
export function getDJFolderName(fullName: string, djId: string): string {
    const slug = getDJSlug(fullName);
    return `${slug}_${djId}`;
}

/**
 * Generates complete R2 storage path for DJ content
 * @param fullName - DJ's full name
 * @param djId - DJ user ID
 * @param subfolder - Content type subfolder: 'tracks', 'albums', or 'fan_uploads'
 * @param filename - Original filename
 * @returns Complete R2 key path with timestamp
 * 
 * @example
 * getDJStoragePath("DJ Rahul", "9f3c2a1e", "tracks", "song.mp3")
 * // => "dj-rahul_9f3c2a1e/tracks/1738568811234-song.mp3"
 */
export function getDJStoragePath(
    fullName: string,
    djId: string,
    subfolder: "tracks" | "albums" | "fan_uploads",
    filename: string
): string {
    const folderName = getDJFolderName(fullName, djId);
    const timestamp = Date.now();
    return `${folderName}/${subfolder}/${timestamp}-${filename}`;
}

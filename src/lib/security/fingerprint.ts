/**
 * Client-side fingerprinting helper.
 * Generates a stable hash based on browser/device characteristics.
 */
export function getBrowserFingerprint(): string {
  if (typeof window === 'undefined') return 'server';

  const assets = [
    navigator.userAgent,
    navigator.language,
    window.screen.colorDepth,
    window.screen.width + 'x' + window.screen.height,
    new Date().getTimezoneOffset(),
    !!window.sessionStorage,
    !!window.localStorage,
    !!window.indexedDB,
  ];

  const str = assets.join('|');
  
  // Simple hash function (murmur-like)
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0; // Convert to 32bit integer
  }
  
  return Math.abs(hash).toString(16);
}

export function getDeviceLabel(): string {
    if (typeof window === 'undefined') return 'Server';
    
    const ua = navigator.userAgent;
    if (ua.includes('Windows')) return 'Windows PC';
    if (ua.includes('Macintosh')) return 'Mac';
    if (ua.includes('iPhone')) return 'iPhone';
    if (ua.includes('Android')) return 'Android Device';
    if (ua.includes('Linux')) return 'Linux PC';
    
    return 'Web Browser';
}

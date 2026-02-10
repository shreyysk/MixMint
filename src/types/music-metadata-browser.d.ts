declare module 'music-metadata-browser' {
  export interface ICommonTagsResult {
    title?: string;
    artist?: string;
    album?: string;
    year?: number;
    track?: { no: number | null; of: number | null };
    disk?: { no: number | null; of: number | null };
    genre?: string[];
    picture?: IPicture[];
    bpm?: number;
  }

  export interface IPicture {
    format: string;
    data: Uint8Array;
    description?: string;
    type?: string;
  }

  export interface IAudioMetadata {
    common: ICommonTagsResult;
    format: any;
    native: any;
  }

  export function parseBlob(blob: Blob, options?: any): Promise<IAudioMetadata>;
}

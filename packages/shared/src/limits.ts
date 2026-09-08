export const MAX_UPLOAD_MB = 50;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

export function splitBySize<T extends { size: number }>(files: T[]): { accepted: T[]; rejected: T[] } {
  return {
    accepted: files.filter((f) => f.size <= MAX_UPLOAD_BYTES),
    rejected: files.filter((f) => f.size > MAX_UPLOAD_BYTES),
  };
}

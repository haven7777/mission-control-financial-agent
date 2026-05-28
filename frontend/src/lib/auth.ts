const STORAGE_KEY = "master_code";

export function getMasterCode(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(STORAGE_KEY);
}

export function setMasterCode(code: string): void {
  localStorage.setItem(STORAGE_KEY, code);
}

export function clearMasterCode(): void {
  localStorage.removeItem(STORAGE_KEY);
}

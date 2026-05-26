const STORAGE_KEY = "notion_id";

export function persistResume(id: string) {
    if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, id);
    }
}

export function getPersistedResume() {
    if (typeof window === "undefined") {
        return null;
    }

    return localStorage.getItem(STORAGE_KEY);
}

export function clearResume() {
    if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
    }
}
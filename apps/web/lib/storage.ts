import { ResumeResponse } from "./resume-types";

const STORAGE_KEY = "notion_data";

export function persistResume(data: ResumeResponse) {
    if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }
}

export function getPersistedResume(): ResumeResponse | null {
    if (typeof window === "undefined") {
        return null;
    }

    const stored = localStorage.getItem(STORAGE_KEY);

    if (!stored) {
        return null;
    }

    try {
        return JSON.parse(stored);
    } catch {
        return null;
    }
}

export function clearResume() {
    if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
    }
}
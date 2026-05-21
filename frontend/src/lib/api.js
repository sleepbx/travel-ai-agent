export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export function apiUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export function backendUnavailableMessage() {
  return `Could not reach the backend at ${API_BASE_URL}. Start or restart the FastAPI server, then try again.`;
}

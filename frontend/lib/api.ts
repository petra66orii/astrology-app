const browserApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie.split("; ").find((value) => value.startsWith(`${name}=`))?.split("=")[1];
}

export async function ensureCsrf(): Promise<string> {
  await fetch(`${browserApiUrl}/auth/csrf/`, { credentials: "include" });
  const token = readCookie("csrftoken");
  if (!token) throw new Error("Could not establish a secure session. Refresh and try again.");
  return decodeURIComponent(token);
}

export async function apiMutation<T>(path: string, method: "POST" | "PATCH", body?: unknown): Promise<T> {
  const csrf = await ensureCsrf();
  const response = await fetch(`${browserApiUrl}${path}`, {
    method,
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const error = new Error(data?.error?.detail ?? "Request failed") as Error & { payload?: unknown; status?: number };
    error.payload = data;
    error.status = response.status;
    throw error;
  }
  return data as T;
}

export async function browserApi<T>(path: string): Promise<T> {
  const response = await fetch(`${browserApiUrl}${path}`, { credentials: "include" });
  if (!response.ok) throw new Error("Request failed");
  return response.json() as Promise<T>;
}

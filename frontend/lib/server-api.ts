import { cookies } from "next/headers";

const serverApiUrl = process.env.DJANGO_API_URL ?? "http://localhost:8000/api/v1";

export async function serverApi<T>(path: string): Promise<{ ok: boolean; status: number; data: T | null }> {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(`${serverApiUrl}${path}`, {
    headers: { Cookie: cookieHeader },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, data: response.ok ? await response.json() : null };
}

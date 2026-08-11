"use client";

import { useRouter } from "next/navigation";
import { apiMutation } from "@/lib/api";

export function LogoutButton() {
  const router = useRouter();
  return <button className="textButton" onClick={async () => { await apiMutation("/auth/logout/", "POST"); router.push("/login"); router.refresh(); }}>Sign out</button>;
}

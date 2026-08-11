import { redirect } from "next/navigation";
import { ChartForm } from "@/components/ChartForm";
import { serverApi } from "@/lib/server-api";

export default async function NewChartPage() {
  const me = await serverApi("/auth/me/");
  if (!me.ok) redirect("/login");
  return <section className="narrow pageShell"><p className="eyebrow">New natal chart</p><h1>Begin with what you know</h1><p className="lede compact">Your saved chart will preserve these exact inputs and calculation settings.</p><ChartForm /></section>;
}

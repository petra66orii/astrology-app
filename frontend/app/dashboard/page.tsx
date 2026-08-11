import Link from "next/link";
import { redirect } from "next/navigation";
import { serverApi } from "@/lib/server-api";
import type { Chart, User } from "@/lib/types";
import { LogoutButton } from "@/components/LogoutButton";

export default async function DashboardPage() {
  const [me, charts] = await Promise.all([
    serverApi<{ user: User }>("/auth/me/"),
    serverApi<{ results?: Chart[] } | Chart[]>("/charts/"),
  ]);
  if (!me.ok) redirect("/login");
  const chartList = Array.isArray(charts.data) ? charts.data : charts.data?.results ?? [];
  return (
    <section className="pageShell">
      <div className="pageHeading"><div><p className="eyebrow">Your sky archive</p><h1>Dashboard</h1><p className="muted">Signed in as {me.data?.user.email} · <LogoutButton /></p></div><Link className="button" href="/chart/new">Create a chart</Link></div>
      {chartList.length ? <div className="chartGrid">{chartList.map((chart) => <Link className="card chartCard" key={chart.id} href={`/charts/${chart.id}`}><span className="status">{chart.normalized_result?.time_precision === "UNKNOWN" ? "Unknown time" : "Exact time"}</span><h2>{chart.birth_profile_label}</h2><p>{chart.location.selected_display_name}</p><time>{new Date(chart.created_at).toLocaleDateString("en-IE", { dateStyle: "medium" })}</time></Link>)}</div> : <div className="emptyState"><h2>No saved charts yet</h2><p>Your first chart will appear here and remain tied to its original calculation version.</p><Link className="textLink" href="/chart/new">Create your first chart →</Link></div>}
    </section>
  );
}

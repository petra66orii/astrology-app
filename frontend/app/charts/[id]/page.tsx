import { notFound, redirect } from "next/navigation";
import { serverApi } from "@/lib/server-api";
import type { Chart } from "@/lib/types";

export default async function ChartPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await serverApi<Chart>(`/charts/${id}/`);
  if (response.status === 401 || response.status === 403) redirect("/login");
  if (!response.ok || !response.data) notFound();
  const chart = response.data;
  const result = chart.normalized_result;
  if (!result) return <section className="pageShell"><h1>{chart.birth_profile_label}</h1><p className="error">This calculation did not complete.</p></section>;
  const sun = result.planets.find((planet) => planet.name === "Sun");
  const moon = result.planets.find((planet) => planet.name === "Moon");
  return (
    <section className="pageShell resultPage">
      <p className="eyebrow">{result.time_precision === "EXACT" ? "Exact-time natal chart" : "Unknown-time natal chart"}</p>
      <h1>{chart.birth_profile_label}</h1><p className="lede compact">{chart.location.selected_display_name}</p>
      {result.time_precision === "UNKNOWN" && <div className="notice prominent"><strong>Some chart features are unavailable.</strong><p>Without an exact birth time, rising sign, angles, houses, and house placements are intentionally omitted. Planetary values below are shown only where the sampled day supports them.</p></div>}
      <div className="summaryGrid"><article><span>Sun</span><strong>{sun?.zodiac_sign ?? "Changes during the day"}</strong></article><article><span>Moon</span><strong>{moon?.zodiac_sign ?? "Changes during the day"}</strong></article>{result.angles && <article><span>Rising</span><strong>{formatDegrees(result.angles.ascendant)}</strong></article>}</div>
      <section className="resultSection"><h2>Planetary positions</h2><div className="tableWrap"><table><thead><tr><th>Body</th><th>Sign</th><th>Longitude</th><th>Motion</th>{result.time_precision === "EXACT" && <th>House</th>}</tr></thead><tbody>{result.planets.map((planet) => <tr key={planet.name}><th>{planet.name}</th><td>{planet.zodiac_sign ?? "Not stable"}</td><td>{planet.longitude !== null ? formatDegrees(planet.longitude) : formatRange(planet.longitude_range)}</td><td>{planet.is_retrograde === null ? "Varies" : planet.is_retrograde ? "Retrograde" : "Direct"}</td>{result.time_precision === "EXACT" && <td>{planet.house_number ?? "—"}</td>}</tr>)}</tbody></table></div></section>
      {result.houses.length > 0 && <section className="resultSection"><h2>House cusps</h2><div className="houseGrid">{result.houses.map((house) => <div key={house.number}><span>House {house.number}</span><strong>{formatDegrees(house.start_cusp)}</strong></div>)}</div></section>}
      <section className="resultSection"><h2>Major aspects</h2>{result.aspects.length ? <ul className="aspectList">{result.aspects.map((aspect, index) => <li key={`${aspect.body_one}-${aspect.body_two}-${index}`}><strong>{aspect.body_one} {aspect.name} {aspect.body_two}</strong><span>Orb {aspect.orb_degrees.toFixed(2)}°</span></li>)}</ul> : <p className="muted">No aspects were stable enough to display.</p>}</section>
    </section>
  );
}

function formatDegrees(value: number | null | undefined) { return value == null ? "Unavailable" : `${value.toFixed(2)}°`; }
function formatRange(range: { start_degrees: number; end_degrees: number; wraps_zero: boolean } | null | undefined) { return range ? `${range.start_degrees.toFixed(2)}°–${range.end_degrees.toFixed(2)}°${range.wraps_zero ? " across 0°" : ""}` : "Unavailable"; }

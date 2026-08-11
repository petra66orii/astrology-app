"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiMutation, browserApi } from "@/lib/api";
import type { BirthProfile, Chart, LocationResult } from "@/lib/types";

type OffsetCandidate = { fold: number; utc_datetime: string; utc_offset_seconds: number };

export function ChartForm() {
  const router = useRouter();
  const [precision, setPrecision] = useState<"EXACT" | "UNKNOWN">("EXACT");
  const [query, setQuery] = useState("");
  const [locations, setLocations] = useState<LocationResult[]>([]);
  const [selected, setSelected] = useState<LocationResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [candidates, setCandidates] = useState<OffsetCandidate[]>([]);
  const [pendingProfile, setPendingProfile] = useState<string | null>(null);

  useEffect(() => {
    if (selected || query.trim().length < 2) return;
    const timeout = window.setTimeout(() => {
      browserApi<{ results: LocationResult[] }>(`/locations/search/?q=${encodeURIComponent(query)}&limit=8`)
        .then((data) => setLocations(data.results)).catch(() => setLocations([]));
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [query, selected]);

  async function calculate(profileId: string, fold?: number) {
    try {
      const chart = await apiMutation<Chart>("/charts/create/", "POST", { birth_profile_id: profileId, ...(fold === undefined ? {} : { fold }) });
      router.push(`/charts/${chart.id}`);
      router.refresh();
    } catch (reason) {
      const payload = (reason as Error & { payload?: { error?: { code?: string; detail?: string; candidates?: OffsetCandidate[] } } }).payload;
      if (payload?.error?.code === "ambiguous_local_time") {
        setCandidates(payload.error.candidates ?? []);
        setPendingProfile(profileId);
      }
      setError(payload?.error?.detail ?? (reason instanceof Error ? reason.message : "Calculation failed."));
      setBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) { setError("Choose a birthplace from the search results."); return; }
    setBusy(true); setError(""); setCandidates([]);
    const data = new FormData(event.currentTarget);
    try {
      const profile = await apiMutation<BirthProfile>("/birth-profiles/", "POST", {
        display_label: data.get("display_label"), local_birth_date: data.get("birth_date"),
        local_birth_time: precision === "EXACT" ? data.get("birth_time") : null,
        birth_time_precision: precision, geonames_location_id: selected.id,
      });
      setPendingProfile(profile.id);
      await calculate(profile.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save the birth details.");
      setBusy(false);
    }
  }

  return (
    <form className="card chartForm" onSubmit={submit}>
      <label>Chart name<input name="display_label" required maxLength={120} placeholder="My birth chart" /></label>
      <label>Birth date<input name="birth_date" type="date" required /></label>
      <fieldset><legend>Birth time</legend><div className="toggleGroup"><label><input type="radio" name="precision" checked={precision === "EXACT"} onChange={() => setPrecision("EXACT")} /> Exact birth time</label><label><input type="radio" name="precision" checked={precision === "UNKNOWN"} onChange={() => setPrecision("UNKNOWN")} /> I don&apos;t know my birth time</label></div></fieldset>
      {precision === "EXACT" && <label>Local birth time<input name="birth_time" type="time" required /></label>}
      <div className="locationField"><label htmlFor="location">Birthplace</label><input id="location" value={query} onChange={(event) => { setQuery(event.target.value); setSelected(null); if (event.target.value.trim().length < 2) setLocations([]); }} autoComplete="off" placeholder="Start typing a city" role="combobox" aria-controls="location-suggestions" aria-expanded={locations.length > 0} />
        {locations.length > 0 && <ul id="location-suggestions" className="suggestions" role="listbox">{locations.map((location) => <li key={location.id}><button type="button" onClick={() => { setSelected(location); setQuery(location.display_name); setLocations([]); }}>{location.display_name}</button></li>)}</ul>}
      </div>
      {selected && <div className="selection"><strong>Selected location</strong><span>{selected.canonical_name}</span><span>{selected.region}</span><span>{selected.country_name}</span></div>}
      {precision === "UNKNOWN" && <p className="notice">Rising sign, chart angles, houses, and house placements will not be shown. Only values stable across the sampled day may appear.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {candidates.length > 0 && pendingProfile && <div className="offsetChoices"><h2>Which occurrence do you mean?</h2><p>This clock time occurred twice. Choose the matching UTC offset.</p>{candidates.map((candidate) => <button className="secondaryButton" type="button" key={candidate.fold} onClick={() => { setBusy(true); calculate(pendingProfile, candidate.fold); }}>Occurrence {candidate.fold + 1}: UTC{formatOffset(candidate.utc_offset_seconds)}</button>)}</div>}
      <button className="button" disabled={busy}>{busy ? "Calculating…" : "Create natal chart"}</button>
    </form>
  );
}

function formatOffset(seconds: number): string {
  const sign = seconds >= 0 ? "+" : "−";
  const absolute = Math.abs(seconds);
  return `${sign}${String(Math.floor(absolute / 3600)).padStart(2, "0")}:${String((absolute % 3600) / 60).padStart(2, "0")}`;
}

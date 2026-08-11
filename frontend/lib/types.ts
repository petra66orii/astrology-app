export type User = { id: string; email: string; created_at: string };

export type LocationResult = {
  id: number;
  display_name: string;
  canonical_name: string;
  region: string;
  country_name: string;
  country_code: string;
  latitude: string;
  longitude: string;
  timezone_id: string;
};

export type BirthProfile = {
  id: string;
  display_label: string;
  local_birth_date: string;
  local_birth_time: string | null;
  birth_time_precision: "EXACT" | "UNKNOWN";
  resolved_location: { selected_display_name: string; timezone_id: string };
};

export type Planet = {
  name: string;
  longitude: number | null;
  zodiac_sign: string | null;
  is_retrograde: boolean | null;
  house_number: number | null;
  longitude_range?: { start_degrees: number; end_degrees: number; wraps_zero: boolean } | null;
};

export type Chart = {
  id: string;
  birth_profile_label: string;
  status: "SUCCEEDED" | "FAILED";
  created_at: string;
  location: { selected_display_name: string; timezone_id: string };
  normalized_result: null | {
    time_precision: "EXACT" | "UNKNOWN";
    planets: Planet[];
    angles: null | { ascendant: number | null; midheaven: number | null };
    houses: { number: number; start_cusp: number; end_cusp: number }[];
    aspects: { body_one: string; body_two: string; name: string; orb_degrees: number }[];
    unavailable: { field: string; reason: string }[];
  };
};

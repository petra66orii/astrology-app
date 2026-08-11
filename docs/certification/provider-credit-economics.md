# Prokerala credit economics

Checked against the official [credit-utilisation table](https://api.prokerala.com/api-credits), [pricing calculator](https://api.prokerala.com/pricing-calculator), and [plans](https://api.prokerala.com/pricing) on 2026-08-11. Natal Planet Positions & Aspects costs 500 credits per request.

## Per-chart exposure

| Provider calls | Credits | Exact-chart equivalents |
|---:|---:|---:|
| 1 exact chart | 500 | 1 |
| 5 unknown-time samples | 2,500 | 5 |
| 9 unknown-time samples | 4,500 | 9 |
| 13 unknown-time samples | 6,500 | 13 |
| 17 unknown-time samples | 8,500 | 17 |

Credit accounting does not translate cleanly into a single monetary unit because plans are tiered, promotional prices can change, credits reset, and add-on credits have separate terms. Capacity is therefore the reliable comparison.

| Current published plan | Monthly credits | Exact charts | Unknown at 5 samples | Unknown at 17 samples |
|---|---:|---:|---:|---:|
| Free | 5,000 | 10 | 2 | 0 complete |
| Ruby | 100,000 | 200 | 40 | 11 |
| Emerald | 350,000 | 700 | 140 | 41 |
| Sapphire | 1,000,000 | 2,000 | 400 | 117 |

## Monthly usage at the current theoretical 17-sample maximum

| Charts/month | All exact | 10% unknown | 25% unknown |
|---:|---:|---:|---:|
| 100 | 50,000 | 130,000 | 250,000 |
| 1,000 | 500,000 | 1,300,000 | 2,500,000 |
| 10,000 | 5,000,000 | 13,000,000 | 25,000,000 |

## Monthly usage at the recommended five-sample production cap

| Charts/month | All exact | 10% unknown | 25% unknown |
|---:|---:|---:|---:|
| 100 | 50,000 | 70,000 | 100,000 |
| 1,000 | 500,000 | 700,000 | 1,000,000 |
| 10,000 | 5,000,000 | 7,000,000 | 10,000,000 |

## Recommendation

Keep live unknown-time charts disabled until they are numerically certified. If enabled later, cap production at five provider samples initially. A five-sample result must disclose that it describes observed stability at those samples rather than proving invariance over every instant.

Investigate a cheaper positions-only source, returned planetary speeds, or a licensed local ephemeris for stability detection before allowing adaptive subdivision. Do not interpolate houses or angles for unknown-time output; they remain omitted.

The proposed staged live-certification ceiling is 5,000 credits: five exact fixtures (2,500) plus one five-sample unknown-time experiment (2,500). The first approval should still authorize only one 500-credit Dublin exact request.

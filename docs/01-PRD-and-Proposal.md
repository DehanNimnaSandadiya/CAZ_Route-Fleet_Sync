# CAZ-Route & Fleet Sync (Bristol)
## Project Proposal & Product Requirements Document (PRD)

| | |
|---|---|
| **Version** | 1.0 (draft for stakeholder review) |
| **Date** | 7 October 2026 |
| **Product type** | Hyper-local B2B SaaS + marketplace |
| **Launch geography** | Bristol, UK (central Bristol first) |
| **Status of figures** | Regulatory facts were checked against Bristol City Council / GOV.UK sources in Oct 2026 and are marked **[verify]** where they must be re-confirmed before launch. Prices, volumes and financial figures are **planning assumptions to be validated**, not market data. |

---

## 1. Executive Summary & Problem Statement

### 1.1 Summary
**CAZ-Route & Fleet Sync** helps small delivery and trades fleets operate profitably in central Bristol. It combines four capabilities in one product:

1. a **routing engine** that understands Bristol's hills and the Clean Air Zone (CAZ) boundary;
2. a **cargo-bike micro-hub handshake** that moves the final, hardest leg from a van to a bike;
3. an **automated compliance ledger with a PCN risk predictor**; and
4. an **SME pool-sharing marketplace** for shared drop points.

The first customers are the businesses least able to absorb CAZ costs and delivery friction: sole-trader tradespeople, independent couriers, and inner-city shops, cafés and bars.

### 1.2 Bristol's operating context
| Challenge | Why it hurts small fleets |
|---|---|
| **Topography** | Bristol is built on steep ground (Clifton, Kingsdown, Brandon Hill, Totterdown, Bedminster). Double-digit gradients make cargo-bike and walking-delivery times highly route-dependent, and loaded vans are slow and fuel-hungry on climbs. Generic routing treats a hill and a flat street as equal. |
| **Street fabric** | Narrow Victorian terraces, medieval-origin lanes in the centre, one-way systems, limited loading bays and heavy parking pressure mean the "last 200 metres" often takes longer than the last 20 minutes of driving. |
| **Clean Air Zone** | Bristol operates a **Class D CAZ** (live since 28 Nov 2022) covering the city centre. Non-compliant vehicles pay per day of entry: **£9** for cars, taxis, vans and minibuses; **£100** for HGVs, buses and coaches. Compliance generally means **petrol Euro 4+ / diesel Euro 6+** (heavy vehicles Euro VI). **[verify]** |
| **Enforcement** | Camera-enforced. The charge can be paid up to **6 days before** or up to **6 days after** the day of travel. An unpaid day leads to a **Penalty Charge Notice (PCN) of £120, halved to £60 if paid within 14 days**; the unpaid daily charge is payable in addition, and there are 28 days to pay. **[verify]** |
| **Congestion** | The M32 approach, the A38 and the A4 (Bath Road) corridors suffer predictable peak gridlock; any trip crossing them is hard to time. |
| **Fragmented tools** | Firms juggle a satnav, the GOV.UK payment service, spreadsheets and memory. Nothing connects "where am I driving" to "what will it cost and what must I pay by when". |

### 1.3 Problem statement
> Small Bristol fleets lose time and money because routing tools ignore hills and the CAZ, compliance is tracked by memory, and there is no cheap way to hand the last leg to a low-emission mode or share drop-off infrastructure.

### 1.4 Value proposition
- **Cut avoidable CAZ charges** by choosing routes (or mode changes) that avoid or minimise zone entry when it is cheaper overall.
- **Eliminate avoidable PCNs** through a ledger that shows every chargeable day, its deadline and its status.
- **Shorten and de-risk the last mile** with hill-aware cargo-bike hand-offs from perimeter depots.
- **Share cost** with neighbouring businesses through pooled drop nodes.

### 1.5 Success metrics (12 months after public launch)
| Metric | Target (assumption) |
|---|---|
| Paying organisations | 400 |
| Chargeable-day coverage in ledger | ≥ 95% of detected zone entries recorded |
| PCNs among active customers | ≥ 60% reduction vs. their self-reported baseline |
| Median route plan latency (p95) | < 1.5 s |
| Handshake on-time rate | ≥ 92% |
| Logo churn (monthly) | < 3% |
| NPS | ≥ 40 |

### 1.6 Honest scope boundary
The product **supports** compliance; it does not replace the legal duty to pay. In the MVP the user pays through the official GOV.UK service, and the product records the receipt. It is not affiliated with Bristol City Council.

---

## 2. Target Audience & User Personas

### Persona A: "Dan", independent electrician / plumber (sole trader)
- **Profile:** one older diesel van, 5-9 jobs a day across BS1-BS8, books via phone and apps.
- **Pain:** unsure if his van is chargeable on a given day; forgets to pay; loses time circling for parking in Clifton.
- **Jobs to be done:** "Tell me today's cheapest, least stressful job order", "Remind me before I get a PCN."
- **Needs:** mobile-first, 2-tap day plan, WhatsApp/SMS reminders, no training.
- **Willingness to pay:** low; will pay if the product visibly saves more than it costs.

### Persona B: "Priya", owner of a 6-rider local courier firm
- **Profile:** mixed fleet of vans and e-bikes; same-day B2B parcels, contracts with shops and clinics.
- **Pain:** inconsistent rider workload due to hills; CAZ charges eating margin on non-compliant vans; no hand-off point.
- **Jobs to be done:** "Assign jobs by mode and hill load", "See the CAZ bill before it arrives."
- **Needs:** dispatcher console, multi-vehicle ledger, hub booking, invoices.

### Persona C: "Marcus", independent café/bar/retail owner in the city centre
- **Profile:** receives multiple small supplier drops daily; limited storage and kerb space.
- **Pain:** suppliers block the street; missed deliveries; wants spare capacity (a back-room shelf, a locker) to earn money.
- **Jobs to be done:** "Let suppliers drop at agreed times", "Rent out my spare slots."
- **Needs:** simple slot calendar, payouts, clear liability terms.

### Secondary stakeholders
Hub operators (depot owners), cargo-bike operators/co-operatives, Bristol City Council (data, policy), accountants and fleet-finance providers.

### Persona-to-feature map
| Feature | Dan | Priya | Marcus |
|---|:--:|:--:|:--:|
| CAZ- and hill-aware routing | ●● | ●● | ○ |
| Compliance ledger / PCN predictor | ●● | ●● | ○ |
| Micro-hub handshake | ○ | ●● | ● |
| Pool-sharing marketplace | ● | ● | ●● |

(●● core · ● useful · ○ marginal)

---

## 3. Core Features & Technical Architecture

### 3.1 Feature F1: Dynamic topography- and CAZ-aware routing engine

**Goal:** return the least *total-cost* route, not merely the fastest one.

**Functional requirements**
- **F1.1** Cost per edge = travel time (mode- and gradient-adjusted) + congestion multiplier (vans only) + CAZ term.
- **F1.2** CAZ term: if the vehicle is chargeable, the **daily charge is applied once** the first time the route touches the zone (a state-space search over *(node, charged?)*), converted to time by a customer-tunable "value of £1 in minutes".
- **F1.3** Mode profiles: *van*, *cargo-bike (e-assist)*, later *walking courier*. Each defines base speed, uphill slowdown per % gradient, max climbable gradient, downhill speed cap, and road-class restrictions (vans cannot use bike-only links).
- **F1.4** Gradient from terrain: elevation sampled per edge from a terrain model (see §4.3), giving signed grade per direction.
- **F1.5** Multi-stop sequencing (MVP: nearest-neighbour + 2-opt; Phase 3: OR-Tools VRP with time windows and zone-charge-once logic).
- **F1.6** Always show a **comparison**: recommended route vs. fastest-ignoring-CAZ, with charge avoided.
- **F1.7** Time-of-day congestion profiles for M32/A38/A4 corridors learned from anonymised fleet telemetry (cold-start from public traffic data).
- **F1.8** Explainability: every recommendation lists *why* (e.g. "Avoids £9 charge for +1.1 min").

**Non-functional:** p95 < 1.5 s for single route; < 6 s for 25-stop plan; deterministic for a given graph version.

**Acceptance criteria (examples)**
- Given a chargeable van and a destination reachable outside the zone at ≤ the value-of-time penalty, the route avoids the zone.
- Given a start point inside the zone, the charge is applied **once**, not per edge.
- A cargo bike is never routed over an edge steeper than its configured maximum uphill grade; a van is never routed over a bike-only edge.

> *The repository's `backend/app/engine.py` implements this cost model and is covered by automated tests.*

### 3.2 Feature F2: Micro-hub cargo-bike handshake system

**Goal:** let a van stop at a perimeter depot (e.g. a candidate site at **St Philip's Marsh**) and pass parcels to a cargo-bike rider for hill-heavy inner areas such as **Clifton**.

**Functional requirements**
- **F2.1** Hub registry: location, capacity, opening hours, bike capacity per trip, operator.
- **F2.2** **Handshake planner:** given origin, destination and parcel count, compare *direct van* vs. *van→hub + bike→destination* on cost (driver time, rider time × round trips, CAZ charge, platform fee) and recommend the cheaper option. The planner **will recommend direct delivery when it is cheaper**; the product does not push hand-offs where they do not pay.
- **F2.3** Capacity reservation at plan confirmation; released on delivery or cancellation.
- **F2.4** State machine: `CREATED → VAN_ARRIVED → HANDED_OVER → OUT_FOR_DELIVERY → DELIVERED`, plus `FAILED` / `CANCELLED` from any non-terminal state. Illegal transitions are rejected.
- **F2.5** Proof of hand-over: QR scan at the hub by both parties, timestamp and photo.
- **F2.6** Rider matching: nearest available e-cargo-bike with spare payload and a hill-feasible route.
- **F2.7** Platform fee per parcel handed over (see §5).

**Dependencies/risks:** securing hub sites (planning/lease), insurance for goods in transit, bike-operator supply, parcel handling standards.

### 3.3 Feature F3: Automated compliance ledger & PCN risk predictor

**Functional requirements**
- **F3.1** **Vehicle compliance check:** classify vehicle as compliant / chargeable / unknown from fuel type, Euro standard and exemptions. *Unknown is treated as chargeable (safe side)* until verified.
- **F3.2** **Ledger:** one entry per vehicle per travel day (the daily charge applies once per day), with source (route plan, telematics, manual, ANPR-import), amount, deadline and status (`due`, `paid`, `overdue_pcn_likely`).
- **F3.3** **Payment window logic:** window opens 6 days before and closes 6 days after the travel day **[verify]**; payments recorded outside the window are rejected.
- **F3.4** **Exposure calculator:** for overdue days, show outstanding charges plus PCN at £60 (discount) and £120 (full) **[verify]**.
- **F3.5** **PCN risk predictor (v1, rule-based and transparent):** 0-100 score from unknown compliance, planned zone entry, unpaid status, deadline proximity/closure and prior overdue days; bands *low / medium / high*, each with human-readable factors. **v2 (Phase 3):** gradient-boosted model trained on anonymised ledger outcomes, with the rule-based score kept as an explainable baseline.
- **F3.6** Alerts: push/SMS/email at T-24h before deadline and on route plans that enter the zone unpaid.
- **F3.7** One-tap hand-off to the official GOV.UK payment service with vehicle details pre-copied; user enters the receipt reference.
- **F3.8** Exports: monthly CSV/PDF for accountants.
- **F3.9** PCN intake: user logs a received PCN (number, dates, amount) to track discount deadlines and appeal grounds. The product does not give legal advice.

**Acceptance criteria (examples)**
- Recording the same chargeable vehicle twice on one day creates one ledger entry.
- A payment dated outside the window is rejected with a clear message.
- A compliant or exempt vehicle always scores 0.

### 3.4 Feature F4: SME pool-sharing marketplace for localised drop nodes

**Goal:** turn spare shelf, locker, doorway or loading-bay capacity into shared drop points that reduce failed deliveries and kerb conflict.

**Functional requirements**
- **F4.1** Hosts list drop nodes (location, slots/day, price/slot, access hours, accepted parcel sizes).
- **F4.2** Bookers reserve slots by day; overbooking is prevented.
- **F4.3** Transparent quote before confirmation: gross, platform commission (assumed 10%), host payout.
- **F4.4** Pool cost-split: host's daily takings apportioned across booked businesses by slots used.
- **F4.5** Trust: identity verification, ratings, parcel-condition photos, liability/insurance terms, dispute workflow.
- **F4.6** Nodes appear as selectable drop points inside the routing engine, so a route can terminate at a node rather than the final door.

### 3.5 System architecture

```
┌──────────────┐   HTTPS    ┌──────────────────────────┐
│ Next.js PWA  │──────────▶│ API gateway (FastAPI)     │
│ (React, TS)  │            │  auth · rate-limit · RBAC │
└──────┬───────┘            └───┬───────────┬───────────┘
       │ WebSocket / SSE        │           │
       ▼                        ▼           ▼
┌──────────────┐   ┌────────────────┐  ┌──────────────────┐
│ Live tracking│   │ Routing service│  │ Compliance svc   │
│ & dispatch   │   │ (state-space   │  │ ledger · PCN risk│
└──────┬───────┘   │ Dijkstra / OR- │  │ · alerts         │
       │           │ Tools VRP)     │  └────────┬─────────┘
       │           └───────┬────────┘           │
       │                   │                    │
       ▼                   ▼                    ▼
┌──────────────────────────────────────────────────────────┐
│ PostgreSQL 16 + PostGIS + pgRouting                       │
│ road_edges · caz_zone · hubs · ledger · bookings          │
└───────▲───────────────────────────────▲─────────────────┘
        │ nightly import                 │ cache / queues
┌───────┴──────────┐              ┌──────┴───────┐
│ Data pipeline    │              │ Redis + job  │
│ OSM · terrain ·  │              │ worker       │
│ Bristol Open Data│              │ (alerts,     │
└──────────────────┘              │ DVLA lookups)│
                                  └──────────────┘
```

**Design principles**
- **Spatial truth lives in PostGIS.** The CAZ polygon is imported from the council's official data; `inside_caz` is *computed*, never hand-drawn.
- **Stateless services** behind the gateway; long jobs on a worker queue.
- **Versioned graph snapshots** so a quoted route can be reproduced later (important for disputes).
- **Multi-tenant by organisation**, with row-level access by role.
- **Privacy by design** (see §3.6).

### 3.6 Non-functional, security and legal requirements
- **UK GDPR / DPA 2018:** vehicle registrations and location trails are personal data in many contexts. Lawful basis documented; data-minimisation; configurable retention (default 12 months for trails, 6 years for financial records); DPIA before launch; DPA with all processors.
- **Location consent:** driver-level notice and opt-in; no covert tracking.
- **Security:** OIDC auth, MFA for owners, encryption in transit and at rest, secrets in a vault, dependency scanning, annual penetration test; audit log for ledger edits.
- **Reliability:** 99.5% API availability target in MVP; daily backups; tested restore.
- **Accessibility:** WCAG 2.2 AA.
- **Payments & marketplace:** use a regulated payment provider (e.g. Stripe Connect or equivalent) for host payouts; the platform never holds funds directly.
- **Disclaimers:** CAZ rules and charges can change; the product shows the source and "last verified" date for every rule, and a feature flag lets operations update rules without a deploy.

---

## 4. Tech Stack Recommendation

### 4.1 Summary
| Layer | Choice | Rationale |
|---|---|---|
| **Web** | Next.js (React + TypeScript), PWA | One codebase for dispatcher console and driver mobile web; SSR for marketing/SEO. |
| **Mobile** | Start as PWA; React Native (Expo) in Phase 3 | Fast MVP; native later for background location and push. |
| **Maps UI** | MapLibre GL JS with OSM-based vector tiles | No per-load licensing; supports gradient shading and zone overlay. |
| **API** | Python 3.12 + FastAPI, Pydantic | Strong geospatial/optimisation ecosystem; typed contracts. |
| **Realtime** | WebSockets/SSE via FastAPI; Redis pub/sub | Live job and hand-off status. |
| **Optimisation** | OR-Tools (VRP, time windows) | Multi-stop sequencing with zone-charge-once logic (custom penalty). |
| **Spatial DB** | PostgreSQL 16 + **PostGIS** + **pgRouting** | Spatial joins for zone containment; SQL-based graph search for MVP. |
| **Routing at scale** | Option: Valhalla/OSRM custom profiles | If pgRouting latency becomes limiting; cost function ports across. |
| **Cache/queue** | Redis; RQ/Celery | Alerts, DVLA lookups, imports. |
| **Node (optional)** | Node.js for webhook gateway/BFF only | Keep one primary backend language to limit complexity. |
| **Infra** | Docker; deploy on a UK/EU region of a major cloud; Terraform; GitHub Actions CI | Data residency, repeatability. |
| **Observability** | OpenTelemetry, Prometheus/Grafana, Sentry | Latency and error budgets. |
| **Payments** | Stripe Connect (or similar) | Marketplace payouts, KYC handled by provider. |

### 4.2 Why Python for the backend (and Node optional)
The routing, optimisation and data-pipeline work is Python-native (OR-Tools, GeoPandas, Shapely, rasterio). A single FastAPI backend avoids a polyglot core. Node.js is acceptable for a thin BFF or webhook layer if the team prefers.

### 4.3 Data sources (all subject to licence and terms review)
| Data | Source | Use |
|---|---|---|
| Road & path network | **OpenStreetMap** (ODbL licence, attribution required) | Graph, bike-only links, one-ways, weight limits. |
| Terrain / elevation | Environment Agency National LIDAR composite DTM or OS Terrain data **[confirm licence]** | Edge elevation and grade. |
| CAZ boundary & rules | **Bristol City Council** pages and **Bristol Open Data** portal; GOV.UK Clean Air Zones pages | `caz_zone` polygon, charges, exemptions. |
| Vehicle data | **DVLA Vehicle Enquiry Service** (fuel, year, Euro status where available) and the GOV.UK vehicle checker | Compliance classification. **[confirm API access and terms]** |
| Payment of charges | GOV.UK "Drive in a Clean Air Zone" service | User-initiated; **no public payment API assumed**. |
| Traffic | Public traffic feeds, then anonymised fleet telemetry | Congestion multipliers. |
| Hub/site candidates | Council and landlord data, field surveys | Hub registry. |

### 4.4 Core data model (see `db/schema.sql`)
`organisations`, `users`, `vehicles`, `caz_zone`, `road_edges` (with `grade_pct` and `inside_caz`), `congestion_profiles`, `hubs`, `handshakes`, `ledger_entries` (unique per vehicle per day), `pcn_events`, `drop_nodes`, `bookings`.

### 4.5 API surface (prototype implements these)
| Endpoint | Purpose |
|---|---|
| `POST /route` | Recommended vs. fastest-ignoring-CAZ route, charge avoided, PCN risk, payment window. |
| `POST /compliance/check` | Compliant / chargeable / unknown and daily charge. |
| `GET /ledger/{reg}` · `POST /ledger/pay` | Entries with status and exposure; record payment. |
| `POST /handshake/plan` · `POST /handshake` · `POST /handshake/{id}/advance` | Plan, create, progress hand-offs. |
| `GET /marketplace/nodes` · `POST /marketplace/nodes/{id}/book` | Browse and book drop nodes. |

---

## 5. Monetisation Strategy & Go-To-Market

### 5.1 Revenue streams (price points are hypotheses to test)
| Tier | Target | Price (hypothesis) | Includes |
|---|---|---|---|
| **Free** | Trials, very light users | £0 | 1 vehicle, compliance check, 5 route plans/week, ledger view. |
| **Solo** | Sole traders (Dan) | £12 / vehicle / month | Unlimited routing, ledger, deadline alerts, PCN tracker, exports. |
| **Fleet** | Couriers (Priya), 3-25 vehicles | £22 / vehicle / month (min £110) | Solo + dispatch console, multi-stop optimisation, reporting, API access. |
| **Pro** | Larger or multi-site fleets | Custom | Fleet + SSO, SLAs, telematics integrations, dedicated onboarding. |
| **Handshake fee** | Senders using hubs | £1.20 / parcel handed over | Hub reservation, proof of hand-over, rider matching. |
| **Marketplace commission** | Drop-node bookings | 10% of booking value | Payments, trust & dispute tooling. |
| **Hub/bike-operator listing** | Operators | Optional £30-£60 / month featured listing | Visibility, analytics. |

**Value test:** Solo pays for itself if it avoids ~1.3 chargeable days or one avoidable PCN per month at the current £9/£60 levels. This is the central claim to validate in discovery.

### 5.2 Unit-economics hypotheses (to validate)
- Blended ARPU target £20/vehicle/month; gross margin ≥ 75% (hosting, maps, SMS).
- CAC target < £120 via partnerships and community channels; payback < 6 months.
- Handshake and marketplace revenue is upside, not required for break-even in year 1.

### 5.3 Go-to-market, phased by geography and segment
**Phase A: Central Bristol beachhead (months 0-6)**
- Focus on BS1/BS2/BS8 (inside and adjoining the zone) and sole traders plus small couriers.
- 20-30 design-partner businesses on free pilot; weekly feedback; collect "money saved" case studies.
- Channels: trade groups and local business networks, Bristol Chamber/Business Improvement District-type bodies, electrician/plumber communities, local courier co-operatives, bike-courier collectives, van-leasing and insurance partners.

**Phase B: Inner-ring expansion (months 6-12)**
- Add Clifton, Redland, Bedminster, Old Market, Totterdown (hill-heavy residential delivery).
- Launch hub handshake with 1-2 hubs and 1-2 bike operators; open the marketplace to invited hosts.

**Phase C: Greater Bristol and replication (year 2+)**
- Greater Bristol/South Gloucestershire corridors; then other UK Clean Air Zone cities where the same compliance engine applies (rules modelled as data, not code).

### 5.4 Positioning and differentiation
- vs. generic route planners: hill-, mode- and CAZ-aware, with a compliance ledger.
- vs. enterprise fleet suites: priced and designed for 1-25 vehicles.
- vs. doing nothing: tangible, monthly "£ saved / PCNs avoided" report.

### 5.5 Marketing and sales motions
- Content: "Bristol CAZ explained for tradespeople", "Hill-aware delivery times in Clifton".
- Product-led growth: free compliance check and a shareable "Is my van chargeable?" tool.
- Referral credit: one free month per referred paying vehicle.
- Partnerships: council economic-development and sustainability teams, cargo-bike operators, depot landlords.

### 5.6 Go-to-market risks
| Risk | Mitigation |
|---|---|
| Customers believe they can "just pay the £9" | Lead with total-cost savings, deadline alerts and time savings, not only fee avoidance. |
| Chargeable-van share falls as fleets renew | Pivot emphasis to hill/hub/marketplace value; modular pricing. |
| CAZ policy changes | Rules as data; monitoring; fast update process. |
| Two-sided marketplace cold start | Seed supply with 10-15 curated hosts; subsidise first bookings. |

---

## 6. MVP Roadmap (3 Phases)

Assumes a core team of ~6: product manager, 2 full-stack engineers, 1 data/GIS engineer, 1 designer (part-time), 1 QA/DevOps (part-time). Durations are planning estimates.

### Phase 1: Discovery & Data Mapping (Weeks 1-8)
**Objectives:** prove the problem and build the spatial foundation.
- **Customer discovery:** 30+ interviews across the three personas; collect real week-in-the-life routes; test willingness to pay for Solo.
- **Regulatory review:** confirm current charges, exemptions, financial-support schemes, payment window and PCN terms with Bristol City Council/GOV.UK; document sources and verification dates.
- **Data pipeline:** import OSM Bristol extract with osm2pgrouting; import official CAZ polygon; attach terrain elevation and compute `grade_pct`; compute `inside_caz`.
- **Validation:** spot-check 200 random edges against known gradients and boundary crossings; produce a data-quality report.
- **Legal/compliance:** DPIA draft, privacy notice, terms of service, DVLA access application.
- **Design:** clickable prototype for dispatch console and driver app.
- **Hub scouting:** shortlist 3-5 depot candidates (including St Philip's Marsh area) and 2-3 bike operators.

**Exit criteria:** ≥ 10 design partners signed; data-quality report passed; documented rule sources; decision on hub sites; go/no-go gate.

### Phase 2: Core Routing & CAZ Ledger MVP (Weeks 9-20)
**Objectives:** ship the product that saves money on day one.
- **F1 (core):** single-route and multi-stop routing for van profile; CAZ-once cost logic; comparison view; explanations.
- **F3 (core):** vehicle compliance check; ledger; payment window; exposure; rule-based PCN risk; alerts; GOV.UK hand-off; CSV export.
- **Apps:** Next.js PWA with map, day plan, ledger, alerts; basic org/user management; Stripe subscriptions for Solo/Fleet.
- **Quality:** automated tests on the cost function and ledger rules (the prototype already contains these); load test to p95 < 1.5 s; security review.
- **Pilot:** launch to the design partners; weekly metrics review.

**Exit criteria:** ≥ 60 weekly active vehicles; ≥ 25 paying vehicles; measurable PCN or charge reduction vs. baseline; p95 latency met; no critical security findings.

### Phase 3: Cargo-Bike & Hub Integration (Weeks 21-36)
**Objectives:** unlock the hill and last-mile advantage and the network effects.
- **F1 (extension):** cargo-bike profile with gradient limits and payload; congestion profiles from telemetry; OR-Tools multi-stop with time windows.
- **F2:** hub registry, handshake planner, capacity reservation, state machine, QR hand-over proof, rider matching, platform fee billing.
- **F4:** drop-node listing and booking, quotes and commission, payouts, ratings; nodes selectable in routing.
- **F3 (extension):** PCN risk model v2 trained on ledger outcomes.
- **Mobile:** React Native driver/rider app with background location and push.
- **Ops:** pilot 1-2 hubs and 1-2 bike operators; insurance and liability terms finalised.

**Exit criteria:** ≥ 500 completed handshakes; ≥ 85% on-time; ≥ 10 active drop nodes with repeat bookings; unit economics review; decision on Greater Bristol expansion.

### Roadmap summary
| Phase | Weeks | Deliverable | Key gate |
|---|---|---|---|
| 1. Discovery & data mapping | 1-8 | Validated data layer, partners, rules register | Go/no-go on build |
| 2. Core routing & CAZ ledger | 9-20 | Paying-customer MVP | Paying vehicles + measurable savings |
| 3. Cargo-bike & hub integration | 21-36 | Handshake + marketplace | Handshake volume + on-time rate |

---

## 7. Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|:--:|:--:|---|
| Regulatory change (CAZ rules, charges, boundary) | Med | High | Rules-as-data, source and verification date on every rule, monitoring, ops-editable config. |
| Inaccurate terrain or boundary data | Med | High | Official sources only, automated data-quality tests, user "report a problem" button. |
| Over-reliance on compliance advice | Med | High | Clear disclaimers; user pays via official service; versioned snapshots for audit. |
| DVLA/GOV.UK data access limits | Med | Med | Manual entry fallback; unknown = chargeable until verified. |
| Hub site availability / cost | High | Med | Pilot with 1-2 hubs; flexible leases; partner with existing depots. |
| Marketplace liability for lost or damaged goods | Med | High | Insurance, photo proof, clear terms, dispute process. |
| Privacy breach on location data | Low | High | Minimisation, short retention, encryption, DPIA, access logs. |
| Slow adoption by sole traders | Med | Med | Free compliance checker, WhatsApp/SMS-first alerts, measurable savings reports. |

---

## 8. Open Questions for Stakeholders
1. Which data licences (terrain, vehicle data) are acceptable commercially, and what is the budget?
2. Is a partnership with Bristol City Council or a Business Improvement District feasible for data and distribution?
3. Who owns hub operations: the platform, a partner, or the hub landlord?
4. Insurance model for goods in transit and marketplace storage?
5. Which exemption and financial-support schemes currently apply to local businesses, and can the ledger model them? **[verify with council]**

## 9. Appendix
### A. Reference constants (configurable; **[verify]** before launch)
| Item | Value used in prototype |
|---|---|
| Zone type / start | Class D, 28 Nov 2022 |
| Daily charge (light) | £9 |
| Daily charge (heavy) | £100 |
| Min standards | Petrol Euro 4, diesel Euro 6 |
| Payment window | 6 days before to 6 days after travel day |
| PCN | £120; £60 if paid within 14 days of service; 28 days to pay; charge payable additionally |

### B. Prototype note
The repository includes a working backend prototype (routing engine, ledger, hubs, marketplace, API, 8 automated tests) and a small Next.js demo. It runs on an **illustrative seed network**: place coordinates, elevations and zone flags are approximations to demonstrate behaviour, **not survey or official data**. Production replaces the seed with the OSM, terrain and official-boundary pipeline described above.

### C. Sources checked (Oct 2026)
- Bristol City Council: Clean Air Zone pages (charges, PCN payment) and the GOV.UK Clean Air Zones service.
- Traffic Penalty Tribunal: Bristol CAZ PCN grounds of appeal.

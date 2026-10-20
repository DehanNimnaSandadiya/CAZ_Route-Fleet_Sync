"use client";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const NODES = ["M32J", "MARSH", "TMEADS", "OLDMKT", "CENTRE", "QSQ", "PARKST", "PARKTOP", "WHITELADIES", "CLIFTONV", "HOTWELLS", "A38N"];

type PathNode = { id: string; name: string; elev_m: number; in_caz: boolean };
type Leg = { found: boolean; path: PathNode[]; duration_min: number; distance_m: number; ascent_m: number; caz_charge_gbp: number };
type Result = {
  recommended: Leg; fastest_ignoring_caz: Leg; charge_avoided_gbp: number;
  pcn_risk: { score: number; level: string; factors: string[] };
  payment_window: { opens: string; closes: string };
};

const panel = {
  background: "#ffffff",
  border: "1px solid #d7dfe3",
  borderRadius: 10,
  padding: 20,
  boxShadow: "none"
} as const;

const fieldStyle = {
  width: "100%",
  border: "1px solid #c5ced4",
  borderRadius: 8,
  padding: "10px 12px",
  background: "#f5f6f5",
  fontSize: 14,
  color: "#17272a",
  boxSizing: "border-box" as const,
};

export default function Home() {
  const [origin, setOrigin] = useState("M32J");
  const [destination, setDestination] = useState("CLIFTONV");
  const [reg, setReg] = useState("AB12CDE");
  const [fuel, setFuel] = useState("diesel");
  const [euro, setEuro] = useState(5);
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10));
  const [res, setRes] = useState<Result | null>(null);
  const [err, setErr] = useState("");

  async function plan() {
    setErr("");
    setRes(null);
    try {
      const r = await fetch(`${API}/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          origin,
          destination,
          travel_day: day,
          vehicle: { reg, vehicle_class: "van", fuel, euro_standard: euro },
        }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? `HTTP ${r.status}`);
      setRes(await r.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    }
  }

  return (
    <main style={{ minHeight: "100vh", background: "#f2f4f3", padding: "28px 20px" }}>
      <div style={{ maxWidth: 1160, margin: "0 auto" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
          <div>
            <div style={{ color: "#58666c", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Bristol regional transport compliance
            </div>
            <h1 style={{ margin: "8px 0 0", fontSize: "clamp(2rem, 3vw, 2.6rem)", color: "#1a2427", lineHeight: 1.15, fontWeight: 700 }}>
              CAZ Route &amp; Fleet Sync
            </h1>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <span style={{ background: "#edf1f3", color: "#32434c", border: "1px solid #d7dde0", borderRadius: 999, padding: "7px 10px", fontSize: 11, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Operational
            </span>
            <span style={{ background: "#f4f5f5", color: "#4d5d66", border: "1px solid #dfe4e6", borderRadius: 999, padding: "7px 10px", fontSize: 11, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Prototype
            </span>
          </div>
        </header>

        <section style={{ ...panel, marginBottom: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
            <div>
              <h2 style={{ margin: 0, fontSize: 22, color: "#1b2428" }}>Compliance routing</h2>
              <p style={{ margin: "6px 0 0", color: "#51636b" }}>
                Route planning and Clean Air Zone compliance assessment for Bristol fleet movements.
              </p>
            </div>
            <div style={{ borderLeft: "3px solid #dfe4e7", paddingLeft: 12, color: "#53656d", fontSize: 13 }}>
              Check current charges at gov.uk/clean-air-zones.
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 18 }}>
            <label style={{ display: "grid", gap: 8, color: "#27353c", fontWeight: 600 }}>
              Origin
              <select value={origin} onChange={(e) => setOrigin(e.target.value)} style={fieldStyle}>
                {NODES.map((n) => <option key={n}>{n}</option>)}
              </select>
            </label>

            <label style={{ display: "grid", gap: 8, color: "#27353c", fontWeight: 600 }}>
              Destination
              <select value={destination} onChange={(e) => setDestination(e.target.value)} style={fieldStyle}>
                {NODES.map((n) => <option key={n}>{n}</option>)}
              </select>
            </label>

            <label style={{ display: "grid", gap: 8, color: "#27353c", fontWeight: 600 }}>
              Vehicle registration
              <input value={reg} onChange={(e) => setReg(e.target.value)} style={fieldStyle} />
            </label>

            <label style={{ display: "grid", gap: 8, color: "#27353c", fontWeight: 600 }}>
              Fuel type
              <select value={fuel} onChange={(e) => setFuel(e.target.value)} style={fieldStyle}>
                <option value="diesel">Diesel</option>
                <option value="petrol">Petrol</option>
                <option value="electric">Electric</option>
              </select>
            </label>

            <label style={{ display: "grid", gap: 8, color: "#27353c", fontWeight: 600 }}>
              Euro standard
              <input type="number" min={1} max={7} value={euro} onChange={(e) => setEuro(Number(e.target.value))} style={fieldStyle} />
            </label>

            <label style={{ display: "grid", gap: 8, color: "#27353c", fontWeight: 600 }}>
              Travel date
              <input type="date" value={day} onChange={(e) => setDay(e.target.value)} style={fieldStyle} />
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 22, flexWrap: "wrap", gap: 12 }}>
            <button type="button" onClick={plan} style={{
              background: "#1f3138",
              color: "#ffffff",
              border: "none",
              borderRadius: 8,
              padding: "11px 18px",
              fontSize: 15,
              fontWeight: 700,
              cursor: "pointer"
            }}>
              Plan route
            </button>
            <button type="button" onClick={() => setRes(null)} style={{
              background: "#eef2f4",
              color: "#20333b",
              border: "1px solid #d7dde0",
              borderRadius: 8,
              padding: "11px 18px",
              fontSize: 15,
              fontWeight: 700,
              cursor: "pointer"
            }}>
              Clear
            </button>
          </div>
        </section>

        {err && (
          <div style={{ ...panel, borderColor: "#e7c6c5", background: "#fff8f8", color: "#7e2a2b", marginBottom: 20 }} role="alert">
            <strong>System alert:</strong> {err}
          </div>
        )}

        {!res && !err && (
          <section style={{ ...panel, color: "#465a61", lineHeight: 1.7 }}>
            <strong>Ready for assessment.</strong> Select a route and vehicle profile to generate a compliance outcome.
          </section>
        )}

        {res && (
          <>
            <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 18, marginBottom: 20 }}>
              <div style={{ ...panel, background: "#f5f7f7" }}>
                <div style={{ color: "#4d5e68", fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                  PCN risk
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#1d2d31", marginTop: 8 }}>{res.pcn_risk.level.toUpperCase()}</div>
                <div style={{ color: "#44606a", marginTop: 8 }}>{res.pcn_risk.score}/100 score</div>
              </div>

              <div style={{ ...panel, background: "#f7f7f5" }}>
                <div style={{ color: "#5d666d", fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                  Charge avoidance
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#1d2d31", marginTop: 8 }}>£{res.charge_avoided_gbp.toFixed(2)}</div>
                <div style={{ color: "#53656e", marginTop: 8 }}>Compared with fastest unrestricted route</div>
              </div>

              <div style={{ ...panel, background: "#f5f2eb" }}>
                <div style={{ color: "#6c5d38", fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                  Payment window
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#332d22", marginTop: 8 }}>{res.payment_window.opens}</div>
                <div style={{ color: "#5c4d35", marginTop: 8 }}>to {res.payment_window.closes}</div>
              </div>
            </section>

            <section style={{ ...panel, marginBottom: 20 }}>
              <h3 style={{ marginTop: 0, marginBottom: 12, color: "#1d2d31" }}>Risk factors</h3>
              <ul style={{ margin: 0, paddingLeft: 18, color: "#31454d", lineHeight: 1.8 }}>
                {res.pcn_risk.factors.map((factor) => <li key={factor}>{factor}</li>)}
              </ul>
            </section>

          </>
        )}
      </div>
    </main>
  );
}

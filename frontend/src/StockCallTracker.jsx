import { useState, useEffect, useCallback, useMemo } from "react";

const SAMPLE_BROKERS = [
  { id: 1, name: "TradeBulls Securities", category: "Full Service", contact: "info@tradebulls.com", source: "WhatsApp", score: 78, totalCalls: 45, wins: 35 },
  { id: 2, name: "HDFC Securities", category: "Bank Broker", contact: "hdfc@securities.in", source: "Email", score: 82, totalCalls: 60, wins: 49 },
  { id: 3, name: "Angel One Signals", category: "Discount Broker", contact: "signals@angelone.in", source: "Telegram", score: 71, totalCalls: 38, wins: 27 },
  { id: 4, name: "Zerodha Varsity", category: "Discount Broker", contact: "varsity@zerodha.com", source: "Telegram", score: 88, totalCalls: 52, wins: 46 },
  { id: 5, name: "Motilal Oswal", category: "Full Service", contact: "research@motilaloswal.com", source: "WhatsApp", score: 75, totalCalls: 41, wins: 31 },
];

const SAMPLE_CALLS = [
  { id: 1, date: "2025-05-01", time: "09:32", broker: "TradeBulls Securities", stock: "TATASTEEL", exchange: "NSE", action: "BUY", cmp: 202, entry: 202, targets: [236], stoploss: 185, support: 211, resistance: 240, duration: "2-3 Days", callType: "Swing", status: "Target Hit", originalMsg: "TATA STEEL\nCMP 202\nTARGET 236\nSUPPORT 211\nDURATION 2-3 DAYS", pnlPct: 16.8 },
  { id: 2, date: "2025-05-02", time: "10:15", broker: "HDFC Securities", stock: "INFY", exchange: "NSE", action: "BUY", cmp: 1780, entry: 1780, targets: [1820], stoploss: 1710, support: 1750, resistance: 1850, duration: "1 Week", callType: "Swing", status: "Pending", originalMsg: "ACCUMULATE INFY\nTARGET 1820\nSL 1710\nTIME 1 WEEK", pnlPct: null },
  { id: 3, date: "2025-05-02", time: "11:05", broker: "Angel One Signals", stock: "RELIANCE", exchange: "NSE", action: "BUY", cmp: 1445, entry: 1450, targets: [1510, 1540], stoploss: 1420, support: 1430, resistance: 1560, duration: "Intraday", callType: "Intraday", status: "Partial Hit", originalMsg: "BUY RELIANCE ABOVE 1450\nTARGET 1510 / 1540\nSTOPLOSS 1420\nINTRADAY", pnlPct: 4.1 },
  { id: 4, date: "2025-05-03", time: "09:50", broker: "Zerodha Varsity", stock: "HDFCBANK", exchange: "NSE", action: "BUY", cmp: 1625, entry: 1625, targets: [1680], stoploss: 1590, support: 1610, resistance: 1700, duration: "3-5 Days", callType: "Swing", status: "Target Hit", originalMsg: "BUY HDFCBANK CMP 1625\nTGT 1680\nSL 1590", pnlPct: 3.4 },
  { id: 5, date: "2025-05-05", time: "10:30", broker: "Motilal Oswal", stock: "TCS", exchange: "NSE", action: "SELL", cmp: 3950, entry: 3950, targets: [3880], stoploss: 4010, support: 3870, resistance: 4020, duration: "2 Days", callType: "Swing", status: "SL Hit", originalMsg: "SELL TCS @3950\nTARGET 3880\nSL 4010", pnlPct: -1.5 },
  { id: 6, date: "2025-05-06", time: "09:15", broker: "TradeBulls Securities", stock: "SBIN", exchange: "NSE", action: "BUY", cmp: 798, entry: 800, targets: [840, 860], stoploss: 775, support: 790, resistance: 850, duration: "1 Week", callType: "Swing", status: "Target Hit", originalMsg: "BUY SBI\nCMP 798\nTGT1 840 TGT2 860\nSL 775", pnlPct: 5.0 },
  { id: 7, date: "2025-05-07", time: "11:20", broker: "HDFC Securities", stock: "WIPRO", exchange: "NSE", action: "BUY", cmp: 468, entry: 470, targets: [495], stoploss: 455, support: 460, resistance: 500, duration: "5-7 Days", callType: "Swing", status: "Expired", originalMsg: "WIPRO BUY ABOVE 470\nTARGET 495\nSL 455\n5-7 DAYS", pnlPct: -0.4 },
  { id: 8, date: "2025-05-08", time: "10:00", broker: "Zerodha Varsity", stock: "ICICIBANK", exchange: "NSE", action: "BUY", cmp: 1102, entry: 1105, targets: [1145], stoploss: 1075, support: 1090, resistance: 1160, duration: "Intraday", callType: "Intraday", status: "Target Hit", originalMsg: "ICICI BANK BUY 1105\nTGT 1145\nSL 1075\nINTRADAY", pnlPct: 3.6 },
  { id: 9, date: "2025-05-09", time: "09:45", broker: "Angel One Signals", stock: "BAJFINANCE", exchange: "NSE", action: "BUY", cmp: 7200, entry: 7220, targets: [7450], stoploss: 7050, support: 7100, resistance: 7500, duration: "3 Days", callType: "Swing", status: "SL Hit", originalMsg: "BUY BAJFINANCE\nCMP 7200 ENTRY 7220\nTARGET 7450\nSL 7050", pnlPct: -2.4 },
  { id: 10, date: "2025-05-10", time: "10:45", broker: "Motilal Oswal", stock: "MARUTI", exchange: "NSE", action: "BUY", cmp: 12400, entry: 12400, targets: [12800], stoploss: 12100, support: 12200, resistance: 13000, duration: "1-2 Weeks", callType: "Positional", status: "Pending", originalMsg: "MARUTI ACCUMULATE\nTGT 12800\nSL 12100\n1-2 WEEKS", pnlPct: null },
];

function parseMessage(msg) {
  const upper = msg.toUpperCase();
  const result = { stock: "", action: "BUY", cmp: null, entry: null, targets: [], stoploss: null, duration: "", callType: "Swing" };
  const stockPat = /\b([A-Z]{2,10}(?:STEEL|BANK|FIN|LTD|TECH|AUTO)?)\b/g;
  const keywords = ["BUY","SELL","CMP","TARGET","TGT","STOPLOSS","SL","SUPPORT","RESISTANCE","INTRADAY","SWING","WEEK","DAY","DURATION","ACCUMULATE","ENTRY","ABOVE","BELOW"];
  const stocks = [];
  let m;
  while ((m = stockPat.exec(upper)) !== null) {
    if (!keywords.includes(m[1]) && m[1].length >= 3) stocks.push(m[1]);
  }
  result.stock = stocks[0] || "";
  if (/\bSELL\b/.test(upper)) result.action = "SELL";
  const cmpMatch = upper.match(/CMP\s*[:\-]?\s*(\d+(?:\.\d+)?)/);
  if (cmpMatch) result.cmp = parseFloat(cmpMatch[1]);
  const entryMatch = upper.match(/(?:ENTRY|ABOVE|BUY\s+\w+\s+@?)\s*(\d+(?:\.\d+)?)/);
  if (entryMatch) result.entry = parseFloat(entryMatch[1]);
  const tgtMatches = [...upper.matchAll(/(?:TARGET|TGT)\s*\d?\s*[:\-]?\s*(\d+(?:\.\d+)?)/g)];
  result.targets = tgtMatches.map(x => parseFloat(x[1]));
  if (!result.targets.length) {
    const slashTargets = upper.match(/(?:TARGET|TGT)[^0-9]*(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/);
    if (slashTargets) result.targets = [parseFloat(slashTargets[1]), parseFloat(slashTargets[2])];
  }
  const slMatch = upper.match(/(?:STOPLOSS|STOP LOSS|SL)\s*[:\-]?\s*(\d+(?:\.\d+)?)/);
  if (slMatch) result.stoploss = parseFloat(slMatch[1]);
  if (/\bINTRADAY\b/.test(upper)) result.callType = "Intraday";
  else if (/\bLONG\s*TERM\b/.test(upper)) result.callType = "Long Term";
  else if (/\bPOSITIONAL\b/.test(upper)) result.callType = "Positional";
  const durMatch = upper.match(/(\d+[-–]\d+\s*(?:DAY|WEEK|MONTH)S?|\d+\s*(?:DAY|WEEK|MONTH)S?)/);
  if (durMatch) result.duration = durMatch[0];
  else if (/INTRADAY/.test(upper)) result.duration = "Intraday";
  return result;
}

const STATUS_COLORS = { "Target Hit": "#22c55e", "Partial Hit": "#f59e0b", "SL Hit": "#ef4444", "Pending": "#3b82f6", "Expired": "#6b7280" };
const STATUS_BG = { "Target Hit": "#dcfce7", "Partial Hit": "#fef3c7", "SL Hit": "#fee2e2", "Pending": "#dbeafe", "Expired": "#f3f4f6" };

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [calls, setCalls] = useState(SAMPLE_CALLS);
  const [brokers, setBrokers] = useState(SAMPLE_BROKERS);
  const [filters, setFilters] = useState({ broker: "All", callType: "All", status: "All", search: "" });
  const [parseMsg, setParseMsg] = useState("");
  const [parsed, setParsed] = useState(null);
  const [showAddCall, setShowAddCall] = useState(false);
  const [showAddBroker, setShowAddBroker] = useState(false);
  const [newCall, setNewCall] = useState({ date: new Date().toISOString().split("T")[0], time: "10:00", broker: "", stock: "", exchange: "NSE", action: "BUY", cmp: "", entry: "", target1: "", target2: "", stoploss: "", support: "", resistance: "", duration: "", callType: "Swing", originalMsg: "" });
  const [newBroker, setNewBroker] = useState({ name: "", category: "Discount Broker", contact: "", source: "Telegram", score: 70 });
  const [toast, setToast] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  const showToast = (msg, type = "success") => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const filteredCalls = useMemo(() => calls.filter(c => {
    if (filters.broker !== "All" && c.broker !== filters.broker) return false;
    if (filters.callType !== "All" && c.callType !== filters.callType) return false;
    if (filters.status !== "All" && c.status !== filters.status) return false;
    if (filters.search && !c.stock.toLowerCase().includes(filters.search.toLowerCase()) && !c.broker.toLowerCase().includes(filters.search.toLowerCase())) return false;
    return true;
  }), [calls, filters]);

  const stats = useMemo(() => {
    const total = calls.length;
    const hits = calls.filter(c => c.status === "Target Hit").length;
    const partial = calls.filter(c => c.status === "Partial Hit").length;
    const sl = calls.filter(c => c.status === "SL Hit").length;
    const pending = calls.filter(c => c.status === "Pending").length;
    const accuracy = total ? Math.round(((hits + partial) / total) * 100) : 0;
    const avgReturn = calls.filter(c => c.pnlPct !== null).reduce((a, c) => a + c.pnlPct, 0) / (calls.filter(c => c.pnlPct !== null).length || 1);
    return { total, hits, partial, sl, pending, accuracy, avgReturn: avgReturn.toFixed(1) };
  }, [calls]);

  const brokerStats = useMemo(() => brokers.map(b => {
    const bc = calls.filter(c => c.broker === b.name);
    const wins = bc.filter(c => c.status === "Target Hit" || c.status === "Partial Hit").length;
    return { ...b, callCount: bc.length, winRate: bc.length ? Math.round((wins / bc.length) * 100) : 0 };
  }).sort((a, b) => b.score - a.score), [brokers, calls]);

  const handleParseMsg = () => { if (parseMsg.trim()) { setParsed(parseMessage(parseMsg)); showToast("Message parsed successfully"); } };
  const handleUseParsed = () => {
    if (!parsed) return;
    setNewCall(prev => ({ ...prev, stock: parsed.stock, action: parsed.action, cmp: parsed.cmp || "", entry: parsed.entry || "", target1: parsed.targets[0] || "", target2: parsed.targets[1] || "", stoploss: parsed.stoploss || "", duration: parsed.duration, callType: parsed.callType, originalMsg: parseMsg }));
    setShowAddCall(true);
    setParsed(null);
    setParseMsg("");
  };

  const handleAddCall = () => {
    if (!newCall.stock || !newCall.broker) { showToast("Stock name and broker are required", "error"); return; }
    const c = { id: calls.length + 1, ...newCall, cmp: parseFloat(newCall.cmp) || 0, entry: parseFloat(newCall.entry) || 0, targets: [newCall.target1, newCall.target2].filter(Boolean).map(Number), stoploss: parseFloat(newCall.stoploss) || 0, support: parseFloat(newCall.support) || 0, resistance: parseFloat(newCall.resistance) || 0, status: "Pending", pnlPct: null };
    setCalls(prev => [c, ...prev]);
    setShowAddCall(false);
    showToast("Call added successfully");
  };

  const handleAddBroker = () => {
    if (!newBroker.name) { showToast("Broker name is required", "error"); return; }
    setBrokers(prev => [...prev, { id: brokers.length + 1, ...newBroker, totalCalls: 0, wins: 0 }]);
    setShowAddBroker(false);
    showToast("Broker added");
  };

  const updateStatus = (id, status) => {
    setCalls(prev => prev.map(c => c.id === id ? { ...c, status, pnlPct: status === "Target Hit" ? parseFloat(((c.targets[0] - c.entry) / c.entry * 100).toFixed(1)) : status === "SL Hit" ? parseFloat(((c.stoploss - c.entry) / c.entry * 100).toFixed(1)) : c.pnlPct } : c));
    showToast(`Status updated to ${status}`);
  };

  const navItems = [
    { id: "dashboard", icon: "ti-dashboard", label: "Dashboard" },
    { id: "calls", icon: "ti-list-check", label: "Calls" },
    { id: "parse", icon: "ti-wand", label: "Parser" },
    { id: "brokers", icon: "ti-users", label: "Brokers" },
    { id: "analytics", icon: "ti-chart-bar", label: "Analytics" },
  ];

  return (
    <div style={{ fontFamily: "'DM Sans', 'Segoe UI', sans-serif", background: "var(--color-background-tertiary)", minHeight: "100vh", color: "var(--color-text-primary)" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />

      {toast && (
        <div style={{ position: "fixed", top: 16, right: 16, zIndex: 9999, background: toast.type === "error" ? "#fee2e2" : "#dcfce7", color: toast.type === "error" ? "#991b1b" : "#166534", padding: "10px 18px", borderRadius: 10, fontSize: 13, fontWeight: 500, border: `1px solid ${toast.type === "error" ? "#fca5a5" : "#86efac"}`, boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}>
          {toast.msg}
        </div>
      )}

      <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
        {/* Sidebar */}
        <div style={{ width: 220, background: "var(--color-background-primary)", borderRight: "0.5px solid var(--color-border-tertiary)", display: "flex", flexDirection: "column", flexShrink: 0 }}>
          <div style={{ padding: "20px 16px 12px", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <i className="ti ti-trending-up" style={{ color: "#22c55e", fontSize: 16 }}></i>
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, letterSpacing: "-0.01em" }}>StockCall</div>
                <div style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>Tracker Pro</div>
              </div>
            </div>
          </div>
          <nav style={{ padding: "8px 8px", flex: 1 }}>
            {navItems.map(n => (
              <button key={n.id} onClick={() => setPage(n.id)} style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 8, border: "none", cursor: "pointer", background: page === n.id ? "#f0fdf4" : "transparent", color: page === n.id ? "#166534" : "var(--color-text-secondary)", fontWeight: page === n.id ? 500 : 400, fontSize: 13, marginBottom: 2, transition: "all 0.15s" }}>
                <i className={`ti ${n.icon}`} style={{ fontSize: 16 }}></i>
                {n.label}
              </button>
            ))}
          </nav>
          <div style={{ padding: "12px 16px", borderTop: "0.5px solid var(--color-border-tertiary)" }}>
            <div style={{ background: "var(--color-background-secondary)", borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 4 }}>Overall Accuracy</div>
              <div style={{ fontSize: 22, fontWeight: 600, color: "#166534" }}>{stats.accuracy}%</div>
              <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{stats.total} calls tracked</div>
            </div>
          </div>
        </div>

        {/* Main */}
        <div style={{ flex: 1, overflow: "auto", padding: "0" }}>
          {page === "dashboard" && <DashboardPage stats={stats} calls={calls} brokerStats={brokerStats} setPage={setPage} />}
          {page === "calls" && <CallsPage calls={filteredCalls} allCalls={calls} brokers={brokers} filters={filters} setFilters={setFilters} updateStatus={updateStatus} showAddCall={showAddCall} setShowAddCall={setShowAddCall} newCall={newCall} setNewCall={setNewCall} handleAddCall={handleAddCall} />}
          {page === "parse" && <ParsePage parseMsg={parseMsg} setParseMsg={setParseMsg} parsed={parsed} handleParseMsg={handleParseMsg} handleUseParsed={handleUseParsed} />}
          {page === "brokers" && <BrokersPage brokerStats={brokerStats} showAddBroker={showAddBroker} setShowAddBroker={setShowAddBroker} newBroker={newBroker} setNewBroker={setNewBroker} handleAddBroker={handleAddBroker} calls={calls} />}
          {page === "analytics" && <AnalyticsPage calls={calls} brokerStats={brokerStats} stats={stats} activeTab={activeTab} setActiveTab={setActiveTab} />}
        </div>
      </div>
    </div>
  );
}

function DashboardPage({ stats, calls, brokerStats, setPage }) {
  const recent = calls.slice(0, 5);
  const byType = ["Intraday", "Swing", "Positional", "Long Term"].map(t => ({ type: t, count: calls.filter(c => c.callType === t).length }));

  return (
    <div style={{ padding: "24px 28px" }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Dashboard</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>Overview of all tracked stock recommendations</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Total Calls", value: stats.total, icon: "ti-stack", color: "#3b82f6", bg: "#dbeafe" },
          { label: "Target Hit", value: stats.hits, icon: "ti-target", color: "#22c55e", bg: "#dcfce7" },
          { label: "SL Hit", value: stats.sl, icon: "ti-shield-x", color: "#ef4444", bg: "#fee2e2" },
          { label: "Accuracy", value: stats.accuracy + "%", icon: "ti-chart-pie", color: "#8b5cf6", bg: "#ede9fe" },
          { label: "Avg Return", value: stats.avgReturn + "%", icon: "ti-trending-up", color: "#f59e0b", bg: "#fef3c7" },
        ].map(s => (
          <div key={s.label} style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "14px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{s.label}</span>
              <div style={{ width: 28, height: 28, borderRadius: 7, background: s.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <i className={`ti ${s.icon}`} style={{ fontSize: 14, color: s.color }}></i>
              </div>
            </div>
            <div style={{ fontSize: 24, fontWeight: 600 }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "16px 20px" }}>
          <h3 style={{ fontSize: 14, fontWeight: 500, margin: "0 0 14px", display: "flex", alignItems: "center", gap: 6 }}>
            <i className="ti ti-list-check" style={{ fontSize: 15 }}></i> Recent Calls
          </h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead><tr>{["Stock", "Broker", "Type", "Status"].map(h => <th key={h} style={{ textAlign: "left", padding: "4px 6px", color: "var(--color-text-secondary)", fontWeight: 500, borderBottom: "0.5px solid var(--color-border-tertiary)" }}>{h}</th>)}</tr></thead>
            <tbody>
              {recent.map(c => (
                <tr key={c.id}>
                  <td style={{ padding: "6px 6px", fontWeight: 500, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{c.stock}</td>
                  <td style={{ padding: "6px 6px", color: "var(--color-text-secondary)", fontSize: 11 }}>{c.broker.split(" ")[0]}</td>
                  <td style={{ padding: "6px 6px" }}><span style={{ background: "#f3f4f6", color: "#374151", fontSize: 10, padding: "2px 6px", borderRadius: 4 }}>{c.callType}</span></td>
                  <td style={{ padding: "6px 6px" }}><span style={{ background: STATUS_BG[c.status], color: STATUS_COLORS[c.status], fontSize: 10, padding: "2px 7px", borderRadius: 4, fontWeight: 500 }}>{c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <button onClick={() => setPage("calls")} style={{ marginTop: 12, fontSize: 12, color: "#3b82f6", background: "none", border: "none", cursor: "pointer", padding: 0 }}>View all calls →</button>
        </div>

        <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "16px 20px" }}>
          <h3 style={{ fontSize: 14, fontWeight: 500, margin: "0 0 14px", display: "flex", alignItems: "center", gap: 6 }}>
            <i className="ti ti-trophy" style={{ fontSize: 15 }}></i> Top Brokers
          </h3>
          {brokerStats.slice(0, 5).map((b, i) => (
            <div key={b.id} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{ width: 22, height: 22, borderRadius: "50%", background: i === 0 ? "#fef3c7" : "var(--color-background-secondary)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 600, color: i === 0 ? "#92400e" : "var(--color-text-secondary)" }}>{i + 1}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 500 }}>{b.name}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
                  <div style={{ height: 4, borderRadius: 2, background: "#dcfce7", flex: 1, overflow: "hidden" }}>
                    <div style={{ height: "100%", background: "#22c55e", width: b.score + "%" }}></div>
                  </div>
                  <span style={{ fontSize: 11, color: "var(--color-text-secondary)", minWidth: 28 }}>{b.score}%</span>
                </div>
              </div>
              <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{b.callCount} calls</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {byType.map(t => (
          <div key={t.type} style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "14px 16px", textAlign: "center" }}>
            <div style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>{t.count}</div>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{t.type}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CallsPage({ calls, allCalls, brokers, filters, setFilters, updateStatus, showAddCall, setShowAddCall, newCall, setNewCall, handleAddCall }) {
  const [expandedId, setExpandedId] = useState(null);

  return (
    <div style={{ padding: "24px 28px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Stock Calls</h1>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>{calls.length} calls matching filters</p>
        </div>
        <button onClick={() => setShowAddCall(!showAddCall)} style={{ display: "flex", alignItems: "center", gap: 6, padding: "9px 16px", background: "#0f172a", color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500 }}>
          <i className="ti ti-plus" style={{ fontSize: 15 }}></i> Add Call
        </button>
      </div>

      {showAddCall && (
        <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "20px", marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 500, margin: "0 0 16px" }}>New Stock Call</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
            {[
              { key: "date", label: "Date", type: "date" }, { key: "time", label: "Time", type: "time" },
              { key: "stock", label: "Stock *", type: "text", placeholder: "e.g. TATASTEEL" },
              { key: "broker", label: "Broker *", type: "select", options: brokers.map(b => b.name) },
              { key: "action", label: "Action", type: "select", options: ["BUY", "SELL"] },
              { key: "callType", label: "Call Type", type: "select", options: ["Intraday", "Swing", "Positional", "Long Term"] },
              { key: "exchange", label: "Exchange", type: "select", options: ["NSE", "BSE"] },
              { key: "cmp", label: "CMP", type: "number" }, { key: "entry", label: "Entry", type: "number" },
              { key: "target1", label: "Target 1", type: "number" }, { key: "target2", label: "Target 2", type: "number" },
              { key: "stoploss", label: "Stop Loss", type: "number" }, { key: "support", label: "Support", type: "number" },
              { key: "resistance", label: "Resistance", type: "number" }, { key: "duration", label: "Duration", type: "text" },
            ].map(f => (
              <div key={f.key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <label style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{f.label}</label>
                {f.type === "select" ? (
                  <select value={newCall[f.key] || ""} onChange={e => setNewCall(p => ({ ...p, [f.key]: e.target.value }))} style={{ fontSize: 12, padding: "7px 10px", borderRadius: 6, border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)" }}>
                    {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input type={f.type} value={newCall[f.key] || ""} placeholder={f.placeholder} onChange={e => setNewCall(p => ({ ...p, [f.key]: e.target.value }))} style={{ fontSize: 12, padding: "7px 10px", borderRadius: 6, border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)" }} />
                )}
              </div>
            ))}
          </div>
          <div style={{ marginTop: 10 }}>
            <label style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>Original Message</label>
            <textarea value={newCall.originalMsg} onChange={e => setNewCall(p => ({ ...p, originalMsg: e.target.value }))} rows={2} style={{ width: "100%", marginTop: 4, fontSize: 12, padding: "7px 10px", borderRadius: 6, border: "0.5px solid var(--color-border-secondary)", resize: "vertical", background: "var(--color-background-primary)", color: "var(--color-text-primary)", boxSizing: "border-box" }} />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button onClick={handleAddCall} style={{ padding: "9px 18px", background: "#0f172a", color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500 }}>Save Call</button>
            <button onClick={() => setShowAddCall(false)} style={{ padding: "9px 18px", background: "transparent", color: "var(--color-text-secondary)", border: "0.5px solid var(--color-border-secondary)", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>Cancel</button>
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <input placeholder="Search stock or broker..." value={filters.search} onChange={e => setFilters(p => ({ ...p, search: e.target.value }))} style={{ padding: "8px 12px", borderRadius: 8, border: "0.5px solid var(--color-border-secondary)", fontSize: 12, width: 200, background: "var(--color-background-primary)", color: "var(--color-text-primary)" }} />
        {[
          { key: "broker", options: ["All", ...brokers.map(b => b.name)], label: "Broker" },
          { key: "callType", options: ["All", "Intraday", "Swing", "Positional", "Long Term"], label: "Type" },
          { key: "status", options: ["All", "Target Hit", "SL Hit", "Pending", "Partial Hit", "Expired"], label: "Status" },
        ].map(f => (
          <select key={f.key} value={filters[f.key]} onChange={e => setFilters(p => ({ ...p, [f.key]: e.target.value }))} style={{ padding: "8px 12px", borderRadius: 8, border: "0.5px solid var(--color-border-secondary)", fontSize: 12, background: "var(--color-background-primary)", color: "var(--color-text-primary)" }}>
            {f.options.map(o => <option key={o} value={o}>{o === "All" ? `All ${f.label}s` : o}</option>)}
          </select>
        ))}
      </div>

      <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "var(--color-background-secondary)" }}>
              {["Date", "Stock", "Broker", "Action", "CMP", "Entry", "Target", "SL", "Type", "Status", "P&L%", "Update"].map(h => (
                <th key={h} style={{ padding: "10px 10px", textAlign: "left", fontWeight: 500, fontSize: 11, color: "var(--color-text-secondary)", borderBottom: "0.5px solid var(--color-border-tertiary)", whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {calls.map((c, i) => (
              <>
                <tr key={c.id} onClick={() => setExpandedId(expandedId === c.id ? null : c.id)} style={{ borderBottom: "0.5px solid var(--color-border-tertiary)", cursor: "pointer", background: expandedId === c.id ? "var(--color-background-secondary)" : "transparent" }}>
                  <td style={{ padding: "8px 10px", color: "var(--color-text-secondary)", fontSize: 11 }}>{c.date}</td>
                  <td style={{ padding: "8px 10px", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{c.stock}</td>
                  <td style={{ padding: "8px 10px", maxWidth: 130, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.broker}</td>
                  <td style={{ padding: "8px 10px" }}><span style={{ background: c.action === "BUY" ? "#dcfce7" : "#fee2e2", color: c.action === "BUY" ? "#166534" : "#991b1b", fontSize: 10, padding: "2px 7px", borderRadius: 4, fontWeight: 600 }}>{c.action}</span></td>
                  <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>{c.cmp}</td>
                  <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>{c.entry}</td>
                  <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>{c.targets[0]}</td>
                  <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>{c.stoploss}</td>
                  <td style={{ padding: "8px 10px" }}><span style={{ background: "#f3f4f6", color: "#374151", fontSize: 10, padding: "2px 6px", borderRadius: 4 }}>{c.callType}</span></td>
                  <td style={{ padding: "8px 10px" }}><span style={{ background: STATUS_BG[c.status], color: STATUS_COLORS[c.status], fontSize: 10, padding: "2px 7px", borderRadius: 4, fontWeight: 500 }}>{c.status}</span></td>
                  <td style={{ padding: "8px 10px", fontWeight: 500, color: c.pnlPct === null ? "var(--color-text-secondary)" : c.pnlPct >= 0 ? "#22c55e" : "#ef4444" }}>
                    {c.pnlPct === null ? "—" : (c.pnlPct >= 0 ? "+" : "") + c.pnlPct + "%"}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <select onChange={e => { if (e.target.value) updateStatus(c.id, e.target.value); }} defaultValue="" style={{ fontSize: 10, padding: "3px 6px", borderRadius: 4, border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)", cursor: "pointer" }}>
                      <option value="">Update</option>
                      {["Target Hit", "Partial Hit", "SL Hit", "Expired", "Pending"].map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                </tr>
                {expandedId === c.id && (
                  <tr key={`exp-${c.id}`} style={{ background: "var(--color-background-secondary)" }}>
                    <td colSpan={12} style={{ padding: "12px 16px" }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                        <div>
                          <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 4 }}>Original Message</div>
                          <pre style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, margin: 0, whiteSpace: "pre-wrap", color: "var(--color-text-primary)", background: "var(--color-background-primary)", padding: "8px 10px", borderRadius: 6, border: "0.5px solid var(--color-border-tertiary)" }}>{c.originalMsg}</pre>
                        </div>
                        <div>
                          <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 4 }}>Levels</div>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                            {[["Support", c.support], ["Resistance", c.resistance], ["Target 1", c.targets[0]], ["Target 2", c.targets[1] || "—"]].map(([k, v]) => (
                              <div key={k} style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 6, padding: "6px 10px" }}>
                                <div style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>{k}</div>
                                <div style={{ fontWeight: 500, fontFamily: "monospace" }}>{v}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 4 }}>Details</div>
                          {[["Duration", c.duration || "—"], ["Exchange", c.exchange], ["Time", c.time]].map(([k, v]) => (
                            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "0.5px solid var(--color-border-tertiary)", fontSize: 12 }}>
                              <span style={{ color: "var(--color-text-secondary)" }}>{k}</span><span style={{ fontWeight: 500 }}>{v}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ParsePage({ parseMsg, setParseMsg, parsed, handleParseMsg, handleUseParsed }) {
  const examples = [
    "TRADEBULLS SECURITIES\nTATA STEEL\nCMP 202\nTARGET 236\nSUPPORT 211\nDURATION 2-3 DAYS",
    "BUY RELIANCE ABOVE 1450\nTARGET 1510 / 1540\nSTOPLOSS 1420\nINTRADAY",
    "HDFC SECURITIES:\nACCUMULATE INFY\nTARGET 1820\nSL 1710\nTIME 1 WEEK",
  ];

  return (
    <div style={{ padding: "24px 28px", maxWidth: 900 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Message Parser</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>Paste any broker message to extract structured data automatically</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "20px" }}>
            <h3 style={{ fontSize: 14, fontWeight: 500, margin: "0 0 12px" }}>Input Message</h3>
            <textarea value={parseMsg} onChange={e => setParseMsg(e.target.value)} placeholder="Paste your broker message here..." rows={8} style={{ width: "100%", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, padding: "10px 12px", borderRadius: 8, border: "0.5px solid var(--color-border-secondary)", resize: "vertical", background: "var(--color-background-secondary)", color: "var(--color-text-primary)", boxSizing: "border-box", lineHeight: 1.6 }} />
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button onClick={handleParseMsg} style={{ padding: "9px 18px", background: "#0f172a", color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", gap: 6 }}>
                <i className="ti ti-wand" style={{ fontSize: 14 }}></i> Parse Message
              </button>
              <button onClick={() => { setParseMsg(""); }} style={{ padding: "9px 14px", background: "transparent", color: "var(--color-text-secondary)", border: "0.5px solid var(--color-border-secondary)", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>Clear</button>
            </div>
          </div>

          <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "20px", marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 500, margin: "0 0 12px" }}>Example messages</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {examples.map((e, i) => (
                <button key={i} onClick={() => setParseMsg(e)} style={{ textAlign: "left", padding: "10px 12px", background: "var(--color-background-secondary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 8, cursor: "pointer", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                  {e.split("\n")[0]}...
                </button>
              ))}
            </div>
          </div>
        </div>

        <div>
          {parsed ? (
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 500, margin: 0 }}>Parsed Data</h3>
                <span style={{ background: "#dcfce7", color: "#166534", fontSize: 11, padding: "3px 8px", borderRadius: 6, fontWeight: 500 }}>✓ Extracted</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                {[
                  ["Stock Name", parsed.stock || "—", "#3b82f6"],
                  ["Action", parsed.action, parsed.action === "BUY" ? "#22c55e" : "#ef4444"],
                  ["CMP", parsed.cmp || "—", null],
                  ["Entry Price", parsed.entry || "—", null],
                  ["Targets", parsed.targets.join(", ") || "—", "#22c55e"],
                  ["Stop Loss", parsed.stoploss || "—", "#ef4444"],
                  ["Duration", parsed.duration || "—", null],
                  ["Call Type", parsed.callType, "#8b5cf6"],
                ].map(([k, v, c]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
                    <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{k}</span>
                    <span style={{ fontSize: 13, fontWeight: 500, fontFamily: typeof v === "number" ? "monospace" : "inherit", color: c || "var(--color-text-primary)" }}>{v}</span>
                  </div>
                ))}
              </div>
              <button onClick={handleUseParsed} style={{ marginTop: 16, width: "100%", padding: "10px", background: "#0f172a", color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                <i className="ti ti-plus" style={{ fontSize: 14 }}></i> Use This Data to Add Call
              </button>
            </div>
          ) : (
            <div style={{ background: "var(--color-background-secondary)", border: "0.5px dashed var(--color-border-secondary)", borderRadius: 12, padding: "40px 20px", textAlign: "center" }}>
              <i className="ti ti-wand" style={{ fontSize: 40, color: "var(--color-text-secondary)", opacity: 0.4 }}></i>
              <p style={{ color: "var(--color-text-secondary)", fontSize: 13, marginTop: 12 }}>Paste a message and click "Parse Message" to extract stock call data</p>
            </div>
          )}

          <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "20px", marginTop: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 500, margin: "0 0 10px" }}>Parser capabilities</h3>
            {[
              ["Regex patterns", "CMP, TARGET, TGT, SL, STOPLOSS, ENTRY, ABOVE"],
              ["Keyword detection", "INTRADAY, SWING, POSITIONAL, LONG TERM"],
              ["Multi-target", "Handles TARGET 1510 / 1540 format"],
              ["Stock extraction", "Filters known keywords to find ticker symbol"],
              ["Duration", "Detects 2-3 DAYS, 1 WEEK, etc."],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <i className="ti ti-check" style={{ fontSize: 14, color: "#22c55e", marginTop: 1, flexShrink: 0 }}></i>
                <div>
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{k}: </span>
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{v}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function BrokersPage({ brokerStats, showAddBroker, setShowAddBroker, newBroker, setNewBroker, handleAddBroker, calls }) {
  return (
    <div style={{ padding: "24px 28px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Brokers</h1>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>Manage and rate your signal sources</p>
        </div>
        <button onClick={() => setShowAddBroker(!showAddBroker)} style={{ display: "flex", alignItems: "center", gap: 6, padding: "9px 16px", background: "#0f172a", color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500 }}>
          <i className="ti ti-plus" style={{ fontSize: 15 }}></i> Add Broker
        </button>
      </div>

      {showAddBroker && (
        <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "20px", marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 500, margin: "0 0 14px" }}>New Broker</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
            {[
              { key: "name", label: "Broker Name *", type: "text" },
              { key: "category", label: "Category", type: "select", options: ["Full Service", "Discount Broker", "Bank Broker", "Independent"] },
              { key: "contact", label: "Contact", type: "text" },
              { key: "source", label: "Source", type: "select", options: ["WhatsApp", "Telegram", "Email", "SMS", "App"] },
              { key: "score", label: "Initial Score", type: "number" },
            ].map(f => (
              <div key={f.key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <label style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{f.label}</label>
                {f.type === "select" ? (
                  <select value={newBroker[f.key]} onChange={e => setNewBroker(p => ({ ...p, [f.key]: e.target.value }))} style={{ fontSize: 12, padding: "7px 10px", borderRadius: 6, border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)" }}>
                    {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input type={f.type} value={newBroker[f.key]} onChange={e => setNewBroker(p => ({ ...p, [f.key]: e.target.value }))} style={{ fontSize: 12, padding: "7px 10px", borderRadius: 6, border: "0.5px solid var(--color-border-secondary)", background: "var(--color-background-primary)", color: "var(--color-text-primary)" }} />
                )}
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button onClick={handleAddBroker} style={{ padding: "9px 18px", background: "#0f172a", color: "white", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500 }}>Save Broker</button>
            <button onClick={() => setShowAddBroker(false)} style={{ padding: "9px 14px", background: "transparent", color: "var(--color-text-secondary)", border: "0.5px solid var(--color-border-secondary)", borderRadius: 8, cursor: "pointer", fontSize: 13 }}>Cancel</button>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 14 }}>
        {brokerStats.map((b, i) => {
          const bc = calls.filter(c => c.broker === b.name);
          const hits = bc.filter(c => c.status === "Target Hit").length;
          const sl = bc.filter(c => c.status === "SL Hit").length;
          const scoreColor = b.score >= 80 ? "#22c55e" : b.score >= 65 ? "#f59e0b" : "#ef4444";
          return (
            <div key={b.id} style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "18px 20px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: "var(--color-background-secondary)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 600, fontSize: 14, color: "var(--color-text-primary)" }}>{b.name.slice(0, 2).toUpperCase()}</div>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: 13 }}>{b.name}</div>
                    <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 1 }}>{b.category} · {b.source}</div>
                  </div>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 20, fontWeight: 600, color: scoreColor }}>{b.score}</div>
                  <div style={{ fontSize: 9, color: "var(--color-text-secondary)" }}>SCORE</div>
                </div>
              </div>
              <div style={{ height: 4, borderRadius: 2, background: "var(--color-background-secondary)", marginBottom: 12, overflow: "hidden" }}>
                <div style={{ height: "100%", background: scoreColor, width: b.score + "%" }}></div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8 }}>
                {[["Calls", bc.length], ["Hits", hits], ["SL", sl], ["Win%", bc.length ? Math.round(hits / bc.length * 100) + "%" : "—"]].map(([k, v]) => (
                  <div key={k} style={{ background: "var(--color-background-secondary)", borderRadius: 7, padding: "6px 8px", textAlign: "center" }}>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{v}</div>
                    <div style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>{k}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10, fontSize: 11, color: "var(--color-text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
                <i className="ti ti-mail" style={{ fontSize: 12 }}></i>{b.contact}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AnalyticsPage({ calls, brokerStats, stats, activeTab, setActiveTab }) {
  const completedCalls = calls.filter(c => c.pnlPct !== null);
  const cumPnl = completedCalls.reduce((acc, c, i) => { acc.push((acc[i - 1] || 0) + c.pnlPct); return acc; }, []);

  const byBroker = brokerStats.map(b => {
    const bc = calls.filter(c => c.broker === b.name);
    const wins = bc.filter(c => c.status === "Target Hit").length;
    const partial = bc.filter(c => c.status === "Partial Hit").length;
    const sl = bc.filter(c => c.status === "SL Hit").length;
    const avgRet = bc.filter(c => c.pnlPct !== null).reduce((a, c) => a + c.pnlPct, 0) / (bc.filter(c => c.pnlPct !== null).length || 1);
    return { ...b, wins, partial, sl, avgRet: avgRet.toFixed(1), winRate: bc.length ? Math.round(((wins + partial) / bc.length) * 100) : 0 };
  });

  const statusDist = ["Target Hit", "Partial Hit", "SL Hit", "Pending", "Expired"].map(s => ({
    status: s, count: calls.filter(c => c.status === s).length, color: STATUS_COLORS[s]
  }));

  const byCallType = ["Intraday", "Swing", "Positional", "Long Term"].map(t => {
    const tc = calls.filter(c => c.callType === t);
    const wins = tc.filter(c => c.status === "Target Hit").length;
    return { type: t, total: tc.length, wins, accuracy: tc.length ? Math.round(wins / tc.length * 100) : 0 };
  });

  return (
    <div style={{ padding: "24px 28px" }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Analytics</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>Performance insights across brokers and call types</p>
      </div>

      <div style={{ display: "flex", gap: 4, marginBottom: 20 }}>
        {[["overview", "Overview"], ["brokers", "Broker Analysis"], ["accuracy", "Accuracy"]].map(([t, l]) => (
          <button key={t} onClick={() => setActiveTab(t)} style={{ padding: "7px 14px", borderRadius: 7, border: "0.5px solid var(--color-border-secondary)", background: activeTab === t ? "#0f172a" : "transparent", color: activeTab === t ? "white" : "var(--color-text-secondary)", cursor: "pointer", fontSize: 12, fontWeight: 500 }}>{l}</button>
        ))}
      </div>

      {activeTab === "overview" && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "18px 20px" }}>
              <h3 style={{ fontSize: 13, fontWeight: 500, margin: "0 0 14px" }}>Call outcome distribution</h3>
              {statusDist.map(s => (
                <div key={s.status} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: s.color, flexShrink: 0 }}></div>
                  <span style={{ fontSize: 12, flex: 1 }}>{s.status}</span>
                  <div style={{ flex: 2, height: 6, borderRadius: 3, background: "var(--color-background-secondary)", overflow: "hidden" }}>
                    <div style={{ height: "100%", background: s.color, width: `${(s.count / calls.length) * 100}%` }}></div>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 500, minWidth: 20, textAlign: "right" }}>{s.count}</span>
                  <span style={{ fontSize: 11, color: "var(--color-text-secondary)", minWidth: 34, textAlign: "right" }}>{Math.round(s.count / calls.length * 100)}%</span>
                </div>
              ))}
            </div>
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "18px 20px" }}>
              <h3 style={{ fontSize: 13, fontWeight: 500, margin: "0 0 14px" }}>Accuracy by call type</h3>
              {byCallType.map(t => (
                <div key={t.type} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <span style={{ fontSize: 12, minWidth: 80 }}>{t.type}</span>
                  <div style={{ flex: 1, height: 6, borderRadius: 3, background: "var(--color-background-secondary)", overflow: "hidden" }}>
                    <div style={{ height: "100%", background: "#3b82f6", width: t.accuracy + "%" }}></div>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 500, minWidth: 30, textAlign: "right" }}>{t.accuracy}%</span>
                  <span style={{ fontSize: 11, color: "var(--color-text-secondary)", minWidth: 40, textAlign: "right" }}>{t.total} calls</span>
                </div>
              ))}
            </div>
          </div>
          <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "18px 20px" }}>
            <h3 style={{ fontSize: 13, fontWeight: 500, margin: "0 0 14px" }}>Cumulative P&L curve</h3>
            <div style={{ height: 160, position: "relative" }}>
              <svg width="100%" height="160" viewBox={`0 0 ${Math.max(cumPnl.length * 60, 400)} 160`} preserveAspectRatio="none">
                {cumPnl.length > 1 && (() => {
                  const min = Math.min(...cumPnl, 0);
                  const max = Math.max(...cumPnl, 0);
                  const range = max - min || 1;
                  const pts = cumPnl.map((v, i) => `${(i / (cumPnl.length - 1)) * 100}%,${((max - v) / range) * 130 + 10}`).join(" ");
                  const fillPts = `0%,${((max - 0) / range) * 130 + 10} ${pts} 100%,${((max - 0) / range) * 130 + 10}`;
                  return <>
                    <line x1="0" y1={`${((max) / range) * 130 + 10}`} x2="100%" y2={`${((max) / range) * 130 + 10}`} stroke="#e5e7eb" strokeWidth="1" strokeDasharray="4" />
                    <polyline points={fillPts} fill="rgba(34,197,94,0.1)" stroke="none" />
                    <polyline points={pts.split(",").reduce((a, v, i) => i % 2 === 0 ? a + v + "," : a + v + " ", "")} fill="none" stroke="#22c55e" strokeWidth="2" />
                  </>;
                })()}
              </svg>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--color-text-secondary)", marginTop: 4 }}>
              <span>Start: 0%</span>
              <span>Current: {cumPnl[cumPnl.length - 1]?.toFixed(1) || 0}%</span>
            </div>
          </div>
        </div>
      )}

      {activeTab === "brokers" && (
        <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "var(--color-background-secondary)" }}>
                {["Rank", "Broker", "Category", "Calls", "Wins", "Partial", "SL Hit", "Win Rate", "Avg Return", "Score"].map(h => (
                  <th key={h} style={{ padding: "10px 12px", textAlign: "left", fontWeight: 500, fontSize: 11, color: "var(--color-text-secondary)", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {byBroker.map((b, i) => (
                <tr key={b.id} style={{ borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
                  <td style={{ padding: "10px 12px", fontWeight: 600, color: i === 0 ? "#d97706" : "var(--color-text-secondary)" }}>#{i + 1}</td>
                  <td style={{ padding: "10px 12px", fontWeight: 500 }}>{b.name}</td>
                  <td style={{ padding: "10px 12px", color: "var(--color-text-secondary)" }}>{b.category}</td>
                  <td style={{ padding: "10px 12px" }}>{b.callCount}</td>
                  <td style={{ padding: "10px 12px", color: "#22c55e", fontWeight: 500 }}>{b.wins}</td>
                  <td style={{ padding: "10px 12px", color: "#f59e0b", fontWeight: 500 }}>{b.partial}</td>
                  <td style={{ padding: "10px 12px", color: "#ef4444", fontWeight: 500 }}>{b.sl}</td>
                  <td style={{ padding: "10px 12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ height: 4, width: 60, borderRadius: 2, background: "var(--color-background-secondary)", overflow: "hidden" }}>
                        <div style={{ height: "100%", background: b.winRate >= 70 ? "#22c55e" : b.winRate >= 50 ? "#f59e0b" : "#ef4444", width: b.winRate + "%" }}></div>
                      </div>
                      <span style={{ fontWeight: 500 }}>{b.winRate}%</span>
                    </div>
                  </td>
                  <td style={{ padding: "10px 12px", color: parseFloat(b.avgRet) >= 0 ? "#22c55e" : "#ef4444", fontWeight: 500 }}>{b.avgRet}%</td>
                  <td style={{ padding: "10px 12px" }}>
                    <span style={{ background: b.score >= 80 ? "#dcfce7" : b.score >= 65 ? "#fef3c7" : "#fee2e2", color: b.score >= 80 ? "#166534" : b.score >= 65 ? "#92400e" : "#991b1b", fontSize: 11, padding: "3px 8px", borderRadius: 6, fontWeight: 600 }}>{b.score}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "accuracy" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "18px 20px" }}>
            <h3 style={{ fontSize: 13, fontWeight: 500, margin: "0 0 14px" }}>Risk-reward analysis</h3>
            {calls.filter(c => c.entry && c.targets[0] && c.stoploss).slice(0, 8).map(c => {
              const reward = Math.abs(c.targets[0] - c.entry);
              const risk = Math.abs(c.entry - c.stoploss);
              const rr = (reward / risk).toFixed(1);
              return (
                <div key={c.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <span style={{ fontFamily: "monospace", fontSize: 11, minWidth: 80, fontWeight: 500 }}>{c.stock}</span>
                  <div style={{ flex: 1, height: 14, background: "var(--color-background-secondary)", borderRadius: 3, position: "relative", overflow: "hidden" }}>
                    <div style={{ position: "absolute", left: 0, top: 0, height: "100%", background: "#ef4444", width: `${(risk / (risk + reward)) * 100}%` }}></div>
                    <div style={{ position: "absolute", right: 0, top: 0, height: "100%", background: "#22c55e", width: `${(reward / (risk + reward)) * 100}%` }}></div>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, minWidth: 32 }}>R:{rr}</span>
                  <span style={{ background: STATUS_BG[c.status], color: STATUS_COLORS[c.status], fontSize: 10, padding: "2px 6px", borderRadius: 4 }}>{c.status}</span>
                </div>
              );
            })}
            <div style={{ marginTop: 8, display: "flex", gap: 12, fontSize: 11, color: "var(--color-text-secondary)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: 1, background: "#ef4444", display: "inline-block" }}></span> Risk</span>
              <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: 1, background: "#22c55e", display: "inline-block" }}></span> Reward</span>
            </div>
          </div>
          <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: 12, padding: "18px 20px" }}>
            <h3 style={{ fontSize: 13, fontWeight: 500, margin: "0 0 14px" }}>P&L distribution</h3>
            {completedCalls.sort((a, b) => b.pnlPct - a.pnlPct).map(c => (
              <div key={c.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
                <span style={{ fontFamily: "monospace", fontSize: 11, minWidth: 80, fontWeight: 500 }}>{c.stock}</span>
                <div style={{ flex: 1, height: 6, borderRadius: 3, background: "var(--color-background-secondary)", overflow: "hidden" }}>
                  <div style={{ height: "100%", background: c.pnlPct >= 0 ? "#22c55e" : "#ef4444", width: Math.min(Math.abs(c.pnlPct) * 4, 100) + "%" }}></div>
                </div>
                <span style={{ fontSize: 11, fontWeight: 600, minWidth: 40, textAlign: "right", color: c.pnlPct >= 0 ? "#22c55e" : "#ef4444" }}>
                  {c.pnlPct >= 0 ? "+" : ""}{c.pnlPct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

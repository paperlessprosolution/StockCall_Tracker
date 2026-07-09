/**
 * API client — all calls to the Flask backend
 * Base URL reads from Vite env or defaults to localhost:5000
 */

const BASE = typeof import_meta !== "undefined"
  ? (import_meta.env?.VITE_API_URL || "http://localhost:5000/api")
  : "http://localhost:5000/api";

async function req(path, options = {}) {
  const url = BASE + path;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Calls ─────────────────────────────────────
export const api = {
  calls: {
    list:   (params = {}) => req("/calls/?" + new URLSearchParams(params)),
    get:    (id)          => req(`/calls/${id}`),
    create: (data)        => req("/calls/", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data)    => req(`/calls/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id)          => req(`/calls/${id}`, { method: "DELETE" }),
    parse:  (message)     => req("/calls/parse", { method: "POST", body: JSON.stringify({ message }) }),
  },
  brokers: {
    list:   ()            => req("/brokers/"),
    create: (data)        => req("/brokers/", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data)    => req(`/brokers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id)          => req(`/brokers/${id}`, { method: "DELETE" }),
    rescore:(id)          => req(`/brokers/${id}/rescore`, { method: "POST" }),
  },
  analytics: {
    dashboard: ()         => req("/analytics/dashboard"),
    brokers:   ()         => req("/analytics/brokers"),
    byType:    ()         => req("/analytics/by-type"),
    monthly:   ()         => req("/analytics/monthly"),
    rr:        ()         => req("/analytics/rr"),
    topStocks: ()         => req("/analytics/top-stocks"),
    rescoreAll:()         => req("/analytics/rescore-all", { method: "POST" }),
  },
  prices: {
    get:     (symbol, exchange = "NSE") => req(`/prices/${symbol}?exchange=${exchange}`),
    bulk:    (symbols, exchange = "NSE") => req("/prices/bulk", { method: "POST", body: JSON.stringify({ symbols, exchange }) }),
    history: (symbol, days = 30)        => req(`/prices/history/${symbol}?days=${days}`),
    updateStatuses: ()                  => req("/prices/update-statuses", { method: "POST" }),
  },
  alerts: {
    list:   ()            => req("/alerts/"),
    check:  ()            => req("/alerts/check", { method: "POST" }),
    delete: (id)          => req(`/alerts/${id}`, { method: "DELETE" }),
  },
  import: {
    parseMessage: (message) => req("/import/parse-message", { method: "POST", body: JSON.stringify({ message }) }),
    bulkSave:     (records) => req("/import/bulk-save", { method: "POST", body: JSON.stringify({ records }) }),
    uploadFile:   (endpoint, file) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(BASE + endpoint, { method: "POST", body: form }).then(r => r.json());
    },
  },
};

export default api;

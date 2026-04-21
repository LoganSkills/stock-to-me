const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type TokenGetter = () => Promise<string | null>;

let _getToken: TokenGetter | null = null;

export function setTokenGetter(fn: TokenGetter) {
  _getToken = fn;
}

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = _getToken ? await _getToken() : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(`${API_BASE}${url}`, { ...options, headers });
}

export const api = {
  // Auth
  register: (email: string, password: string) =>
    fetchWithAuth("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }).then((r) => r.json()),

  login: (email: string, password: string) =>
    fetchWithAuth("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }).then((r) => r.json()),

  getMe: () => fetchWithAuth("/auth/me").then((r) => r.json()),

  // Dashboard
  getDashboardOverview: () =>
    fetchWithAuth("/dashboard/overview").then((r) => r.json()),

  getTopTraps: (limit = 20) =>
    fetchWithAuth(`/dashboard/top-traps?limit=${limit}`).then((r) => r.json()),

  getNewFilings: (limit = 20) =>
    fetchWithAuth(`/dashboard/new-filings?limit=${limit}`).then((r) => r.json()),

  // Stocks
  listStocks: (params: Record<string, string | number | undefined> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined) as URLSearchParams
    ).toString();
    return fetchWithAuth(`/stocks${qs ? `?${qs}` : ""}`).then((r) => r.json());
  },

  getStock: (ticker: string) =>
    fetchWithAuth(`/stocks/${ticker.toUpperCase()}`).then((r) => r.json()),

  getStockScores: (ticker: string) =>
    fetchWithAuth(`/stocks/${ticker.toUpperCase()}/scores`).then((r) => r.json()),

  getStockTimeline: (ticker: string) =>
    fetchWithAuth(`/stocks/${ticker.toUpperCase()}/timeline`).then((r) => r.json()),

  getStockFilings: (ticker: string, limit = 20) =>
    fetchWithAuth(`/stocks/${ticker.toUpperCase()}/filings?limit=${limit}`).then((r) =>
      r.json()
    ),

  getDilutionImpact: (ticker: string) =>
    fetchWithAuth(`/stocks/${ticker.toUpperCase()}/dilution-impact`).then((r) =>
      r.json()
    ),

  // Alerts
  getAlerts: (unreadOnly = false, limit = 50) =>
    fetchWithAuth(`/alerts?unread_only=${unreadOnly}&limit=${limit}`).then((r) =>
      r.json()
    ),

  markAlertRead: (alertId: number) =>
    fetchWithAuth(`/alerts/${alertId}/read`, { method: "PATCH" }).then((r) => r.json()),

  // Watchlists
  getWatchlists: () => fetchWithAuth("/watchlists").then((r) => r.json()),

  createWatchlist: (name: string) =>
    fetchWithAuth("/watchlists", {
      method: "POST",
      body: JSON.stringify({ name }),
    }).then((r) => r.json()),

  addToWatchlist: (watchlistId: number, ticker: string) =>
    fetchWithAuth(`/watchlists/${watchlistId}/items`, {
      method: "POST",
      body: JSON.stringify({ ticker }),
    }).then((r) => r.json()),

  removeFromWatchlist: (watchlistId: number, ticker: string) =>
    fetchWithAuth(`/watchlists/${watchlistId}/items/${ticker}`, {
      method: "DELETE",
    }).then((r) => r.json()),
};

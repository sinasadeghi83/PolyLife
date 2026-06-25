// Lightweight API client for the PolyLife core.
// Served same-origin (Django serves the SPA and the API together), so paths
// are relative and no CORS setup is needed.
//
// Tokens live in localStorage. When a short-lived access token expires, the
// client transparently uses the refresh token to get a new one and retries —
// so a logged-in user stays logged in for the refresh token's lifetime.

const BASE = import.meta.env.VITE_API_BASE ?? '';
const ACCESS_KEY = 'polylife_token';
const REFRESH_KEY = 'polylife_refresh';

export function getToken() {
  return localStorage.getItem(ACCESS_KEY);
}
function setAccess(token) {
  localStorage.setItem(ACCESS_KEY, token);
}
function setRefresh(token) {
  localStorage.setItem(REFRESH_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function tryRefresh() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  const res = await fetch(`${BASE}/api/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json().catch(() => ({}));
  if (data.token) {
    setAccess(data.token);
    return true;
  }
  return false;
}

async function request(path, { method = 'GET', body, auth = false, _retried = false } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Access token expired? Refresh once and retry the original request.
  if (res.status === 401 && auth && !_retried) {
    if (await tryRefresh()) {
      return request(path, { method, body, auth, _retried: true });
    }
    clearToken();
  }

  let data = {};
  try {
    data = await res.json();
  } catch {
    // response had no JSON body
  }

  if (!res.ok || data.success === false) {
    throw new Error(data.message || 'خطایی رخ داد');
  }
  return data;
}

export function register({ username, password, first_name = '', last_name = '' }) {
  return request('/api/register', {
    method: 'POST',
    body: { username, password, first_name, last_name },
  });
}

export async function login({ username, password }) {
  const data = await request('/api/login', {
    method: 'POST',
    body: { username, password },
  });
  if (data.token) setAccess(data.token);
  if (data.refresh) setRefresh(data.refresh);
  return data;
}

export function getCurrentUser() {
  return request('/api/user', { auth: true });
}

export async function logout() {
  try {
    await request('/api/logout', { method: 'POST', auth: true });
  } finally {
    clearToken();
  }
}

export function getMicroservices() {
  return request('/api/microservices/');
}

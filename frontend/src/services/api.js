// const PRIMARY_API = 'https://wonderful-generosity-production.up.railway.app'; studentattendancetrackingsystem-production-6440.up.railway.app
const DEFAULT_API_BASE =
  typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)
    ? 'http://localhost:8000'
    : 'https://studentattendancetrackingsystem-production-7589.up.railway.app';
const API_BASE = (process.env.REACT_APP_API_BASE || DEFAULT_API_BASE).replace(/\/$/, '');

function getCookie(name) {
  if (typeof document === 'undefined' || !document.cookie) {
    return '';
  }

  const cookies = document.cookie.split(';');
  for (let i = 0; i < cookies.length; i += 1) {
    const cookie = cookies[i].trim();
    if (cookie.startsWith(`${name}=`)) {
      return decodeURIComponent(cookie.slice(name.length + 1));
    }
  }
  return '';
}

function buildUrl(path) {
  // If path already includes protocol, leave it alone.
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  return `${API_BASE}${path}`;
}

async function fetchJson(path, options = {}) {
  const url = buildUrl(path);
  const method = (options.method || 'GET').toUpperCase();
  const csrfToken = getCookie('csrftoken');

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (csrfToken && method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
    headers['X-CSRFToken'] = csrfToken;
  }

  const finalOptions = {
    credentials: 'include',
    headers,
    ...options,
  };

  const response = await fetch(url, finalOptions);
  const text = await response.text();

  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }

  if (!response.ok) {
    const errorMessage = data?.message || response.statusText || `Request failed (${response.status})`;
    const error = new Error(errorMessage);
    error.status = response.status;
    error.details = data;
    error.url = url;
    throw error;
  }

  return data;
}

export async function login({ username, password }) {
  await fetchJson('/api/auth/csrf/');
  return fetchJson('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function logout() {
  return fetchJson('/api/auth/logout/', {
    method: 'POST',
  });
}

export async function getCurrentUser() {
  return fetchJson('/api/auth/me/');
}

export async function getStudentDashboard() {
  return fetchJson('/api/student/dashboard/');
}

export async function getLecturerDashboard() {
  return fetchJson('/api/lecturer/dashboard/');
}

export async function askAiChat(message) {
  return fetchJson('/api/chat/', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

import { getCurrentUserToken } from '../lib/firebase';
import { triggerAlert } from '@/components/alertBus';

async function withAuthHeaders(headers = {}) {
  const token = await getCurrentUserToken();
  if (token) return { ...headers, Authorization: `Bearer ${token}` };
  return headers;
}

export async function authStatus() {
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/auth/status`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function authMe() {
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/auth/me`, { headers });
  if (res.status === 401) {
    triggerAlert('error', 'Sign in required', 'Please sign in to continue.');
    return { authenticated: false, user: null };
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function uploadFiles(files) {
  const form = new FormData();
  for (const f of files) form.append('files', f);
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/upload-temp`, { method: 'POST', headers, body: form });
  if (res.status === 401) {
    triggerAlert('error', 'Sign in required', 'Please sign in to upload files.');
    throw new Error('Unauthorized: Please sign in to upload files.');
  }
  if (res.status === 403) throw new Error('Registration required: Please complete your profile to upload files.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSessionStats(sessionId) {
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/session/${sessionId}/stats`, { headers });
  if (res.status === 401) { triggerAlert('error', 'Sign in required', 'Please sign in.'); throw new Error('Unauthorized: Please sign in.'); }
  if (res.status === 403) throw new Error('Registration required: Please complete your profile.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listEmbeddings(sessionId, { offset = 0, limit = 50, includeVectors = false, type, search } = {}) {
  const params = new URLSearchParams();
  params.set('offset', String(offset));
  params.set('limit', String(limit));
  if (includeVectors) params.set('includeVectors', 'true');
  if (type) params.set('type', type);
  if (search) params.set('search', search);
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/session/${sessionId}/embeddings?${params.toString()}`, { headers });
  if (res.status === 401) { triggerAlert('error', 'Sign in required', 'Please sign in.'); throw new Error('Unauthorized: Please sign in.'); }
  if (res.status === 403) throw new Error('Registration required: Please complete your profile.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getEmbedding(sessionId, indexId, includeVector = true) {
  const params = new URLSearchParams();
  if (includeVector) params.set('includeVector', 'true');
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/session/${sessionId}/embedding/${indexId}?${params.toString()}`, { headers });
  if (res.status === 401) { triggerAlert('error', 'Sign in required', 'Please sign in.'); throw new Error('Unauthorized: Please sign in.'); }
  if (res.status === 403) throw new Error('Registration required: Please complete your profile.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportEmbeddings(sessionId, { format = 'jsonl', includeVectors = true } = {}) {
  const params = new URLSearchParams();
  params.set('format', format);
  if (includeVectors) params.set('includeVectors', 'true');
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/session/${sessionId}/export?${params.toString()}`, { headers });
  if (res.status === 401) { triggerAlert('error', 'Sign in required', 'Please sign in.'); throw new Error('Unauthorized: Please sign in.'); }
  if (res.status === 403) throw new Error('Registration required: Please complete your profile.');
  if (!res.ok) throw new Error(await res.text());
  return res.text();
}

export async function retrieve(sessionId, query, k = 5, returnVectors = false) {
  const body = { session_id: sessionId, query, k, returnVectors };
  const headers = await withAuthHeaders({ 'Content-Type': 'application/json' });
  const res = await fetch(`${API_BASE}/retrieve/detailed`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (res.status === 401) { triggerAlert('error', 'Sign in required', 'Please sign in.'); throw new Error('Unauthorized: Please sign in.'); }
  if (res.status === 403) throw new Error('Registration required: Please complete your profile.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function retrieveSimple(query) {
  const headers = await withAuthHeaders({ 'Content-Type': 'application/json' });
  const res = await fetch(`${API_BASE}/retrieve`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query }),
  });
  if (res.status === 401) { triggerAlert('error', 'Sign in required', 'Please sign in.'); throw new Error('Unauthorized: Please sign in.'); }
  if (res.status === 403) throw new Error('Registration required: Please complete your profile.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function retrieveDetailed(sessionId, query, k = 5, returnVectors = false) {
  const headers = await withAuthHeaders({ 'Content-Type': 'application/json' });
  const res = await fetch(`${API_BASE}/retrieve/detailed`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId, query, k, returnVectors }),
  });
  if (res.status === 401) throw new Error('Unauthorized: Please sign in.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLastSimple() {
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/retrieve/last`, { headers });
  if (res.status === 401) throw new Error('Unauthorized: Please sign in.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLastDetailed(sessionId) {
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/retrieve/last/${sessionId}`, { headers });
  if (res.status === 401) throw new Error('Unauthorized: Please sign in.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteSession(sessionId) {
  const headers = await withAuthHeaders();
  const res = await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE', headers });
  if (res.status === 401) throw new Error('Unauthorized: Please sign in.');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}



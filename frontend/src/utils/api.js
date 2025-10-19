const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://geollm-backend-hbdccjdfhhdphyfx.canadacentral-01.azurewebsites.net";

export async function uploadFiles(files) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch(`${API_BASE}/upload-temp`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSessionStats(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/stats`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listEmbeddings(
  sessionId,
  { offset = 0, limit = 50, includeVectors = false, type, search } = {}
) {
  const params = new URLSearchParams();
  params.set("offset", String(offset));
  params.set("limit", String(limit));
  if (includeVectors) params.set("includeVectors", "true");
  if (type) params.set("type", type);
  if (search) params.set("search", search);
  const res = await fetch(
    `${API_BASE}/session/${sessionId}/embeddings?${params.toString()}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getEmbedding(sessionId, indexId, includeVector = true) {
  const params = new URLSearchParams();
  if (includeVector) params.set("includeVector", "true");
  const res = await fetch(
    `${API_BASE}/session/${sessionId}/embedding/${indexId}?${params.toString()}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exportEmbeddings(
  sessionId,
  { format = "jsonl", includeVectors = true } = {}
) {
  const params = new URLSearchParams();
  params.set("format", format);
  if (includeVectors) params.set("includeVectors", "true");
  const res = await fetch(
    `${API_BASE}/session/${sessionId}/export?${params.toString()}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.text();
}

export async function retrieve(sessionId, query, k = 5, returnVectors = false) {
  // Backward-compat: route to detailed endpoint now
  const body = { session_id: sessionId, query, k, returnVectors };
  const res = await fetch(`${API_BASE}/retrieve/detailed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function retrieveSimple(query) {
  const res = await fetch(`${API_BASE}/retrieve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function retrieveDetailed(
  sessionId,
  query,
  k = 5,
  returnVectors = false
) {
  const res = await fetch(`${API_BASE}/retrieve/detailed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, query, k, returnVectors }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLastSimple() {
  const res = await fetch(`${API_BASE}/retrieve/last`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLastDetailed(sessionId) {
  const res = await fetch(`${API_BASE}/retrieve/last/${sessionId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${API_BASE}/session/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

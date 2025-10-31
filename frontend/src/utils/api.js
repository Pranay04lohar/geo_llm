const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

// ============================================================================
// RAG Endpoints
// ============================================================================

// Upload documents to RAG
export async function uploadFiles(files, sessionId = null) {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  if (sessionId) form.append("session_id", sessionId);

  const res = await fetch(`${API_BASE}/rag/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Get RAG session info
export async function getSessionStats(sessionId) {
  const res = await fetch(`${API_BASE}/rag/sessions/${sessionId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Delete RAG session
export async function deleteSession(sessionId) {
  const res = await fetch(`${API_BASE}/rag/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// List all RAG sessions
export async function listSessions() {
  const res = await fetch(`${API_BASE}/rag/sessions`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Direct RAG query (alternative to using processQuery with session_id)
export async function queryDocuments(sessionId, query, k = 5) {
  const res = await fetch(`${API_BASE}/rag/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      query,
      top_k: k,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ============================================================================
// Health Check
// ============================================================================
export async function healthCheck() {
  const res = await fetch(`http://localhost:8000/health`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ============================================================================
// Legacy Compatibility (for gradual migration)
// ============================================================================

// Backward compatibility - map old retrieve() to new processQuery()
export async function retrieve(sessionId, query, k = 5, returnVectors = false) {
  return queryDocuments(sessionId, query, k);
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
  console.warn("getLastSimple() is deprecated in monolithic architecture");
  return null;
}

export async function getLastDetailed(sessionId) {
  console.warn("getLastDetailed() is deprecated in monolithic architecture");
  return null;
}

// old deleteSession removed; use the RAG version above

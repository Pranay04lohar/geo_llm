let globalAlert = null;

export function setGlobalAlert(fn) {
  globalAlert = fn;
}

export function triggerAlert(type, title, description) {
  if (!globalAlert) return;
  try {
    globalAlert(type, title, description);
  } catch (_) {
    // no-op
  }
}




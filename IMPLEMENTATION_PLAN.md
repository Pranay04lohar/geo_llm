# Implementation Plan: Resource Management & Timeout Protection

## 🎯 Goal

Fix the "first request works, subsequent requests stuck at 80%" issue by adding resource cleanup, timeout protection, and concurrency limiting while maintaining your existing architecture.

---

## ✅ What We're Keeping

- ✅ Existing anti-buffering fixes (already applied)
- ✅ `SimpleStepProcessor` architecture (works well)
- ✅ Service static method pattern (no breaking changes)
- ✅ FastAPI + uvicorn (Azure manages this)

---

## 📋 Implementation Plan

### **Fix 1: Resource Cleanup in Stream Generator**

**File:** `backend/app/routers/query_router.py`

**What:** Add `finally` block with garbage collection to `_stream_steps()` function

**Why:** Ensures resources are freed after each stream completes (prevents memory/resource accumulation)

**Impact:** Low risk, high benefit for preventing stuck workers

---

### **Fix 2: Resource Cleanup in SimpleStepProcessor**

**File:** `backend/app/services/core_llm_agent/simple_step_processor.py`

**What:** Add cleanup in `process_lst_analysis_steps()` and other analysis methods:

- Add `finally` blocks with `gc.collect()`
- Ensure processors are cleaned up even on errors

**Why:** Earth Engine operations can leave resources that accumulate across requests

**Impact:** Prevents resource leak that causes subsequent requests to hang

---

### **Fix 3: Timeout Protection for Earth Engine Operations**

**File:** `backend/app/services/gee/lst_service.py` (and similar services)

**What:** Wrap long-running `.getInfo()` calls with `asyncio.wait_for()` timeout protection

**Why:** Earth Engine operations can hang indefinitely, blocking subsequent requests

**Impact:** Prevents stuck operations from blocking the entire worker

**Note:** We'll wrap the actual `.getInfo()` calls, not rewrite the entire service

---

### **Fix 4: Concurrency Limiting Middleware**

**File:** `backend/app/main.py`

**What:** Add middleware to limit concurrent analysis requests (max 2-3 simultaneous)

**Why:** Prevents resource exhaustion when multiple users trigger analyses

**Impact:** Reduces risk of worker resource contention

---

### **Fix 5: Enhanced web.config for Azure**

**File:** `backend/web.config`

**What:** Add compression disable for SSE endpoints + additional Azure optimizations

**Why:** Ensures compression doesn't interfere with streaming

**Impact:** Low risk, supporting fix

---

### **Fix 6: Azure Portal Configuration**

**Not a code change** - Instructions to:

- Disable ARR Affinity (if enabled)
- Verify PYTHONUNBUFFERED=1 is set

**Why:** Azure-specific settings that can cause resource pinning

---

## 🚫 What We're NOT Changing

- ❌ NOT rewriting entire stream generator (works fine)
- ❌ NOT changing service architecture (static methods are fine)
- ❌ NOT adding Gunicorn config (Azure manages this)
- ❌ NOT changing SimpleStepProcessor logic (just add cleanup)
- ❌ NOT removing existing anti-buffering fixes

---

## 📊 Implementation Order & Risk Assessment

| Fix                       | File                       | Risk   | Priority | Estimated Time |
| ------------------------- | -------------------------- | ------ | -------- | -------------- |
| 1. Stream cleanup         | `query_router.py`          | Low    | **HIGH** | 10 min         |
| 2. Processor cleanup      | `simple_step_processor.py` | Low    | **HIGH** | 15 min         |
| 3. EE timeout protection  | `lst_service.py`           | Medium | Medium   | 20 min         |
| 4. Concurrency middleware | `main.py`                  | Low    | Medium   | 15 min         |
| 5. web.config enhancement | `web.config`               | Low    | Low      | 5 min          |
| 6. Azure portal config    | Manual                     | None   | Low      | 2 min          |

**Total Estimated Time:** ~1 hour

---

## 🔍 Detailed Changes

### Fix 1: Stream Generator Cleanup

**Location:** `backend/app/routers/query_router.py` - `_stream_steps()` function

**Change:** Wrap entire try block with proper `finally` block:

```python
async def _stream_steps(...):
    processor = None
    try:
        # ... existing code ...
    except Exception as e:
        # ... existing error handling ...
    finally:
        # NEW: Force cleanup
        import gc
        if processor:
            del processor
        gc.collect()
        logger.info("🧹 [AZURE-DEBUG] Stream resources cleaned up")
```

---

### Fix 2: SimpleStepProcessor Cleanup

**Location:** `backend/app/services/core_llm_agent/simple_step_processor.py`

**Change:** Add `finally` blocks to analysis methods:

```python
async def process_lst_analysis_steps(...):
    lst_service = None
    try:
        # ... existing code ...
        from app.services.gee.lst_service import LSTService
        result = LSTService.analyze_lst_with_polygon(...)
        # ... rest of code ...
    except Exception as e:
        # ... existing error handling ...
    finally:
        # NEW: Cleanup
        import gc
        if lst_service:
            del lst_service
        gc.collect()
        logger.debug("🧹 [LST] Cleaned up processor resources")
```

Apply to:

- `process_lst_analysis_steps()`
- `process_water_analysis_steps()`
- `process_ndvi_analysis_steps()` (if exists)

---

### Fix 3: Earth Engine Timeout Protection

**Location:** `backend/app/services/gee/lst_service.py` (and other services)

**Challenge:** Services use static methods with synchronous `.getInfo()` calls

**Solution:** Create a helper wrapper for async timeout:

```python
# Add at top of service file
async def _get_info_with_timeout(ee_object, timeout=60.0):
    """Wrap Earth Engine .getInfo() with timeout protection"""
    import asyncio
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(ee_object.getInfo),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Earth Engine operation timed out after {timeout}s")
        raise Exception(f"Analysis timed out. Try a smaller area or shorter time range.")
```

**Usage:** Wrap critical `.getInfo()` calls in services (where possible)

**Note:** This requires making service calls async-aware, which might need careful implementation to avoid breaking changes.

**Alternative (Simpler):** Just add timeout logging and let existing error handling catch it - less invasive.

---

### Fix 4: Concurrency Limiting Middleware

**Location:** `backend/app/main.py` (already has middleware section)

**Add after existing middleware:**

```python
import asyncio
import gc

# Limit concurrent analysis requests
MAX_CONCURRENT_ANALYSES = 3
analysis_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSES)

@app.middleware("http")
async def concurrency_limit_middleware(request: Request, call_next):
    """Limit concurrent analysis requests to prevent resource exhaustion"""
    if "/api/query/stream" in request.url.path:
        async with analysis_semaphore:
            try:
                response = await call_next(request)
                return response
            finally:
                # Force cleanup after each analysis
                gc.collect()
                logger.debug(f"🧹 Cleaned up resources after {request.url.path}")
    else:
        return await call_next(request)
```

---

### Fix 5: web.config Enhancement

**Location:** `backend/web.config`

**Add after existing `<urlCompression>` section:**

```xml
<!-- Disable compression for SSE to prevent buffering -->
<httpCompression>
  <dynamicTypes>
    <add mimeType="text/event-stream" enabled="false" />
  </dynamicTypes>
</httpCompression>
```

(Actually, we already have this, just verify it's correct)

---

### Fix 6: Azure Portal Configuration

**Manual Steps:**

1. Azure Portal → Your App Service → Configuration → General settings
2. Find **ARR Affinity** → Set to **Off** (if enabled)
3. Verify **PYTHONUNBUFFERED** = "1" in Application settings
4. Save and restart

---

## 🧪 Testing Plan

### After Each Fix:

1. Deploy to Azure (test environment if available)
2. Run 3 consecutive analyses:
   - Request 1: Should work
   - Request 2: Should work (this was failing before)
   - Request 3: Should work
3. Monitor Azure logs for:
   - "🧹 Cleaned up resources" messages
   - No stuck/hanging operations
   - All requests complete successfully

### Expected Log Patterns:

```
✅ First request:
   🚀 [AZURE-DEBUG] Starting SSE stream
   ... steps ...
   ✅ [AZURE-DEBUG] Streaming completed successfully
   🧹 [AZURE-DEBUG] Stream resources cleaned up

✅ Second request (was failing):
   🚀 [AZURE-DEBUG] Starting SSE stream
   ... steps ...
   ✅ [AZURE-DEBUG] Streaming completed successfully
   🧹 [AZURE-DEBUG] Stream resources cleaned up  ← NEW

✅ Third request:
   🚀 [AZURE-DEBUG] Starting SSE stream
   ... steps ...
   ✅ [AZURE-DEBUG] Streaming completed successfully
   🧹 [AZURE-DEBUG] Stream resources cleaned up  ← NEW
```

---

## ⚠️ Risks & Mitigations

| Risk                             | Mitigation                                            |
| -------------------------------- | ----------------------------------------------------- |
| Breaking existing functionality  | Only add cleanup, don't change logic                  |
| Timeout wrapping complexity      | Start with simple cleanup, add timeouts incrementally |
| Concurrency limit too strict     | Start with 3, adjust based on testing                 |
| Async changes breaking sync code | Skip Fix 3 if too complex, focus on cleanup first     |

---

## ✅ Recommended Implementation Order

**Phase 1 (Quick Wins - ~30 min):**

1. ✅ Fix 1: Stream generator cleanup
2. ✅ Fix 2: SimpleStepProcessor cleanup
3. ✅ Deploy and test

**Phase 2 (If Phase 1 doesn't fix it - ~45 min):** 4. ✅ Fix 4: Concurrency limiting middleware 5. ✅ Fix 6: Azure portal config 6. ✅ Deploy and test

**Phase 3 (Advanced - only if needed):** 7. ⚠️ Fix 3: Earth Engine timeout protection (most complex)

---

## 📝 Decision Points

**Question 1:** Should we implement Fix 3 (Earth Engine timeouts) immediately, or try cleanup first?

**Recommendation:** Try Phase 1 first. If it fixes the issue, we avoid the complexity of async wrapping.

**Question 2:** What concurrency limit should we use?

**Recommendation:** Start with 3 concurrent analyses. Adjust based on your Azure plan tier and testing.

**Question 3:** Should we implement all fixes at once or incrementally?

**Recommendation:** Incrementally - Phase 1 first, test, then Phase 2 if needed. Easier to debug and verify what works.

---

## 🎯 Success Criteria

After implementation:

- ✅ First analysis works (already working)
- ✅ Second analysis works (currently failing)
- ✅ Third+ analysis works (currently failing)
- ✅ Azure logs show cleanup messages
- ✅ No stuck workers in Azure metrics
- ✅ Memory/resource usage stays stable across requests

---

## 🤔 Your Approval Needed

Please review and approve:

1. ✅ Overall approach (focus on cleanup, not rewriting)
2. ✅ Phase 1 fixes first (stream + processor cleanup)
3. ✅ Incremental implementation (test after each phase)
4. ✅ Skip Fix 3 initially (timeout protection) if Phase 1 works

**If approved, I'll implement Phase 1 first and we can test before moving to Phase 2.**

---

**Ready for your approval to proceed!** 🚀

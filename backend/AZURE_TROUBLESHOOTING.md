# Azure Deployment Troubleshooting Guide

## Problem: Streaming Gets Stuck at 100% Progress

### Symptoms

- Analysis reaches 100% progress on the frontend
- Final results are not displayed
- Backend logs show no errors
- Works perfectly on local machine
- Azure deployment appears "stuck"

### Root Causes

#### 1. **Azure Response Buffering** (Most Common)

Azure App Service buffers HTTP responses by default, which breaks Server-Sent Events (SSE) streaming.

**Solution Applied:**

- Added `X-Accel-Buffering: no` header in `web.config`
- Added `Cache-Control: no-cache, no-transform` header in streaming endpoint
- Added `Content-Encoding: none` to prevent compression buffering
- Set `PYTHONUNBUFFERED=1` environment variable

#### 2. **Connection Timeout**

Azure drops idle connections after a period of time.

**Solution Applied:**

- Added keep-alive heartbeat every 15 seconds in `_stream_steps()`
- Increased `requestTimeout` to 10 minutes in `web.config`
- Set `timeout_keep_alive=300` (5 minutes) in `startup.py`

#### 3. **Incorrect Startup Configuration**

The original `startup.py` was calling `app.run()` which doesn't work for FastAPI.

**Solution Applied:**

- Fixed `startup.py` to use `uvicorn.run()` with proper configuration
- Added Azure-specific uvicorn settings

---

## Configuration Files Changed

### 1. `backend/startup.py`

```python
# Azure-compatible uvicorn configuration
uvicorn.run(
    app,
    host="0.0.0.0",
    port=port,
    timeout_keep_alive=300,  # 5 minutes for long requests
    timeout_graceful_shutdown=30,
    limit_concurrency=None,
    access_log=True,
    use_colors=False,  # Disable colors for Azure logs
)
```

**Key Changes:**

- ✅ Proper uvicorn configuration
- ✅ Extended keep-alive timeout
- ✅ Disabled color output for Azure logs

### 2. `backend/web.config`

```xml
<!-- 10 minute timeout for long-running requests -->
<httpPlatform requestTimeout="00:10:00">
  <environmentVariables>
    <environmentVariable name="PYTHONUNBUFFERED" value="1"/>
  </environmentVariables>
</httpPlatform>

<!-- Disable response buffering -->
<httpProtocol>
  <customHeaders>
    <add name="X-Accel-Buffering" value="no" />
  </customHeaders>
</httpProtocol>
```

**Key Changes:**

- ✅ Extended request timeout to 10 minutes
- ✅ Disabled Python output buffering
- ✅ Disabled HTTP response buffering

### 3. `backend/app/routers/query_router.py`

**Streaming Endpoint Headers:**

```python
headers={
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
    "Content-Encoding": "none",
    "Access-Control-Allow-Origin": "*",
}
```

**Keep-Alive Mechanism:**

```python
# Send heartbeat every 15 seconds
if current_time - last_heartbeat > 15:
    yield ": heartbeat\n\n".encode("utf-8")
```

**Key Changes:**

- ✅ Anti-buffering headers
- ✅ Keep-alive heartbeat every 15 seconds
- ✅ Enhanced logging for debugging

---

## Debugging Tools

### 1. Check Azure Logs

```bash
# Via Azure CLI
az webapp log tail --name <your-app-name> --resource-group <your-rg>

# Via Portal
Portal → App Service → Monitoring → Log stream
```

### 2. Look for Debug Markers

The enhanced logging adds markers to help identify issues:

```
🚀 [AZURE-DEBUG] Starting SSE stream
📡 Sending initial keep-alive to establish connection
📊 [AZURE-DEBUG] Sending step X - Status: Y, Progress: Z%
🎯 [AZURE-DEBUG] Step X contains final_result (size: Y bytes)
✅ [AZURE-DEBUG] Step X sent successfully
💓 Sending keep-alive heartbeat
✅ [AZURE-DEBUG] Streaming completed successfully
```

### 3. Common Log Patterns

**Success Pattern:**

```
🚀 [AZURE-DEBUG] Starting SSE stream
📊 [AZURE-DEBUG] Sending step 1 - Status: processing, Progress: 20%
📊 [AZURE-DEBUG] Sending step 2 - Status: processing, Progress: 40%
...
📊 [AZURE-DEBUG] Sending step 5 - Status: completed, Progress: 100%
🎯 [AZURE-DEBUG] Step 5 contains final_result (size: 1234 bytes)
✅ [AZURE-DEBUG] Step 5 sent successfully
✅ [AZURE-DEBUG] Streaming completed successfully
   Total steps sent: 5
   Duration: 45.23s
   Has final result: True
```

**Failure Pattern (Buffering Issue):**

```
🚀 [AZURE-DEBUG] Starting SSE stream
📊 [AZURE-DEBUG] Sending step 1 - Status: processing, Progress: 20%
...
📊 [AZURE-DEBUG] Sending step 5 - Status: completed, Progress: 100%
🎯 [AZURE-DEBUG] Step 5 contains final_result (size: 1234 bytes)
✅ [AZURE-DEBUG] Step 5 sent successfully
# ⚠️ NO "Streaming completed successfully" message
# Connection dropped before final data reached client
```

**Failure Pattern (Timeout):**

```
🚀 [AZURE-DEBUG] Starting SSE stream
📊 [AZURE-DEBUG] Sending step 1 - Status: processing, Progress: 20%
💓 Sending keep-alive heartbeat
# ... long pause ...
❌ [AZURE-DEBUG] Streaming failed after 230.00s
   Error: Connection timeout
```

---

## Testing the Fix

### 1. Local Testing

```bash
cd backend
python startup.py
```

Test that streaming still works locally before deploying.

### 2. Azure Deployment

```bash
# Deploy to Azure
az webapp up --name <your-app-name> --resource-group <your-rg>

# Or use your existing deployment method
```

### 3. Test on Azure

1. Open your frontend connected to Azure backend
2. Run an analysis (e.g., "Water analysis of Mumbai")
3. Watch the progress reach 100%
4. **Verify final results are displayed** (not stuck)

### 4. Check Logs

```bash
az webapp log tail --name <your-app-name> --resource-group <your-rg>
```

Look for:

- ✅ "Streaming completed successfully"
- ✅ "Has final result: True"
- ✅ No connection timeout errors

---

## Common Issues After Fix

### Issue 1: Still Stuck at 100%

**Check:**

```bash
# Verify web.config was deployed
az webapp ssh --name <your-app-name>
cat web.config
```

**Verify:**

- `requestTimeout="00:10:00"` is present
- `PYTHONUNBUFFERED=1` is set
- `X-Accel-Buffering` header is present

**Solution:**

```bash
# Restart the app service
az webapp restart --name <your-app-name> --resource-group <your-rg>
```

### Issue 2: Connection Timeout

**Symptoms:**

- Logs show "Connection timeout" after ~230 seconds
- Azure default timeout is still active

**Solution:**
Check if you're behind Azure Application Gateway or Front Door:

```bash
# Application Gateway has its own timeout
az network application-gateway show --name <gateway-name> --resource-group <rg>
```

If using Application Gateway, set backend timeout:

```bash
az network application-gateway http-settings update \
  --gateway-name <gateway-name> \
  --name <settings-name> \
  --resource-group <rg> \
  --timeout 600  # 10 minutes
```

### Issue 3: Frontend Not Receiving Events

**Check Browser Console:**

```javascript
// You should see:
📊 Received step data: {step: 1, status: "processing", ...}
📊 Received step data: {step: 2, status: "processing", ...}
...
📊 Received step data: {step: 5, status: "completed", final_result: {...}}
```

**If missing final_result:**

- Check Azure logs for "Step 5 contains final_result"
- If present in logs but not in browser, it's a buffering issue
- Verify headers are correctly set in the response

### Issue 4: CORS Errors

**Symptoms:**

```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Solution:**
Add frontend origin to Azure App Service CORS settings:

```bash
az webapp cors add \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --allowed-origins "https://your-frontend.vercel.app"
```

Or in code (`backend/app/main.py`):

```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Performance Optimization

### 1. Reduce ROI Complexity

Large polygons can cause serialization delays:

```python
# Already implemented in simple_step_processor.py
simplified_roi = self._simplify_roi_for_streaming(roi)
```

This reduces polygon points from 100+ to ~5 for streaming.

### 2. Monitor Response Size

```bash
# Check final_result size in logs
🎯 [AZURE-DEBUG] Step 5 contains final_result (size: 1234 bytes)
```

If size > 1MB, consider:

- Compressing tile URLs
- Removing unnecessary fields
- Using references instead of full data

### 3. Enable CDN (Optional)

For faster tile delivery:

```bash
az cdn endpoint create \
  --name <endpoint-name> \
  --profile-name <profile-name> \
  --resource-group <your-rg> \
  --origin <your-app-name>.azurewebsites.net
```

---

## Environment Variables

Set these in Azure App Service Configuration:

```bash
# Via Azure CLI
az webapp config appsettings set \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --settings \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    DEBUG=false
```

**Recommended Settings:**

- `PYTHONUNBUFFERED=1` - Disable Python buffering (critical)
- `LOG_LEVEL=INFO` - Enable detailed logging
- `DEBUG=false` - Production mode
- `ALLOWED_ORIGINS=https://your-frontend.com` - CORS origins

---

## Monitoring

### 1. Application Insights (Recommended)

```bash
az monitor app-insights component create \
  --app <your-app-name> \
  --location <location> \
  --resource-group <your-rg>
```

### 2. Custom Metrics

Track streaming performance:

- Average stream duration
- Success rate
- Final result delivery rate

### 3. Alerts

Set up alerts for:

- High error rate
- Long response times (> 3 minutes)
- Connection timeouts

---

## Success Checklist

After applying fixes, verify:

- [ ] `startup.py` uses `uvicorn.run()` with proper config
- [ ] `web.config` has `requestTimeout="00:10:00"`
- [ ] `web.config` has `PYTHONUNBUFFERED=1`
- [ ] `web.config` has `X-Accel-Buffering: no` header
- [ ] Streaming endpoint has anti-buffering headers
- [ ] Keep-alive heartbeat is working (check logs)
- [ ] Enhanced logging is active
- [ ] App service restarted after config changes
- [ ] Test analysis completes and shows final results
- [ ] No "stuck at 100%" issues
- [ ] Azure logs show "Streaming completed successfully"

---

## Contact & Support

If issues persist after applying all fixes:

1. **Check Logs First:** Look for `[AZURE-DEBUG]` markers
2. **Verify Configuration:** Ensure all files were deployed correctly
3. **Test Locally:** Confirm it works on local machine
4. **Network Issues:** Check if behind Application Gateway/Front Door
5. **Azure Support:** Consider opening an Azure support ticket for platform-specific issues

---

## Additional Resources

- [Azure App Service Docs](https://docs.microsoft.com/en-us/azure/app-service/)
- [FastAPI Streaming](https://fastapi.tiangolo.com/advanced/custom-response/)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Azure App Service Timeouts](https://docs.microsoft.com/en-us/azure/app-service/faq-app-service-linux#why-are-my-requests-timing-out-)

# Azure Deployment Checklist

Quick reference for deploying the GeoLLM backend to Azure App Service with streaming support.

## Pre-Deployment Checklist

### 1. Files to Deploy

Ensure these modified files are included in your deployment:

- ✅ `backend/startup.py` - Fixed uvicorn configuration
- ✅ `backend/web.config` - Azure-specific timeout and buffering settings
- ✅ `backend/app/routers/query_router.py` - Enhanced streaming with keep-alive
- ✅ `backend/app/main.py` - Main application
- ✅ `backend/requirements.txt` or `requirements-minimal.txt`

### 2. Environment Variables to Set

Configure these in Azure App Service → Configuration → Application settings:

```bash
PYTHONUNBUFFERED=1              # Critical for streaming
LOG_LEVEL=INFO                  # Enable detailed logs
DEBUG=false                     # Production mode
OPENROUTER_API_KEY=<your-key>   # Your API key
GEE_PROJECT=<your-project>      # Google Earth Engine project
ALLOWED_ORIGINS=https://your-frontend.com  # CORS
```

### 3. Python Version

Ensure Python 3.11 is selected in Azure:

- Portal → Configuration → General Settings → Stack → Python 3.11

---

## Deployment Methods

### Method 1: Azure CLI (Recommended)

```bash
# Login
az login

# Set subscription
az account set --subscription <subscription-id>

# Deploy
cd backend
az webapp up \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --runtime "PYTHON:3.11" \
  --sku B1

# Set environment variables
az webapp config appsettings set \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --settings \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    DEBUG=false
```

### Method 2: Git Deployment

```bash
# Add Azure remote
az webapp deployment source config-local-git \
  --name <your-app-name> \
  --resource-group <your-rg>

# Get deployment URL
az webapp deployment list-publishing-credentials \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --query scmUri --output tsv

# Deploy
cd backend
git remote add azure <deployment-url>
git push azure master
```

### Method 3: VS Code Extension

1. Install "Azure App Service" extension
2. Right-click on `backend` folder
3. Select "Deploy to Web App..."
4. Choose your app service

---

## Post-Deployment Verification

### 1. Check Deployment Status

```bash
az webapp show --name <your-app-name> --resource-group <your-rg> --query state
```

Should return: `"Running"`

### 2. View Logs

```bash
# Stream logs in real-time
az webapp log tail --name <your-app-name> --resource-group <your-rg>

# Or via portal
Portal → App Service → Monitoring → Log stream
```

Look for:

```
✅ GeoLLM Backend started successfully!
📡 Listening on 0.0.0.0:8000
```

### 3. Test Health Endpoint

```bash
curl https://<your-app-name>.azurewebsites.net/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "geollm-backend",
  "services": {...}
}
```

### 4. Test Streaming Endpoint

```bash
# Test basic connectivity
curl -X POST https://<your-app-name>.azurewebsites.net/api/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "roi": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}' \
  --no-buffer
```

Should see streaming output starting with:

```
: keep-alive

data: {"step": 1, ...}
```

---

## Troubleshooting Quick Fixes

### Issue: App not starting

```bash
# Check logs
az webapp log tail --name <your-app-name> --resource-group <your-rg>

# Restart app
az webapp restart --name <your-app-name> --resource-group <your-rg>
```

### Issue: Still stuck at 100%

1. Verify `web.config` was deployed:

   ```bash
   az webapp ssh --name <your-app-name>
   cat web.config
   ```

2. Restart app:

   ```bash
   az webapp restart --name <your-app-name> --resource-group <your-rg>
   ```

3. Check response headers:
   ```bash
   curl -I https://<your-app-name>.azurewebsites.net/api/query/stream
   ```
   Should include: `X-Accel-Buffering: no`

### Issue: CORS errors

```bash
az webapp cors add \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --allowed-origins "https://your-frontend.com"
```

### Issue: Timeout errors

Check if behind Application Gateway:

```bash
az network application-gateway http-settings update \
  --gateway-name <gateway-name> \
  --name <settings-name> \
  --resource-group <rg> \
  --timeout 600
```

---

## Monitoring Setup (Optional but Recommended)

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app <your-app-name> \
  --location <location> \
  --resource-group <your-rg>

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app <your-app-name> \
  --resource-group <your-rg> \
  --query instrumentationKey -o tsv)

# Add to app settings
az webapp config appsettings set \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

### Set Up Alerts

```bash
# Alert for high error rate
az monitor metrics alert create \
  --name high-error-rate \
  --resource-group <your-rg> \
  --scopes /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Web/sites/<app-name> \
  --condition "avg Http5xx > 10" \
  --window-size 5m \
  --evaluation-frequency 1m
```

---

## Performance Optimization

### 1. Scale Up (Vertical)

```bash
# Upgrade to Premium plan for better performance
az appservice plan update \
  --name <plan-name> \
  --resource-group <your-rg> \
  --sku P1V2
```

### 2. Scale Out (Horizontal)

```bash
# Add more instances
az appservice plan update \
  --name <plan-name> \
  --resource-group <your-rg> \
  --number-of-workers 3
```

### 3. Enable CDN for Tile Delivery

```bash
az cdn endpoint create \
  --name <endpoint-name> \
  --profile-name <profile-name> \
  --resource-group <your-rg> \
  --origin <your-app-name>.azurewebsites.net \
  --origin-host-header <your-app-name>.azurewebsites.net
```

---

## Cost Management

### Recommended Tiers

**Development/Testing:**

- Free (F1) - Limited, no custom domain
- Basic (B1) - $13/month, good for testing

**Production:**

- Standard (S1) - $70/month, auto-scale support
- Premium (P1V2) - $146/month, better performance

### Monitor Costs

```bash
az consumption usage list \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --query "[?contains(instanceName, '<your-app-name>')]"
```

---

## Security Best Practices

### 1. Use Managed Identity (Recommended)

```bash
# Enable managed identity
az webapp identity assign \
  --name <your-app-name> \
  --resource-group <your-rg>

# Grant access to Key Vault
az keyvault set-policy \
  --name <vault-name> \
  --object-id <identity-id> \
  --secret-permissions get list
```

### 2. Store Secrets in Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name <vault-name> \
  --resource-group <your-rg> \
  --location <location>

# Add secrets
az keyvault secret set \
  --vault-name <vault-name> \
  --name OPENROUTER-API-KEY \
  --value <your-key>

# Reference in app settings
az webapp config appsettings set \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --settings OPENROUTER_API_KEY="@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/OPENROUTER-API-KEY/)"
```

### 3. Enable HTTPS Only

```bash
az webapp update \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --https-only true
```

---

## Rollback Plan

### Quick Rollback

```bash
# List deployment slots
az webapp deployment slot list \
  --name <your-app-name> \
  --resource-group <your-rg>

# Swap slots (if using staging)
az webapp deployment slot swap \
  --name <your-app-name> \
  --resource-group <your-rg> \
  --slot staging

# Or redeploy previous version
git push azure <previous-commit>:master --force
```

---

## Final Verification Checklist

After deployment, verify:

- [ ] App is running: `az webapp show ... --query state`
- [ ] Health endpoint returns 200: `/health`
- [ ] Logs show startup messages
- [ ] Environment variables are set
- [ ] `web.config` is deployed correctly
- [ ] CORS is configured for frontend
- [ ] Test streaming analysis completes without getting stuck
- [ ] Azure logs show `[AZURE-DEBUG]` markers
- [ ] Final results are displayed (not stuck at 100%)
- [ ] No timeout errors in logs
- [ ] Application Insights is collecting data (if enabled)

---

## Common Commands Reference

```bash
# View logs
az webapp log tail --name <app> --resource-group <rg>

# Restart app
az webapp restart --name <app> --resource-group <rg>

# SSH into app
az webapp ssh --name <app> --resource-group <rg>

# View config
az webapp config show --name <app> --resource-group <rg>

# Update settings
az webapp config appsettings set --name <app> --resource-group <rg> --settings KEY=VALUE

# View deployment history
az webapp deployment list-publishing-profiles --name <app> --resource-group <rg>
```

---

## Support Resources

- **Azure Docs:** https://docs.microsoft.com/azure/app-service/
- **Troubleshooting Guide:** See `AZURE_TROUBLESHOOTING.md`
- **Azure Support:** Portal → Help + Support → New support request
- **Community:** Stack Overflow tag: `azure-app-service`

---

**Last Updated:** October 31, 2025
**Azure SDK Version:** azure-cli 2.55+

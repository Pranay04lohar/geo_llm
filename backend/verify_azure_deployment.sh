#!/bin/bash

# Azure Deployment Verification Script
# This script verifies that all anti-buffering configurations are properly deployed

echo "🔍 Azure Streaming Deployment Verification"
echo "=========================================="
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install it first."
    exit 1
fi

# Get app name and resource group
read -p "Enter your Azure App Service name: " APP_NAME
read -p "Enter your resource group name: " RG_NAME

echo ""
echo "🔍 Checking deployment for: $APP_NAME"
echo "=========================================="
echo ""

# 1. Check if app is running
echo "1️⃣ Checking if app is running..."
STATE=$(az webapp show --name $APP_NAME --resource-group $RG_NAME --query state -o tsv 2>/dev/null)
if [ "$STATE" == "Running" ]; then
    echo "   ✅ App is running"
else
    echo "   ❌ App is NOT running (State: $STATE)"
    exit 1
fi

echo ""

# 2. Check environment variables
echo "2️⃣ Checking environment variables..."
PYTHONUNBUFFERED=$(az webapp config appsettings list --name $APP_NAME --resource-group $RG_NAME --query "[?name=='PYTHONUNBUFFERED'].value" -o tsv 2>/dev/null)
if [ "$PYTHONUNBUFFERED" == "1" ]; then
    echo "   ✅ PYTHONUNBUFFERED is set to 1"
else
    echo "   ❌ PYTHONUNBUFFERED is NOT set!"
    echo "   🔧 Fixing now..."
    az webapp config appsettings set --name $APP_NAME --resource-group $RG_NAME --settings PYTHONUNBUFFERED=1
    echo "   ✅ PYTHONUNBUFFERED set to 1"
fi

echo ""

# 3. Check Python version
echo "3️⃣ Checking Python version..."
PYTHON_VERSION=$(az webapp config show --name $APP_NAME --resource-group $RG_NAME --query linuxFxVersion -o tsv 2>/dev/null)
echo "   Python version: $PYTHON_VERSION"
if [[ "$PYTHON_VERSION" == *"PYTHON|3.11"* ]] || [[ "$PYTHON_VERSION" == *"PYTHON|3.10"* ]]; then
    echo "   ✅ Python version is OK"
else
    echo "   ⚠️  Python version might be old. Recommended: Python 3.11"
fi

echo ""

# 4. Test health endpoint
echo "4️⃣ Testing health endpoint..."
HEALTH_URL="https://${APP_NAME}.azurewebsites.net/health"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
if [ "$HTTP_CODE" == "200" ]; then
    echo "   ✅ Health endpoint returns 200 OK"
else
    echo "   ❌ Health endpoint returned: $HTTP_CODE"
fi

echo ""

# 5. Test streaming endpoint headers
echo "5️⃣ Testing streaming endpoint headers..."
STREAM_URL="https://${APP_NAME}.azurewebsites.net/api/query/stream"
echo "   Testing: $STREAM_URL"

HEADERS=$(curl -I -X OPTIONS $STREAM_URL 2>/dev/null)

# Check for critical headers
if echo "$HEADERS" | grep -q "X-Accel-Buffering: no"; then
    echo "   ✅ X-Accel-Buffering: no header present"
else
    echo "   ❌ X-Accel-Buffering: no header MISSING!"
fi

if echo "$HEADERS" | grep -q "Cache-Control"; then
    echo "   ✅ Cache-Control header present"
else
    echo "   ⚠️  Cache-Control header missing"
fi

echo ""

# 6. Check recent logs for errors
echo "6️⃣ Checking recent logs..."
echo "   (Showing last 50 lines, looking for errors...)"
az webapp log tail --name $APP_NAME --resource-group $RG_NAME --output tsv 2>/dev/null | tail -50 | grep -i "error\|exception\|failed" || echo "   ✅ No recent errors found"

echo ""

# 7. Check if web.config exists
echo "7️⃣ Verifying web.config..."
echo "   Attempting to SSH and check web.config..."
# Note: SSH requires the app to be on a paid tier
WEB_CONFIG_CHECK=$(az webapp ssh --name $APP_NAME --resource-group $RG_NAME --command "cat web.config | grep 'X-Accel-Buffering'" 2>/dev/null)
if [ -n "$WEB_CONFIG_CHECK" ]; then
    echo "   ✅ web.config contains X-Accel-Buffering directive"
else
    echo "   ⚠️  Could not verify web.config (SSH might not be available on Free tier)"
fi

echo ""
echo "=========================================="
echo "🎯 VERIFICATION COMPLETE"
echo "=========================================="
echo ""

# Recommendations
echo "📋 RECOMMENDATIONS:"
echo ""
if [ "$PYTHONUNBUFFERED" != "1" ]; then
    echo "   ⚠️  Set PYTHONUNBUFFERED=1 in App Settings"
fi

echo "   🔄 Restart your app after deploying changes:"
echo "      az webapp restart --name $APP_NAME --resource-group $RG_NAME"
echo ""
echo "   📝 Deploy the updated code:"
echo "      cd backend && az webapp up --name $APP_NAME --resource-group $RG_NAME"
echo ""
echo "   🔍 Monitor logs in real-time:"
echo "      az webapp log tail --name $APP_NAME --resource-group $RG_NAME"
echo ""
echo "   🧪 Test streaming analysis and look for:"
echo "      ✅ [AZURE-DEBUG] Streaming completed successfully"
echo "      ✅ Has final result: True"
echo ""


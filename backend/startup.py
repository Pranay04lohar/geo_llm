import os
import sys
import uvicorn

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    # Azure-compatible uvicorn configuration
    # These settings are critical for Azure App Service deployment
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        timeout_keep_alive=300,  # 5 minutes keep-alive for long-running requests
        timeout_graceful_shutdown=30,
        limit_concurrency=None,  # No concurrency limits for Azure
        limit_max_requests=None,  # No max requests limit
        access_log=True,
        use_colors=False,  # Disable colors for Azure logs
        # Azure-specific: Disable buffering for streaming responses
        headers=[
            ("X-Accel-Buffering", "no"),  # Nginx buffering control
            ("Cache-Control", "no-cache"),  # Prevent caching
        ]
    )
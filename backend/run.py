import os

import uvicorn

if __name__ == "__main__":
    # Railway (and most PaaS) inject the port to bind via the PORT env var.
    port = int(os.getenv("PORT", "8000"))
    # reload is for local dev only; disable it in production (Railway).
    reload = os.getenv("ENV", "development").lower() != "production"
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)

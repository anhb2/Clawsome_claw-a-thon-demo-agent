"""Agent entrypoint for GreenNode AgentBase Runtime."""

import os

from dotenv import load_dotenv

from app.server import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(port=port, host="0.0.0.0")

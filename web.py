import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    # Returns HTTP 200 OK to tell Koyeb the service is alive
    return "Bot is running perfectly!", 200

def run_server():
    # Koyeb passes the port via the PORT environment variable (defaults to 8000)
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

"""One-time Google login inside Docker:
docker compose run --rm -p 8765:8765 web python google_login.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow

import config
from services.calendar_svc import SCOPES

flow = InstalledAppFlow.from_client_secrets_file(config.GOOGLE_CREDENTIALS, SCOPES)
creds = flow.run_local_server(
    host="localhost", bind_addr="0.0.0.0", port=8765, open_browser=False,
    prompt="consent",  # forces Google to issue a refresh_token
    authorization_prompt_message="\n👉 Buka URL ini di browser:\n{url}\n",
)
with open(config.GOOGLE_TOKEN, "w") as f:
  f.write(creds.to_json())
print("✅ TOKEN SAVED ->", config.GOOGLE_TOKEN)
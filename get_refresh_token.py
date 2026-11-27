import json
import subprocess
import webbrowser
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    scopes=SCOPES,
)

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

class ChromeProfileLauncher:
    def open(self, url, new=0, autoraise=True):
        with open("auth_url.txt", "w", encoding="utf-8") as f:
            f.write(url)
        subprocess.Popen([
            chrome_path,
            '--profile-directory=Profile 3',
            url
        ])
        return True

webbrowser.register('custom_chrome', None, ChromeProfileLauncher(), preferred=True)

print("AUTH_SERVER_STARTED", flush=True)
creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline", open_browser=True)

# Update local .env
env_path = Path(".env")
if env_path.exists():
    lines = [l for l in env_path.read_text(encoding="utf-8").splitlines() if not l.startswith("YT_REFRESH_TOKEN=")]
    lines.append(f"YT_REFRESH_TOKEN={creds.refresh_token}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n[SUCCESS] Token .env dosyasina kaydedildi!", flush=True)

# Update GitHub Secrets automatically
for repo in ["berktasbaran6-tech/history-long-bot", "berktasbaran6-tech/kids-shorts-bot"]:
    try:
        res = subprocess.run(["gh", "secret", "set", "YT_REFRESH_TOKEN", "--body", creds.refresh_token, "--repo", repo], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SUCCESS] GitHub Actions Secret 'YT_REFRESH_TOKEN' ({repo}) guncellendi!", flush=True)
        else:
            print(f"[WARN] gh secret error for {repo}: {res.stderr}", flush=True)
    except Exception as e:
        print(f"[WARN] GitHub Secret guncellenemedi: {e}", flush=True)

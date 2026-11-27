"""YouTube iznini yeniler: tarayici acar, izin alinca anahtari .env ve GitHub'a kaydeder."""
import subprocess
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

print("=" * 60)
print(" YOUTUBE IZNI YENILENIYOR")
print(" Simdi tarayicin acilacak. YouTube kanalinin oldugu hesabi sec.")
print(" 'Dogrulanmadi' uyarisi cikarsa: Gelismis -> Devam et -> Izin ver")
print("=" * 60)

flow = InstalledAppFlow.from_client_secrets_file(str(ROOT / "client_secret.json"), scopes=SCOPES)
creds = flow.run_local_server(
    port=0,
    prompt="consent",
    access_type="offline",
    open_browser=True,
    authorization_prompt_message="\nTarayici acilmazsa bu linki kopyalayip Chrome'a yapistir:\n{url}\n",
    success_message="Tamam! Izin alindi. Bu sekmeyi kapatabilirsin.",
)

token = creds.refresh_token
if not token:
    print("\n[HATA] Google yeni anahtar vermedi. Tekrar dene.")
    raise SystemExit(1)

env_path = ROOT / ".env"
lines = []
if env_path.exists():
    lines = [l for l in env_path.read_text(encoding="utf-8-sig").splitlines()
             if not l.startswith("YT_REFRESH_TOKEN=")]
lines.append(f"YT_REFRESH_TOKEN={token}")
env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n[OK] Anahtar bilgisayara kaydedildi.")

res = subprocess.run(
    ["gh", "secret", "set", "YT_REFRESH_TOKEN", "--body", token,
     "--repo", "berktasbaran6-tech/history-long-bot"],
    capture_output=True, text=True,
)
if res.returncode == 0:
    print("[OK] Anahtar GitHub'a kaydedildi. Bot artik yukleyebilir.")
else:
    print("[UYARI] GitHub'a kaydedilemedi:", res.stderr)

print("\nBITTI. Bu pencereyi kapatabilirsin.")

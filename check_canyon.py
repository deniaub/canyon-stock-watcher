"""
Canyon Stock Watcher
Surveille la disponibilité d'une variante précise d'un vélo Canyon et notifie via ntfy.sh.
"""

import json
import os
from datetime import datetime, timezone

import requests

# ── Configuration ──────────────────────────────────────────────────────────────
PRODUCT_URL = (
    "https://www.canyon.com/fr-fr/velos-de-route/velos-endurance/endurace/cf-slx/"
    "endurace-cf-slx-8-di2/4432.html"
    "?dwvar_4432_pv_rahmenfarbe=R130_P02&dwvar_4432_pv_rahmengroesse=S"
)
PRODUCT_LABEL = "Canyon Endurace CF SLX 8 Di2 (R130_P02, taille S)"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "canyon-endurace-23t2ntqyf7")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

OUT_OF_STOCK_MARKERS = [
    "Prévenez-moi",
    "Bientôt disponible",
    "n'est pas disponible",
    "Rupture de stock",
]
IN_STOCK_MARKER = "Ajouter au panier"

REMIND_INTERVAL_MIN = 20  # relance de notif tant que le vélo reste en stock


# ── État persistant ────────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ── Vérification du stock ──────────────────────────────────────────────────────
def check_stock():
    r = requests.get(PRODUCT_URL, headers=REQUEST_HEADERS, timeout=20)
    r.raise_for_status()
    html = r.text

    if any(marker in html for marker in OUT_OF_STOCK_MARKERS):
        return "out_of_stock"
    if IN_STOCK_MARKER in html:
        return "in_stock"
    return "unknown"


# ── Notification ────────────────────────────────────────────────────────────────
def notify(status):
    if status == "in_stock":
        title = "Canyon - Velo disponible !"
        message = f"{PRODUCT_LABEL} est disponible a l'achat.\n{PRODUCT_URL}"
        priority = "urgent"
        tags = "rotating_light,bike"
    else:  # unknown
        title = "Canyon Watcher - statut incertain"
        message = (
            f"Impossible de determiner la disponibilite de {PRODUCT_LABEL}. "
            "Verification manuelle recommandee.\n" + PRODUCT_URL
        )
        priority = "default"
        tags = "warning"

    requests.post(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": tags,
            "Click": PRODUCT_URL,
        },
        timeout=15,
    )


def maybe_notify(status):
    state = load_state()
    last_status = state.get("last_status")
    last_notified_at = state.get("last_notified_at")
    now = datetime.now(timezone.utc)

    should_notify = False
    if status == "in_stock":
        if last_status != "in_stock":
            should_notify = True
        elif last_notified_at:
            elapsed_min = (now - datetime.fromisoformat(last_notified_at)).total_seconds() / 60
            should_notify = elapsed_min >= REMIND_INTERVAL_MIN
        else:
            should_notify = True
    elif status == "unknown" and last_status != "unknown":
        should_notify = True

    if should_notify:
        notify(status)
        state["last_notified_at"] = now.isoformat()

    state["last_status"] = status
    state["last_checked_at"] = now.isoformat()
    save_state(state)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print(f"\n=== Canyon Stock Watcher — {datetime.now().isoformat(timespec='seconds')} ===")
    try:
        if os.environ.get("TEST_NOTIFICATION") == "true":
            print("Mode test : envoi d'une notification factice, aucun état modifié.")
            notify("in_stock")
            return
        status = check_stock()
        print(f"Statut : {status}")
        maybe_notify(status)
    except Exception as e:
        print(f"✗ Erreur : {e}")
        raise


if __name__ == "__main__":
    main()

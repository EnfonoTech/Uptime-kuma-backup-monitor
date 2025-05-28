import os
import requests
from datetime import datetime, timedelta
import frappe

def check_google_backup():
    try:
        site = frappe.local.site
        backup_path = frappe.get_site_path("private", "backups")
        now = datetime.now()

        recent_backup = False
        for file in os.listdir(backup_path):
            if file.endswith(".sql.gz"):
                modified_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(backup_path, file)))
                if (now - modified_time) < timedelta(hours=24):
                    recent_backup = True
                    break

        status = "up" if recent_backup else "down"
        msg = f"{site}: Google Backup {'OK' if recent_backup else 'Missing'}"

        push_to_kuma(status, msg)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Backup Check Error")
        push_to_kuma("down", f"{site}: Error - {str(e)}")

def get_push_url():
    try:
        settings = frappe.get_single("Uptime Kuma Settings")
        return settings.push_url
    except Exception as e:
        frappe.log_error(f"Missing or invalid Push URL: {e}", "Kuma Backup Monitor")
        return None

def push_to_kuma(status, msg):
    url = get_push_url()
    if not url:
        return
    try:
        full_url = f"{url}?status={status}&msg={msg}"
        requests.get(full_url, timeout=10)
    except:
        frappe.log_error("Kuma push failed", "Kuma Backup Monitor")


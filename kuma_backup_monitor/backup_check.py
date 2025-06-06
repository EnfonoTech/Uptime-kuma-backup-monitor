from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import frappe
import requests
import os

def check_gdrive_backup():
    try:
        gdrive_settings = frappe.get_single("Google Drive")
        folder_id = gdrive_settings.backup_folder_id

        creds_dict = {
            "token": None,  # token will be refreshed
            "refresh_token": gdrive_settings.get_password("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": frappe.get_single("Google Settings").client_id,
            "client_secret": frappe.get_single("Google Settings").get_password("client_secret"),
            "scopes": ["https://www.googleapis.com/auth/drive"]
        }

        creds = Credentials.from_authorized_user_info(info=creds_dict)
        service = build("drive", "v3", credentials=creds)

        after_time = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
        query = f"'{folder_id}' in parents and modifiedTime > '{after_time}'"

        results = service.files().list(
            q=query,
            fields="files(name, modifiedTime)",
            orderBy="modifiedTime desc"
        ).execute()

        files = results.get("files", [])
        recent_backup_found = any(
            f["name"].endswith((".sql.gz", ".tgz")) for f in files
        )

        site = frappe.local.site
        status = "up" if recent_backup_found else "down"
        msg = f"{site}: Google Drive Backup {'OK' if recent_backup_found else 'Missing'}"
        push_to_kuma(status, msg)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Google Drive Check Error")
        push_to_kuma("down", f"{frappe.local.site}: Google Drive API Error")

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
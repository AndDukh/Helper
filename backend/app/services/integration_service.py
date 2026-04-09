import base64
import json
import os
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from ..models import IntegrationToken


class IntegrationService:
    def __init__(self) -> None:
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        self.google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
        self.google_access_token = os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN", "").strip()

        self.dropbox_client_id = os.getenv("DROPBOX_CLIENT_ID", "").strip()
        self.dropbox_client_secret = os.getenv("DROPBOX_CLIENT_SECRET", "").strip()
        self.dropbox_redirect_uri = os.getenv("DROPBOX_REDIRECT_URI", "").strip()
        self.dropbox_access_token = os.getenv("DROPBOX_ACCESS_TOKEN", "").strip()
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

    def is_connected(self, db: Session, service: str) -> bool:
        db_token = db.query(IntegrationToken).filter(IntegrationToken.service == service).first()
        if db_token:
            return True
        if service == "google_drive":
            return bool(self.google_access_token)
        if service == "dropbox":
            return bool(self.dropbox_access_token)
        return False

    def _token_for(self, db: Session, service: str) -> str:
        db_token = db.query(IntegrationToken).filter(IntegrationToken.service == service).first()
        if db_token:
            return db_token.access_token
        return self.google_access_token if service == "google_drive" else self.dropbox_access_token

    def _save_token(self, db: Session, service: str, token: str) -> None:
        row = db.query(IntegrationToken).filter(IntegrationToken.service == service).first()
        if row:
            row.access_token = token
        else:
            row = IntegrationToken(service=service, access_token=token)
            db.add(row)
        db.commit()

    def connect(self, service: str) -> dict[str, str]:
        if service == "google_drive":
            if not self.google_client_id or not self.google_redirect_uri:
                return {
                    "service": service,
                    "status": "auth_required",
                    "auth_url": "",
                    "note": "Set GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI to enable Google OAuth.",
                }
            qs = urlencode(
                {
                    "client_id": self.google_client_id,
                    "redirect_uri": self.google_redirect_uri,
                    "response_type": "code",
                    "scope": "https://www.googleapis.com/auth/drive.file",
                    "access_type": "offline",
                    "prompt": "consent",
                }
            )
            return {
                "service": service,
                "status": "auth_ready",
                "auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?{qs}",
                "note": "Open auth_url, complete OAuth, then set GOOGLE_DRIVE_ACCESS_TOKEN.",
            }

        if service == "dropbox":
            if not self.dropbox_client_id or not self.dropbox_redirect_uri:
                return {
                    "service": service,
                    "status": "auth_required",
                    "auth_url": "",
                    "note": "Set DROPBOX_CLIENT_ID and DROPBOX_REDIRECT_URI to enable Dropbox OAuth.",
                }
            qs = urlencode(
                {
                    "client_id": self.dropbox_client_id,
                    "response_type": "code",
                    "redirect_uri": self.dropbox_redirect_uri,
                    "token_access_type": "offline",
                }
            )
            return {
                "service": service,
                "status": "auth_ready",
                "auth_url": f"https://www.dropbox.com/oauth2/authorize?{qs}",
                "note": "Open auth_url, complete OAuth, then set DROPBOX_ACCESS_TOKEN.",
            }

        return {
            "service": service,
            "status": "unsupported",
            "auth_url": "",
            "note": "This integration is not implemented yet.",
        }

    async def exchange_oauth_code(self, db: Session, service: str, code: str) -> dict[str, str]:
        if service == "google_drive":
            return await self._exchange_google_code(db, code)
        if service == "dropbox":
            return await self._exchange_dropbox_code(db, code)
        return {
            "service": service,
            "status": "unsupported",
            "auth_url": "",
            "note": "OAuth exchange is not implemented for this service.",
        }

    async def _exchange_google_code(self, db: Session, code: str) -> dict[str, str]:
        if not self.google_client_id or not self.google_client_secret or not self.google_redirect_uri:
            return {
                "service": "google_drive",
                "status": "auth_required",
                "auth_url": "",
                "note": "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI.",
            }
        payload = {
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.google_redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data=payload)
            resp.raise_for_status()
            data = resp.json()
        token = (data.get("access_token") or "").strip()
        if not token:
            return {
                "service": "google_drive",
                "status": "error",
                "auth_url": "",
                "note": "Google token response did not include access_token.",
            }
        self._save_token(db, "google_drive", token)
        return {
            "service": "google_drive",
            "status": "connected",
            "auth_url": "",
            "note": "Google Drive connected via OAuth callback.",
        }

    async def _exchange_dropbox_code(self, db: Session, code: str) -> dict[str, str]:
        if not self.dropbox_client_id or not self.dropbox_client_secret or not self.dropbox_redirect_uri:
            return {
                "service": "dropbox",
                "status": "auth_required",
                "auth_url": "",
                "note": "Set DROPBOX_CLIENT_ID, DROPBOX_CLIENT_SECRET and DROPBOX_REDIRECT_URI.",
            }
        payload = {
            "code": code,
            "client_id": self.dropbox_client_id,
            "client_secret": self.dropbox_client_secret,
            "redirect_uri": self.dropbox_redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.dropboxapi.com/oauth2/token", data=payload)
            resp.raise_for_status()
            data = resp.json()
        token = (data.get("access_token") or "").strip()
        if not token:
            return {
                "service": "dropbox",
                "status": "error",
                "auth_url": "",
                "note": "Dropbox token response did not include access_token.",
            }
        self._save_token(db, "dropbox", token)
        return {
            "service": "dropbox",
            "status": "connected",
            "auth_url": "",
            "note": "Dropbox connected via OAuth callback.",
        }

    async def upload_material(
        self,
        db: Session,
        service: str,
        filename: str,
        mime_type: str,
        content_base64: str,
        folder: Optional[str] = None,
    ) -> dict[str, str]:
        raw = base64.b64decode(content_base64)

        if service == "google_drive":
            token = self._token_for(db, "google_drive")
            if not token:
                return {
                    "service": service,
                    "status": "auth_required",
                    "location": "",
                    "note": "Set GOOGLE_DRIVE_ACCESS_TOKEN in backend env.",
                }
            metadata = {"name": filename}
            if folder:
                metadata["parents"] = [folder]
            headers = {"Authorization": f"Bearer {token}"}
            files = {
                "metadata": ("metadata", json.dumps(metadata), "application/json"),
                "file": (filename, raw, mime_type),
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                    headers=headers,
                    files=files,
                )
                resp.raise_for_status()
                data = resp.json()
            file_id = data.get("id", "")
            return {
                "service": service,
                "status": "uploaded",
                "location": f"https://drive.google.com/file/d/{file_id}/view" if file_id else "",
                "note": "Material uploaded to Google Drive.",
            }

        if service == "dropbox":
            token = self._token_for(db, "dropbox")
            if not token:
                return {
                    "service": service,
                    "status": "auth_required",
                    "location": "",
                    "note": "Set DROPBOX_ACCESS_TOKEN in backend env.",
                }
            path = f"/{filename}" if not folder else f"/{folder.strip('/')}/{filename}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Dropbox-API-Arg": json.dumps(
                    {"path": path, "mode": "add", "autorename": True, "mute": False}
                ),
                "Content-Type": "application/octet-stream",
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://content.dropboxapi.com/2/files/upload",
                    headers=headers,
                    content=raw,
                )
                resp.raise_for_status()
            return {
                "service": service,
                "status": "uploaded",
                "location": path,
                "note": "Material uploaded to Dropbox.",
            }

        return {
            "service": service,
            "status": "unsupported",
            "location": "",
            "note": "This integration is not implemented yet.",
        }

"""Gmail API wrapper: OAuth auth, list messages by date with attachment, get sender."""

from __future__ import annotations

import base64
import re
from datetime import date
from pathlib import Path
from typing import List, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Read-only scope for Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Gmail search for messages with image attachments (common extensions)
ATTACHMENT_QUERY = "has:attachment (filename:jpg OR filename:jpeg OR filename:png OR filename:heic OR filename:gif)"


def get_credentials(config_dir: Path, credentials_file: str = "credentials.json") -> Credentials:
    """
    Obtain Gmail API credentials via OAuth. Uses token.json for cached credentials.
    First run opens a browser to log in.
    """
    creds = None
    token_path = config_dir / "token.json"
    creds_path = config_dir / credentials_file
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Gmail credentials not found at:\n  {creds_path}\n\n"
            "To fix this:\n"
            "  1. Go to https://console.cloud.google.com/\n"
            "  2. Create or select a project → enable 'Gmail API'\n"
            "  3. APIs & Services → Credentials → Create Credentials → OAuth client ID\n"
            "  4. Application type: Desktop app → Create\n"
            "  5. Download the JSON and save it as 'credentials.json' in this folder:\n"
            f"     {config_dir}\n"
            "  6. Run the script again; a browser will open to sign in as mathcenter@peddie.org"
        )
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def build_service(config_dir: Path):
    """Build Gmail API service."""
    creds = get_credentials(config_dir)
    return build("gmail", "v1", credentials=creds)


def _after_date(d: date) -> str:
    """Gmail after: query format YYYY/MM/DD."""
    return d.strftime("%Y/%m/%d")


def _before_date(d: date) -> str:
    """Gmail before: is exclusive; use next day for inclusive."""
    from datetime import timedelta
    next_d = d + timedelta(days=1)
    return next_d.strftime("%Y/%m/%d")


def list_message_ids_with_attachment(
    service,
    after: date,
    before: date,
    to: str = "mathcenter@peddie.org",
) -> List[str]:
    """
    List Gmail message IDs in the inbox received between after (inclusive) and before (exclusive)
    that have an image attachment. Uses 'deliveredto' or 'to' for the address.
    """
    query_parts = [
        ATTACHMENT_QUERY,
        f"after:{_after_date(after)}",
        f"before:{_before_date(before)}",
    ]
    # Search in inbox; Gmail often stores "to" as the recipient
    query = " ".join(query_parts)
    try:
        results = service.users().messages().list(userId="me", q=query).execute()
    except HttpError as e:
        if e.resp.status == 403 and "accessNotConfigured" in str(e):
            raise RuntimeError(
                "Gmail API is not enabled for your Google Cloud project.\n"
                "Enable it here: https://console.cloud.google.com/apis/library/gmail.googleapis.com\n"
                "Select the same project that has your OAuth client, click Enable, wait a minute, then run the script again."
            ) from e
        raise
    messages = results.get("messages", [])
    return [m["id"] for m in messages]


def list_message_ids_to_mathcenter(
    service,
    after: date,
    before: date,
    to: str = "mathcenter@peddie.org",
) -> List[str]:
    """
    List all Gmail message IDs received between after (inclusive) and before (exclusive)
    sent to the given address (mathcenter). Used to find messages without image attachments.
    """
    query_parts = [
        f"to:{to}",
        f"after:{_after_date(after)}",
        f"before:{_before_date(before)}",
    ]
    query = " ".join(query_parts)
    try:
        results = service.users().messages().list(userId="me", q=query).execute()
    except HttpError as e:
        if e.resp.status == 403 and "accessNotConfigured" in str(e):
            raise RuntimeError(
                "Gmail API is not enabled for your Google Cloud project.\n"
                "Enable it here: https://console.cloud.google.com/apis/library/gmail.googleapis.com\n"
                "Select the same project that has your OAuth client, click Enable, wait a minute, then run the script again."
            ) from e
        raise
    messages = results.get("messages", [])
    return [m["id"] for m in messages]


def get_message_body(service, message_id: str) -> str:
    """
    Get the plain-text body of a message. Handles simple and multipart messages.
    Returns empty string if no text body found.
    """
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    body_data = payload.get("body", {}).get("data")
    if body_data:
        try:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace").strip()
        except Exception:
            pass
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            try:
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace").strip()
            except Exception:
                pass
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            try:
                html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                text = re.sub(r"<[^>]+>", " ", html)
                return " ".join(text.split()).strip()
            except Exception:
                pass
    return ""


def get_sender(service, message_id: str) -> Tuple[str, str]:
    """
    Get (email_address, display_name) for the sender of the message.
    display_name may be empty.
    """
    msg = service.users().messages().get(userId="me", id=message_id, format="metadata", metadataHeaders=["From"]).execute()
    headers = msg.get("payload", {}).get("headers", [])
    from_header = ""
    for h in headers:
        if h.get("name", "").lower() == "from":
            from_header = h.get("value", "")
            break
    # Parse "Display Name <email@example.com>" or just "email@example.com"
    email = ""
    name = ""
    if "<" in from_header and ">" in from_header:
        name = from_header.split("<")[0].strip().strip('"')
        email = from_header.split("<")[1].split(">")[0].strip().lower()
    else:
        from_header = from_header.strip()
        if "@" in from_header:
            email = from_header.lower()
        else:
            name = from_header
    return (email, name)


def get_senders_for_date(
    service,
    d: date,
    to: str = "mathcenter@peddie.org",
) -> List[Tuple[str, str]]:
    """
    Return list of (email, display_name) for messages received on date d
    that have an image attachment.
    """
    from datetime import timedelta
    day_after = d + timedelta(days=1)
    ids = list_message_ids_with_attachment(service, d, day_after, to=to)
    senders = []
    seen = set()
    for mid in ids:
        email, name = get_sender(service, mid)
        key = (email, name)
        if key not in seen:
            seen.add(key)
            senders.append((email, name))
    return senders


def get_senders_without_image_for_date(
    service,
    d: date,
    to: str = "mathcenter@peddie.org",
) -> List[Tuple[str, str]]:
    """
    Return list of (email, display_name) for messages received on date d
    that do NOT have an image attachment (possible excuse / no-photo emails).
    """
    from datetime import timedelta
    day_after = d + timedelta(days=1)
    with_image_ids = set(
        list_message_ids_with_attachment(service, d, day_after, to=to)
    )
    all_ids = set(list_message_ids_to_mathcenter(service, d, day_after, to=to))
    no_image_ids = all_ids - with_image_ids
    senders = []
    seen = set()
    for mid in no_image_ids:
        email, name = get_sender(service, mid)
        key = (email, name)
        if key not in seen:
            seen.add(key)
            senders.append((email, name))
    return senders


def get_no_image_messages_for_date(
    service,
    d: date,
    to: str = "mathcenter@peddie.org",
) -> List[Tuple[str, str, str]]:
    """
    Return list of (message_id, email, display_name) for messages received on date d
    that do NOT have an image attachment. Use for fetching body and LLM analysis.
    """
    from datetime import timedelta
    day_after = d + timedelta(days=1)
    with_image_ids = set(
        list_message_ids_with_attachment(service, d, day_after, to=to)
    )
    all_ids = list_message_ids_to_mathcenter(service, d, day_after, to=to)
    result = []
    for mid in all_ids:
        if mid in with_image_ids:
            continue
        email, name = get_sender(service, mid)
        result.append((mid, email, name))
    return result

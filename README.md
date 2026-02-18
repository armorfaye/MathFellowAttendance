# Math Fellow Attendance

A script that checks which math fellows submitted attendance by reading emails sent to **mathcenter@peddie.org**: it treats messages **with image attachments** as attendance submissions and reports messages **without images** as possible excuse requests.

## Features

- **Attendance from photo emails** – Queries Gmail for messages with image attachments (jpg, jpeg, png, heic, gif) on expected session dates and matches senders to fellows.
- **Reveal sender email** – For each fellow marked present, the script shows the matched sender email in the console and includes it in the CSV report.
- **Possible excuse emails** – Lists senders of messages to mathcenter on the same dates that do *not* have an image attachment. With a **Google Gemini API key** (free), the script uses Gemini to extract the **reason** given for absence and a **suggestion** (approve or reject) with a short explanation.
- **Blue / Gold weeks** – Uses `schedule.yaml` to determine expected fellows per session; supports `--week blue` or `--week gold`.
- **Holidays / days off** – Exclude dates with `--off YYYY-MM-DD` (e.g. holidays).
- **Custom date range** – Override the default (current week Sunday–Saturday) with `--start` and `--end`.
- **CSV export** – Optional `--output` file with columns: date, day, session, time, fellow, status, email.

## How it works

1. You run the script with the **week type** (Blue or Gold) and optionally **days off** and date range.
2. The script loads the schedule from `schedule.yaml`, determines which fellows were expected on which days/sessions.
3. It queries Gmail for:
   - **With image attachment** – Messages with image attachments on those dates → counted as attendance; senders are matched to fellows via `fellows.yaml` or name fallback.
   - **Without image attachment** – All other messages to mathcenter on those dates → listed in the final summary as “Possible excuse emails.”
4. It prints a per-session report (present/absent with email when present), a summary, and for each possible excuse email: sender, and if `GEMINI_API_KEY` is set, the **reason** extracted from the email and an **approve/reject suggestion** with explanation. You can also write the report to a CSV file.

## Setup

### 1. Python environment and dependencies

Use a Python 3 environment (e.g. conda or venv), then install dependencies:

```bash
cd MathFellowAttendance
conda activate myenv   # or: python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Gmail OAuth (one-time)

The script reads the **mathcenter@peddie.org** Gmail inbox. You need to authenticate once:

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or select one) and enable the **Gmail API**.
3. Under **APIs & Services → Credentials**, create an **OAuth 2.0 Client ID**.
   - Application type: **Desktop app**.
4. Download the JSON key and save it in this folder as **`credentials.json`**.

When you run the script for the first time, a browser window will open so you can log in as (or on behalf of) mathcenter@peddie.org. The token is stored in **`token.json`** so future runs do not require logging in again.

**Important:** Do not commit `credentials.json` or `token.json` to version control. They are listed in `.gitignore`.

### 3. Google Gemini API (optional, free – for excuse analysis)

To have the script analyze excuse emails (reason + approve/reject suggestion), set a **Gemini API key** (free):

```bash
export GEMINI_API_KEY=your-key-here
```

Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey). If `GEMINI_API_KEY` is not set, the script only lists possible excuse senders without LLM analysis. Use `--no-llm` to skip LLM even when the key is set.

### 4. Schedule and fellow mapping

- **`schedule.yaml`** – Blue/Gold schedule (session times and fellow assignments). Edit when session times or fellow lists change.
- **`fellows.yaml`** – Optional. Map fellow names to email addresses or display-name variants so the script can match senders to fellows. If a fellow has no entry, the script tries to match by name (e.g. "Jerry Liu" vs "Liu, Jerry").

## Usage

Activate your environment first:

```bash
conda activate myenv
```

### Basic (current week, Blue or Gold)

```bash
python attendance.py --week blue
```

or

```bash
python attendance.py --week gold
```

The script uses the **current week** (Sunday–Saturday) by default.

### With holidays (days off)

```bash
python attendance.py --week blue --off 2025-02-20
```

Multiple days off:

```bash
python attendance.py --week gold --off 2025-02-20 2025-02-21
```

### Custom date range

```bash
python attendance.py --week blue --start 2025-02-16 --end 2025-02-22
```

### Save report to CSV

```bash
python attendance.py --week blue --output attendance_2025-02-21.csv
```

The CSV includes columns: `date`, `day`, `session`, `time`, `fellow`, `status`, `email` (the matched sender email when present, empty when absent).

### All options

| Option | Description |
|--------|-------------|
| `--week` | **Required.** `blue` or `gold` |
| `--off` | Dates that are off (holidays), e.g. `--off 2025-02-20` |
| `--start` | Start date (YYYY-MM-DD). Default: Sunday of current week |
| `--end` | End date (YYYY-MM-DD). Default: Saturday of current week |
| `--output`, `-o` | Write CSV report to this file |
| `--config-dir` | Directory with schedule.yaml, fellows.yaml, credentials.json (default: script directory) |
| `--no-llm` | Skip LLM analysis of excuse emails (list senders only); requires GEMINI_API_KEY for analysis |

## Careful usage

- **Account** – The script uses the Gmail account that completed OAuth (typically mathcenter@peddie.org). Ensure you sign in with the correct account so it only reads the intended inbox.
- **Sensitive data** – Console output and CSV may contain email addresses. Store or share CSV files and logs appropriately.
- **No-image list** – “Possible excuse emails” are *all* messages to mathcenter on the checked dates that do not have an image attachment. This can include non-fellow mail (e.g. other staff, lists). The LLM suggestion is advisory only; use it as a cue to follow up, not as an automatic approval.
- **Matching** – A sender is matched to at most one fellow per session. If multiple fellows share an email or alias, only one will be marked present; keep `fellows.yaml` accurate and use distinct aliases where possible.
- **Date range** – Default is the current week (Sunday–Saturday). For past or future weeks use `--start` and `--end` so only the intended dates are queried.

## Running weekly

Run once per week (e.g. Friday) for the week that just ended:

```bash
conda activate myenv
python attendance.py --week blue
```

If there was a holiday that week:

```bash
python attendance.py --week blue --off 2025-02-20
```

Switch to `--week gold` on Gold weeks.

## Changing the schedule or fellows

| Change | What to do |
|--------|-------------|
| Fellow list or session times | Edit **schedule.yaml** only. |
| New fellow or email alias | Add or update the entry in **fellows.yaml**. |
| Holiday / day off | Use `--off YYYY-MM-DD` when you run the script. |
| Different week | Use `--week gold` or `--week blue`. |

No code changes are required.

## File layout

| File | Purpose |
|------|--------|
| `attendance.py` | Main script (CLI and report). |
| `config.py` | Loads schedule and fellows; computes expected attendance. |
| `gmail_client.py` | Gmail OAuth, messages with/without image attachments. |
| `matching.py` | Matches email senders to fellow names. |
| `schedule.yaml` | Blue/Gold schedule (edit when the schedule changes). |
| `fellows.yaml` | Optional name/email mapping for fellows. |
| `credentials.json` | Gmail OAuth client secret (you add this; do not commit). |
| `token.json` | Cached OAuth token (created on first run; do not commit). |

## Troubleshooting

- **SSL certificate errors when running `pip install`**  
  If you see `SSLCertVerificationError` or similar, run the install in your own terminal with your environment activated and `pip install -r requirements.txt`. You can also try `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt` if your network requires it.

- **Gmail API not enabled**  
  If the script reports that Gmail API is not enabled, go to [Google Cloud Console → APIs & Services → Library](https://console.cloud.google.com/apis/library), search for “Gmail API,” and enable it for the same project that has your OAuth client.

- **No “Possible excuse emails” section**  
  That section only appears when there is at least one message to mathcenter on the checked dates that does not have an image attachment. If all messages have images (or there are no other messages), the section is omitted.

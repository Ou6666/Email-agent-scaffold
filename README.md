# Email Agent

An AI-powered email analysis agent that checks new emails, summarizes key points, scores priority, identifies follow-up actions, and prepares important notifications.

## MVP Goals

- Read new emails from one mailbox.
- Parse sender, subject, received time, body, and attachment metadata.
- Analyze each email with an LLM.
- Assign priority from 1 to 5.
- Detect whether the email needs a reply or follow-up.
- Save processed results to a local SQLite database.
- Send high-priority summaries to a notification channel.

## Initial Project Structure

```text
email-agent/
  app/
  data/
  tests/
  .env
  .gitignore
  README.md
  requirements.txt
```

## Suggested Build Order

1. Create project skeleton.
2. Define data schemas.
3. Add SQLite storage.
4. Connect to Gmail or IMAP.
5. Parse email content.
6. Add LLM-based analysis.
7. Save analysis results.
8. Add scheduled hourly checks.
9. Add notifications.
10. Add attachment analysis.

## Local Setup

```powershell
uv venv .venv
uv pip install -r requirements.txt
.venv\Scripts\python -m app.main
```

The default development mode can run without mailbox credentials by using `EMAIL_PROVIDER=mock`.

## Offline Development Mode

Use this mode before Gmail or Outlook credentials are ready:

```text
EMAIL_PROVIDER=mock
ANALYZER_PROVIDER=rule
FETCH_LIMIT=10
MINIMUM_NOTIFY_PRIORITY=4
SCHEDULER_INTERVAL_MINUTES=60
```

Then run:

```powershell
.venv\Scripts\python -m app.main
```

This runs the full local pipeline:

```text
mock emails -> parser -> rule-based analyzer -> SQLite -> console digest
```

To test the hourly scheduler locally:

```powershell
.venv\Scripts\python -m app.scheduler
```

To inspect saved analysis quality records:

```powershell
.venv\Scripts\python -m app.dashboard
```

## Connectivity Diagnostics

Use diagnostics before running the full agent against real services.

Check local config only:

```powershell
.venv\Scripts\python -m app.diagnostics
```

Try reading one real Gmail message:

```powershell
.venv\Scripts\python -m app.diagnostics --gmail-live
```

Send one real WhatsApp test message through Twilio:

```powershell
.venv\Scripts\python -m app.diagnostics --whatsapp-send
```

Run both live tests:

```powershell
.venv\Scripts\python -m app.diagnostics --all
```

For WhatsApp testing with Twilio Sandbox, make sure your personal WhatsApp number has joined the sandbox first. Use E.164 format, for example `whatsapp:+351XXXXXXXXX`.

## LLM Analyzer

The project currently supports two analyzer modes:

```text
ANALYZER_PROVIDER=rule
```

Uses the local rule-based analyzer. This requires no API key and is best while building the framework.

```text
ANALYZER_PROVIDER=llm
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
LLM_TEMPERATURE=0
LLM_ENABLE_FALLBACK=true
```

Uses the OpenAI analyzer. The LLM is instructed to return strict JSON matching the `EmailAnalysis` schema. If the LLM call fails and fallback is enabled, the workflow automatically uses the rule-based analyzer instead.

## Gmail Setup

This project uses the Gmail API with OAuth. Do not put your Gmail password in the project.

Recommended `.env` values:

```text
EMAIL_PROVIDER=gmail
GMAIL_USER_EMAIL=wuou233@gmail.com
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
```

Google Cloud setup:

1. Create or open a Google Cloud project.
2. Enable the Gmail API.
3. Configure the OAuth consent screen.
4. Create an OAuth Client ID with Application type `Desktop app`.
5. Download the JSON file and save it in the project root as `credentials.json`.

Then run:

```powershell
.venv\Scripts\python -m app.email_client.gmail_client
```

The first run opens a browser login flow. Sign in with `wuou233@gmail.com`, approve the requested Gmail read-only access, and the script will save `token.json` for later runs.

After Gmail is working, switch `.env` back to:

```text
EMAIL_PROVIDER=gmail
```

## Outlook Setup

This project uses Microsoft Graph to read Outlook mail. Create a Microsoft Entra app registration, then put the app's Application (client) ID in `.env`.

Required delegated permissions:

- `User.Read`
- `Mail.Read`

Recommended `.env` values:

```text
EMAIL_PROVIDER=outlook
OUTLOOK_USER_EMAIL=your_school_email@example.edu
OUTLOOK_CLIENT_ID=your_application_client_id
OUTLOOK_TENANT_ID=organizations
OUTLOOK_TOKEN_CACHE_PATH=.outlook_token_cache.json
OUTLOOK_SCOPES=User.Read Mail.Read offline_access
```

After filling `OUTLOOK_CLIENT_ID`, run:

```powershell
.venv\Scripts\python -m app.email_client.outlook_client
```

The first run prints a Microsoft device-code login message. Open the URL, enter the code, sign in with your school Outlook account, and the script will print the latest messages.

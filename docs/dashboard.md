# Dashboard Plan

The dashboard should help review email analysis quality, not just display raw emails.

## MVP Views

1. Overview
   - Total analyzed emails
   - High / medium / low quality counts
   - High priority emails
   - Emails needing reply
   - Emails needing follow-up
   - Opportunity emails

2. Email Quality Table
   - Subject
   - Sender
   - Received time
   - Priority
   - Quality label
   - Quality score
   - Opportunity score
   - Category
   - Needs reply
   - Needs follow-up
   - Deadline

3. Email Detail
   - Summary
   - Key points
   - Action items
   - Attachment summary
   - Model reasoning

4. Review Feedback
   - Mark as high quality
   - Mark as low quality
   - Mark priority as wrong
   - Mark category as wrong
   - Save notes for future personalization

## Suggested Technical Path

Start with a simple local dashboard:

```text
SQLite -> repository queries -> FastAPI endpoint -> minimal web UI
```

For a faster prototype, Streamlit is also reasonable:

```text
SQLite -> pandas -> Streamlit tables and filters
```

The current command-line dashboard can be run with:

```powershell
.venv\Scripts\python -m app.dashboard
```

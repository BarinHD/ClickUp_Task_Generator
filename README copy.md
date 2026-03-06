# ClickUp JSON Task Creator

Lightweight app that creates ClickUp tasks from pasted JSON. Built with Python and Streamlit.

## Setup

### 1. Create virtual environment

```bash
cd clickup-json-creator
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 3. Run the app

```bash
python3 -m streamlit run app.py
```

Open the URL shown in the terminal (usually http://localhost:8501).

If `pip` or `streamlit` are not found, always use `python3 -m pip` and `python3 -m streamlit` instead.

## Configuration

In the sidebar:

- **ClickUp API Token**: Your API token (from ClickUp Settings > Apps > API Token).
- **ClickUp List ID**: The list ID from the list URL (the number after `/list/`).

For persistence across sessions, create a `.env` file from the example:

```bash
cp .env.example .env
```

Add your values:

```
CLICKUP_API_TOKEN=pk_xxxxx...
CLICKUP_LIST_ID=12345678
```

## JSON format

Example input:

```json
{
  "title": "Review API integration",
  "description": "Check the new endpoints",
  "status": "to do",
  "priority": "high",
  "due_date": "2025-03-15"
}
```

### Field mapping

| JSON Field    | ClickUp API | Notes                                  |
|---------------|-------------|----------------------------------------|
| `title`       | `name`      | Required (or use `name`)               |
| `description` | `description` | String                             |
| `status`      | `status`    | Status name in the list                |
| `priority`    | `priority`  | `urgent`, `high`, `normal`, `low` or 1–4 |
| `due_date`    | `due_date`  | `YYYY-MM-DD` or Unix ms                |
| `assignees`   | `assignees` | Array of user IDs                      |
| `tags`        | `tags`      | Array of tag names (must exist in workspace) |
| `subtasks`    | (n/a)       | Array of task objects; each created as subtask with description, priority, assignees, tags |

### Date formats

- `YYYY-MM-DD`
- `YYYY-MM-DDTHH:MM:SS`
- Unix timestamp in milliseconds (integer)

import json
from datetime import datetime
import streamlit as st
import requests
from dotenv import load_dotenv
import os

load_dotenv()

PRIORITY_MAP = {
    "urgent": 1, "1": 1,
    "high": 2, "2": 2,
    "normal": 3, "3": 3,
    "low": 4, "4": 4,
}

CLICKUP_BASE = "https://api.clickup.com/api/v2"


def debug_api(api_token, team_id):
    headers = {"Authorization": api_token}
    out = []
    r0 = requests.get(f"{CLICKUP_BASE}/team", headers=headers, timeout=30)
    out.append(f"0. GET /team (authorized workspaces) → {r0.status_code}")
    if r0.status_code == 200:
        teams = r0.json().get("teams", [])
        out.append(f"   Your team IDs (use one of these):")
        for t in teams:
            out.append(f"   - id={t.get('id')} name={t.get('name')}")
        if not teams:
            out.append("   (empty - token may have no workspace access)")
    else:
        out.append(f"   Body: {r0.text[:300]}")
    out.append("")
    r = requests.get(f"{CLICKUP_BASE}/team/{team_id}/space", headers=headers, params={"include_archived": "false"}, timeout=30)
    out.append(f"1. GET /team/{team_id}/space → {r.status_code}")
    if r.status_code != 200:
        out.append(f"   Body: {r.text[:500]}")
        return "\n".join(out)
    try:
        data = r.json()
        spaces = data.get("spaces", [])
        out.append(f"   Spaces: {len(spaces)}")
        for i, s in enumerate(spaces[:5]):
            out.append(f"   - Space {i+1}: id={s.get('id')}, name={s.get('name')}")
        if len(spaces) > 5:
            out.append(f"   ... and {len(spaces)-5} more")
        for i, s in enumerate(spaces[:3]):
            sid = s.get("id")
            r2 = requests.get(f"{CLICKUP_BASE}/space/{sid}/list", headers=headers, params={"include_archived": "false"}, timeout=30)
            out.append(f"2.{i+1} GET /space/{sid}/list (folderless) → {r2.status_code}")
            if r2.status_code == 200:
                lst = r2.json()
                lists_data = lst.get("lists", lst) if isinstance(lst, dict) else lst
                out.append(f"   Keys: {list(lst.keys()) if isinstance(lst, dict) else 'array'}")
                out.append(f"   lists count: {len(lists_data) if isinstance(lists_data, list) else 'N/A'}")
            else:
                out.append(f"   Body: {r2.text[:300]}")
            r3 = requests.get(f"{CLICKUP_BASE}/space/{sid}/folder", headers=headers, params={"include_archived": "false"}, timeout=30)
            out.append(f"3.{i+1} GET /space/{sid}/folder → {r3.status_code}")
            if r3.status_code == 200:
                fld = r3.json()
                folders = fld.get("folders", [])
                out.append(f"   Folders: {len(folders)}")
            else:
                out.append(f"   Body: {r3.text[:300]}")
    except Exception as e:
        out.append(f"   Error: {e}")
    return "\n".join(out)


def fetch_lists(api_token, team_id):
    headers = {"Authorization": api_token}
    resp = requests.get(f"{CLICKUP_BASE}/team/{team_id}/space", headers=headers, params={"include_archived": "false"}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch spaces: {resp.status_code} - {resp.text[:200]}")
    spaces = resp.json().get("spaces", [])
    out = []
    for space in spaces:
        space_name = space.get("name", "?")
        resp_folderless = requests.get(f"{CLICKUP_BASE}/space/{space['id']}/list", headers=headers, params={"include_archived": "false"}, timeout=30)
        if resp_folderless.status_code == 200:
            for lst in resp_folderless.json().get("lists", []):
                out.append({
                    "id": str(lst["id"]),
                    "name": f"{space_name} / {lst.get('name', '?')}"
                })
        resp2 = requests.get(f"{CLICKUP_BASE}/space/{space['id']}/folder", headers=headers, params={"include_archived": "false"}, timeout=30)
        if resp2.status_code != 200:
            continue
        folders = resp2.json().get("folders", [])
        for folder in folders:
            folder_name = folder.get("name", "?")
            resp3 = requests.get(f"{CLICKUP_BASE}/folder/{folder['id']}/list", headers=headers, params={"include_archived": "false"}, timeout=30)
            if resp3.status_code != 200:
                continue
            for lst in resp3.json().get("lists", []):
                out.append({
                    "id": str(lst["id"]),
                    "name": f"{space_name} / {folder_name} / {lst.get('name', '?')}"
                })
    return out


def parse_due_date(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    s = str(value).strip()
    if not s:
        return None
    try:
        n = int(s)
        return n if n > 0 else None
    except ValueError:
        pass
    try:
        s_clean = s.replace("Z", "+00:00").replace("z", "+00:00")
        dt = datetime.fromisoformat(s_clean)
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            dt = datetime.strptime(s[:26], fmt)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def json_to_clickup_payload(data, parent_id=None):
    name = data.get("name") or data.get("title")
    if not name:
        raise ValueError("JSON must include 'title' or 'name'")
    payload = {"name": str(name)}
    if parent_id is not None:
        payload["parent"] = str(parent_id)
    desc = data.get("description")
    if desc is not None and str(desc).strip():
        payload["description"] = str(desc)
    status = data.get("status")
    if status is not None and str(status).strip():
        payload["status"] = str(status)
    pri = data.get("priority")
    if pri is not None:
        key = str(pri).lower().strip()
        if key in PRIORITY_MAP:
            payload["priority"] = PRIORITY_MAP[key]
        elif isinstance(pri, int) and 1 <= pri <= 4:
            payload["priority"] = pri
    due = parse_due_date(data.get("due_date"))
    if due is not None:
        payload["due_date"] = due
    assignees = data.get("assignees")
    if assignees is not None and isinstance(assignees, list):
        payload["assignees"] = [int(a) for a in assignees if str(a).isdigit()]
    tags = data.get("tags")
    if tags is not None and isinstance(tags, list):
        payload["tags"] = [str(t).strip() for t in tags if str(t).strip()]
    return payload


def create_clickup_task(api_token, list_id, payload):
    url = f"{CLICKUP_BASE}/list/{list_id}/task"
    headers = {"Authorization": api_token, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("err", err.get("message", resp.text))
        except Exception:
            msg = resp.text
        if resp.status_code in (400, 404) and "list" in str(msg).lower():
            msg = f"{msg} — Use **Load Lists** in the sidebar to pick a list; the API needs the numeric list ID, not the URL slug (e.g. 19a4uw-215555)."
        raise RuntimeError(f"API error {resp.status_code}: {msg}")
    return resp.json()


def main():
    st.set_page_config(page_title="ClickUp JSON Task Creator", page_icon="✅", layout="wide")
    st.title("ClickUp JSON Task Creator")

    if "api_token" not in st.session_state:
        st.session_state.api_token = os.getenv("CLICKUP_API_TOKEN", "")
    if "list_id" not in st.session_state:
        st.session_state.list_id = os.getenv("CLICKUP_LIST_ID", "")
    if "team_id" not in st.session_state:
        st.session_state.team_id = os.getenv("CLICKUP_TEAM_ID", "")
    if "lists_cache" not in st.session_state:
        st.session_state.lists_cache = []

    with st.sidebar:
        st.header("Settings")
        api_token = st.text_input(
            "ClickUp API Token",
            value=st.session_state.api_token,
            type="password",
            placeholder="pk_xxxxx..."
        )
        team_id = st.text_input(
            "Team / Workspace ID",
            value=st.session_state.team_id,
            placeholder="43324252"
        )
        st.session_state.api_token = api_token
        st.session_state.team_id = team_id
        if st.button("Load Lists") and api_token.strip() and team_id.strip():
            with st.spinner("Fetching lists..."):
                try:
                    st.session_state.lists_cache = fetch_lists(api_token, team_id.strip())
                    st.success(f"Found {len(st.session_state.lists_cache)} lists")
                except RuntimeError as e:
                    st.error(str(e))
        if st.button("Debug API") and api_token.strip() and team_id.strip():
            with st.spinner("Running debug..."):
                log = debug_api(api_token, team_id.strip())
            st.code(log, language="text")
        list_options = {f"{x['name']} (ID: {x['id']})": x["id"] for x in st.session_state.lists_cache}
        if list_options:
            chosen = st.selectbox("Select list", options=list(list_options.keys()), key="list_select")
            if chosen:
                st.session_state.list_id = list_options[chosen]
        list_id = st.text_input(
            "List ID (or pick above)",
            value=st.session_state.list_id,
            placeholder="Numeric ID e.g. 90123456789"
        )
        st.session_state.list_id = list_id
        with st.expander("Help"):
            st.markdown("""
**List Picker:** Enter Team ID (from URL: `.../43324252/...`), then click **Load Lists** and select the list. The API needs the **numeric** list ID, not the URL slug like `19a4uw-215555`.
            """)

    json_input = st.text_area(
        "JSON Input",
        height=200,
        placeholder='Single object or array: [{"title": "Task 1"}, {"title": "Task 2", "priority": "high"}]'
    )

    if st.button("Create ClickUp Task", type="primary"):
        if not st.session_state.api_token.strip():
            st.error("Please enter your ClickUp API Token in the sidebar.")
            return
        if not st.session_state.list_id.strip():
            st.error("Please enter the ClickUp List ID in the sidebar.")
            return
        if not json_input.strip():
            st.error("Please paste JSON data in the text area.")
            return
        try:
            data = json.loads(json_input)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}")
            return
        items = data if isinstance(data, list) else [data]
        if not items or not all(isinstance(x, dict) for x in items):
            st.error("JSON must be an object or array of objects with 'title' or 'name'")
            return
        success_count = 0
        errors = []
        for i, item in enumerate(items):
            try:
                payload = json_to_clickup_payload(item)
            except ValueError as e:
                errors.append(f"Item {i + 1}: {e}")
                continue
            try:
                result = create_clickup_task(
                    st.session_state.api_token,
                    st.session_state.list_id.strip(),
                    payload
                )
                parent_id = result.get("id")
                url = result.get("url")
                if url:
                    st.success(f"Task {i + 1} created: [{url}]({url})")
                else:
                    st.success(f"Task {i + 1} created (ID: {parent_id})")
                success_count += 1
                subtasks = item.get("subtasks")
                if subtasks and isinstance(subtasks, list) and parent_id:
                    for j, sub in enumerate(subtasks):
                        if not isinstance(sub, dict):
                            continue
                        try:
                            sub_payload = json_to_clickup_payload(sub, parent_id=parent_id)
                            sub_result = create_clickup_task(
                                st.session_state.api_token,
                                st.session_state.list_id.strip(),
                                sub_payload
                            )
                            sub_url = sub_result.get("url")
                            if sub_url:
                                st.success(f"  Subtask {j + 1}: [{sub_url}]({sub_url})")
                        except (ValueError, requests.RequestException, RuntimeError) as e:
                            errors.append(f"Item {i + 1} subtask {j + 1}: {e}")
            except requests.RequestException as e:
                errors.append(f"Item {i + 1}: Request failed - {e}")
            except RuntimeError as e:
                errors.append(f"Item {i + 1}: {e}")
        if errors:
            st.error("\n".join(errors))


if __name__ == "__main__":
    main()

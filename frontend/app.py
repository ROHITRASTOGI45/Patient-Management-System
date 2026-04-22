import streamlit as st
import requests
import pandas as pd
import os
import json
import urllib.parse
from pathlib import Path
import secrets

#  Config
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")        
REDIRECT_URI = st.secrets["REDIRECT_URI"]
CREDENTIALS_FILE = Path(__file__).parent / "google_credentials.json"

#  set insecure transport on localhost
if "localhost" in REDIRECT_URI:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

st.set_page_config(
    page_title="Patient Management System",
    page_icon="🏥",
    layout="wide"
)

#  Load credentials 
try:
    # Production - Streamlit Cloud
    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    BASE_URL = st.secrets.get("BACKEND_URL", BASE_URL)
    REDIRECT_URI = st.secrets.get("REDIRECT_URI", REDIRECT_URI)
    TOKEN_URI = "https://oauth2.googleapis.com/token"
    AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
except:
    # Local - use google_credentials.json
    with open(CREDENTIALS_FILE) as f:
        CREDS = json.load(f)["web"]
    CLIENT_ID = CREDS["client_id"]
    CLIENT_SECRET = CREDS["client_secret"]
    TOKEN_URI = "https://oauth2.googleapis.com/token"
    AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

#  Auth helpers 
def init_session():
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("current_page", "View All Patients")

def is_authenticated():
    return st.session_state.get("authenticated", False)

def current_user():
    return st.session_state.get("user", {})

import secrets

def build_auth_url():
    import secrets

    # ✅ Only generate if not already present
    if "oauth_state" not in st.session_state:
        st.session_state["oauth_state"] = secrets.token_urlsafe(16)

    state = st.session_state["oauth_state"]

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "select_account",
        "include_granted_scopes": "true",
        "state": state,
    }

    return f"{AUTH_URI}?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(code):
    response = requests.post(
        TOKEN_URI,
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=10
    )
    data = response.json()
    if "error" in data:
        raise Exception(f"{data['error']}: {data.get('error_description', '')}")
    return data["access_token"]

def get_user_info(access_token):
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    return resp.json()

# ------------------ BOOTSTRAP ------------------
init_session()

params = st.query_params

if "code" in params and "state" in params and not is_authenticated():
    code = params["code"]
    state = params["state"]

    # Handle list case (Streamlit sometimes returns list)
    if isinstance(code, list):
        code = code[0]
    if isinstance(state, list):
        state = state[0]

    stored_state = st.session_state.get("oauth_state")

    # ✅ Relaxed state handling (prevents session expired bug)
    if not stored_state:
        stored_state = state

    # Validate state
    if state != stored_state:
        st.error("❌ Invalid OAuth state")
        st.stop()

    with st.spinner("Signing you in..."):
        try:
            access_token = exchange_code_for_token(code)
            user_info = get_user_info(access_token)

            # Save session
            st.session_state["authenticated"] = True
            st.session_state["user"] = user_info

            # Cleanup
            st.session_state.pop("oauth_state", None)
            st.query_params.clear()

            st.rerun()

        except Exception as e:
            st.error(f"❌ Login failed: {str(e)}")
            st.stop()

# ------------------ LOGIN WALL ------------------
if not is_authenticated():
    st.markdown("""
        <div style='text-align:center; padding:80px 0 20px'>
            <h1>🏥 Patient Management System</h1>
            <p style='color:grey;font-size:1.1rem'>
                Please sign in to continue
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2,1,2])

    with col2:
        if st.button("🔐 Sign in with Google", use_container_width=True):
            auth_url = build_auth_url()

            # ✅ Direct redirect (same as manual URL — most reliable)
            st.markdown(
                f"[Click here to continue to Google Login]({auth_url})",
                unsafe_allow_html=True
            )

    st.stop()

#  Sidebar 
user = current_user()
st.sidebar.title("🏥 Patient Manager")
st.sidebar.markdown("---")
if user.get("picture"):
    st.sidebar.image(user["picture"], width=60)
st.sidebar.markdown(f"**{user.get('name', 'User')}**")
st.sidebar.caption(user.get("email", ""))
st.sidebar.markdown("---")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state["current_page"] = "View All Patients"
        st.rerun()
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.session_state["current_page"] = "View All Patients"
        st.rerun()

st.sidebar.markdown("---")

pages = ["View All Patients", "View Patient by ID", "Sort Patients",
         "Add Patient", "Update Patient", "Delete Patient"]
current_index = pages.index(st.session_state["current_page"])

page = st.sidebar.radio("Navigate", pages, index=current_index)

if page != st.session_state["current_page"]:
    st.session_state["current_page"] = page

st.sidebar.markdown("---")
st.sidebar.caption(f"Backend: {BASE_URL}")


# Helpers 
def fix_verdict(verdict: str, bmi: float) -> str:
    if 25 <= bmi < 30:
        return "Overweight"
    return verdict

VERDICT_BADGE = {
    "Underweight": "🟡 Underweight",
    "Normal":      "🟢 Normal",
    "Overweight":  "🟠 Overweight",
    "Obese":       "🔴 Obese",
}

VERDICT_COLORS = {
    "Underweight": "background-color: #3d3200; color: #ffd700",
    "Normal":      "background-color: #003d00; color: #00e676",
    "Overweight":  "background-color: #3d1f00; color: #ff9100",
    "Obese":       "background-color: #3d0000; color: #ff5252",
}

def style_verdict(verdict):
    return VERDICT_BADGE.get(verdict, verdict)

def color_verdict_cell(val):
    return VERDICT_COLORS.get(val, "")

def patients_to_df(data):
    rows = []
    for pid, info in data.items():
        row = {"ID": pid, **info}
        row["verdict"] = fix_verdict(row.get("verdict",""), row.get("bmi",0))
        rows.append(row)
    return pd.DataFrame(rows)

def list_to_df(data):
    rows = []
    for info in data:
        row = dict(info)
        row["verdict"] = fix_verdict(row.get("verdict",""), row.get("bmi",0))
        rows.append(row)
    return pd.DataFrame(rows)

def render_styled_df(df):
    try:
        styled = df.style.map(color_verdict_cell, subset=["verdict"])
    except AttributeError:
        styled = df.style.applymap(color_verdict_cell, subset=["verdict"])
    st.dataframe(styled, use_container_width=True, hide_index=True)




if st.session_state["current_page"] == "View All Patients":
    st.title("👥 All Patients")
    st.markdown("Complete list of every patient record in the database.")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
    try:
        resp = requests.get(f"{BASE_URL}/view", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data:
            render_styled_df(patients_to_df(data))
            st.caption(f"Total records: **{len(data)}**")
        else:
            st.warning("No patient records found.")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend.")
    except Exception as e:
        st.error(f"❌ {e}")

elif st.session_state["current_page"] == "View Patient by ID":
    st.title("🔍 View Patient by ID")
    patient_id = st.text_input("Patient ID", placeholder="e.g. P001").strip()
    if st.button("Search", type="primary"):
        if not patient_id:
            st.warning("Please enter a patient ID.")
        else:
            try:
                resp = requests.get(f"{BASE_URL}/patient/{patient_id}", timeout=5)
                if resp.status_code == 404:
                    st.error(f"❌ Patient **{patient_id}** not found.")
                else:
                    resp.raise_for_status()
                    p = resp.json()
                    verdict = fix_verdict(p.get("verdict",""), p.get("bmi",0))
                    st.success(f"✅ Record found for **{patient_id}**")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("### 👤 Personal Info")
                        st.markdown(f"**Name:** {p.get('name','—')}")
                        st.markdown(f"**Age:** {p.get('age','—')}")
                        st.markdown(f"**Gender:** {p.get('gender','—').capitalize()}")
                        st.markdown(f"**City:** {p.get('city','—')}")
                    with c2:
                        st.markdown("### 📏 Measurements")
                        st.markdown(f"**Height:** {p.get('height','—')} m")
                        st.markdown(f"**Weight:** {p.get('weight','—')} kg")
                        st.markdown(f"**BMI:** `{p.get('bmi','—')}`")
                    with c3:
                        st.markdown("### 🩺 Verdict")
                        st.markdown(f"## {style_verdict(verdict)}")
            except Exception as e:
                st.error(f"❌ {e}")

elif st.session_state["current_page"] == "Sort Patients":
    st.title("📊 Sort Patients")
    c1, c2, c3 = st.columns([2,2,1])
    with c1: sort_by = st.selectbox("Sort by", ["height","weight","bmi"])
    with c2: order = st.selectbox("Order", ["asc","desc"])
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        go = st.button("Sort", type="primary", use_container_width=True)
    if go:
        try:
            resp = requests.get(f"{BASE_URL}/sort",
                params={"sort_by":sort_by,"order":order}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if data:
                render_styled_df(list_to_df(data))
                st.caption(f"{len(data)} records sorted by **{sort_by}** ({order})")
            else:
                st.warning("No records found.")
        except Exception as e:
            st.error(f"❌ {e}")

elif st.session_state["current_page"] == "Add Patient":
    st.title("➕ Add New Patient")
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            pid    = st.text_input("Patient ID *", placeholder="e.g. P010")
            name   = st.text_input("Full Name *")
            city   = st.text_input("City *")
            age    = st.number_input("Age *", min_value=1, max_value=119, value=25)
        with c2:
            gender = st.selectbox("Gender *", ["male","female","others"])
            height = st.number_input("Height (m) *", min_value=0.1, max_value=3.0, value=1.70, format="%.2f")
            weight = st.number_input("Weight (kg) *", min_value=1.0, max_value=500.0, value=70.0, format="%.1f")
        sub = st.form_submit_button("➕ Add Patient", type="primary", use_container_width=True)
    if sub:
        if not pid.strip() or not name.strip() or not city.strip():
            st.warning("⚠️ ID, Name and City are required.")
        else:
            try:
                resp = requests.post(f"{BASE_URL}/create", json={
                    "id":pid.strip(),"name":name.strip(),"city":city.strip(),
                    "age":int(age),"gender":gender,"height":float(height),"weight":float(weight)
                }, timeout=5)
                if resp.status_code == 201: st.success(f"✅ Patient **{pid}** added!")
                elif resp.status_code == 400: st.error(f"❌ {resp.json().get('detail')}")
                else: resp.raise_for_status()
            except Exception as e:
                st.error(f"❌ {e}")

elif st.session_state["current_page"] == "Update Patient":
    st.title("✏️ Update Patient")
    patient_id = st.text_input("Patient ID to update", placeholder="e.g. P001").strip()
    with st.form("update_form"):
        c1, c2 = st.columns(2)
        with c1:
            name   = st.text_input("New Name", placeholder="Leave blank to keep")
            city   = st.text_input("New City", placeholder="Leave blank to keep")
            age    = st.number_input("New Age (0=no change)", min_value=0, max_value=119, value=0)
        with c2:
            gender = st.selectbox("New Gender", ["— no change —","male","female","others"])
            height = st.number_input("New Height m (0=no change)", min_value=0.0, max_value=3.0, value=0.0, format="%.2f")
            weight = st.number_input("New Weight kg (0=no change)", min_value=0.0, max_value=500.0, value=0.0, format="%.1f")
        sub = st.form_submit_button("💾 Update", type="primary", use_container_width=True)
    if sub:
        if not patient_id:
            st.warning("⚠️ Enter a patient ID.")
        else:
            payload = {}
            if name.strip(): payload["name"] = name.strip()
            if city.strip(): payload["city"] = city.strip()
            if age > 0: payload["age"] = int(age)
            if gender != "— no change —": payload["gender"] = gender
            if height > 0: payload["height"] = float(height)
            if weight > 0: payload["weight"] = float(weight)
            if not payload:
                st.warning("⚠️ Fill at least one field.")
            else:
                try:
                    resp = requests.put(f"{BASE_URL}/edit/{patient_id}", json=payload, timeout=5)
                    if resp.status_code == 200: st.success(f"✅ Patient **{patient_id}** updated!")
                    elif resp.status_code == 404: st.error(f"❌ Patient not found.")
                    else: resp.raise_for_status()
                except Exception as e:
                    st.error(f"❌ {e}")

elif st.session_state["current_page"] == "Delete Patient":
    st.title("🗑️ Delete Patient")
    patient_id = st.text_input("Patient ID to delete", placeholder="e.g. P001").strip()
    confirm = st.checkbox(f"Yes, permanently delete **{patient_id or '???'}**", disabled=not patient_id)
    if st.button("🗑️ Delete", type="primary", disabled=not confirm):
        try:
            resp = requests.delete(f"{BASE_URL}/delete/{patient_id}", timeout=5)
            if resp.status_code == 200: st.success(f"✅ Patient **{patient_id}** deleted.")
            elif resp.status_code == 404: st.error("❌ Patient not found.")
            else: resp.raise_for_status()
        except Exception as e:
            st.error(f"❌ {e}")
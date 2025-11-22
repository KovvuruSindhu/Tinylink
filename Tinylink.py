# Tinylink
import streamlit as st
import sqlite3
import re
from datetime import datetime

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect("tinylink.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS links (
    code TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_clicked TEXT
)
""")
conn.commit()

# ---------- HELPERS ----------
CODE_REGEX = r"^[A-Za-z0-9]{6,8}$"

def generate_code(n=6):
    import random, string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def create_link(url, code=None):
    if code:
        if not re.fullmatch(CODE_REGEX, code):
            return False, "Code must be 6–8 alphanumeric characters."

    # Auto-generate code
    if not code:
        code = generate_code()

    try:
        cur.execute(
            "INSERT INTO links (code, target_url, clicks, created_at) VALUES (?, ?, 0, ?)",
            (code, url, datetime.utcnow().isoformat())
        )
        conn.commit()
        return True, code
    except:
        return False, "Code already exists."


def get_link(code):
    cur.execute("SELECT code, target_url, clicks, created_at, last_clicked FROM links WHERE code = ?", (code,))
    row = cur.fetchone()
    return row


def delete_link(code):
    cur.execute("DELETE FROM links WHERE code = ?", (code,))
    conn.commit()


def increment_click(code):
    cur.execute("UPDATE links SET clicks = clicks + 1, last_clicked = ? WHERE code = ?",
                (datetime.utcnow().isoformat(), code))
    conn.commit()


# ---------- REDIRECT HANDLER (Streamlit style) ----------
query_params = st.query_params
if "code" in query_params:
    code = query_params["code"]

    link = get_link(code)
    if link:
        increment_click(code)
        st.success(f"Redirecting to {link[1]} ...")
        st.markdown(f"<meta http-equiv='refresh' content='1; url={link[1]}' />", unsafe_allow_html=True)
    else:
        st.error("404 — Link Not Found")
    st.stop()

# ---------- HEALTHZ ----------
if st.sidebar.button("Health Check (GET /healthz)"):
    st.json({"ok": True, "version": "1.0"})
    st.stop()

# ---------- UI ROUTER ----------
st.title("🔗 TinyLink — URL Shortener")

page = st.sidebar.radio("Navigation", ["Dashboard", "Stats Page"])

# ---------- DASHBOARD ----------
if page == "Dashboard":
    st.header("All Links")

    rows = cur.execute("SELECT * FROM links ORDER BY created_at DESC").fetchall()

    if not rows:
        st.info("No links yet. Add your first short link below.")

    for row in rows:
        code, url, clicks, created_at, last_clicked = row

        with st.expander(f"🔹 {code}"):
            st.write(f"**Target:** {url}")
            st.write(f"**Clicks:** {clicks}")
            st.write(f"**Last Click:** {last_clicked}")
            st.write(f"**Created:** {created_at}")

            if st.button(f"Delete {code}"):
                delete_link(code)
                st.success("Deleted!")
                st.rerun()

    st.subheader("Create New Short Link")
    url = st.text_input("Enter long URL")
    custom_code = st.text_input("Custom code (optional)")

    if st.button("Create"):
        if not url.startswith("http"):
            st.error("Invalid URL. Must start with http or https.")
        else:
            ok, result = create_link(url, custom_code.strip() if custom_code else None)
            if ok:
                st.success(f"Created! Your code: **{result}**")
            else:
                st.error(result)

# ---------- SINGLE STATS PAGE ----------
elif page == "Stats Page":
    st.header("Link Stats")

    search_code = st.text_input("Enter short code")

    if st.button("Lookup"):
        link = get_link(search_code)

        if not link:
            st.error("No such code exists.")
        else:
            code, url, clicks, created_at, last_clicked = link

            st.write(f"### Code: `{code}`")
            st.write(f"**Target URL:** {url}")
            st.write(f"**Created At:** {created_at}")
            st.write(f"**Total Clicks:** {clicks}")
            st.write(f"**Last Clicked:** {last_clicked}")

import streamlit as st
import sqlite3
import re
from datetime import datetime
import random, string

# ------------------------------------------------------
# DATABASE SETUP
# ------------------------------------------------------
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

# ------------------------------------------------------
# HELPERS
# ------------------------------------------------------
CODE_REGEX = r"^[A-Za-z0-9]{6,8}$"

def generate_code(n=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def create_link(url, code=None):
    if code:
        if not re.fullmatch(CODE_REGEX, code):
            return False, "Code must be 6–8 alphanumeric characters."

    if not code:
        code = generate_code()

    try:
        cur.execute(
            "INSERT INTO links (code, target_url, clicks, created_at) VALUES (?, ?, 0, ?)",
            (code, url, datetime.utcnow().isoformat())
        )
        conn.commit()
        return True, code
    except sqlite3.IntegrityError:
        return False, "Code already exists."


def get_link(code):
    cur.execute("SELECT code, target_url, clicks, created_at, last_clicked FROM links WHERE code=?", (code,))
    return cur.fetchone()


def delete_link(code):
    cur.execute("DELETE FROM links WHERE code=?", (code,))
    conn.commit()


def increment_click(code):
    cur.execute("""
        UPDATE links
        SET clicks = clicks + 1,
            last_clicked = ?
        WHERE code = ?
    """, (datetime.utcnow().isoformat(), code))
    conn.commit()


# ------------------------------------------------------
# REDIRECT HANDLING (/?code=xxx)
# ------------------------------------------------------
query_params = st.query_params
if "code" in query_params:
    code = query_params["code"]

    link = get_link(code)
    if link:
        increment_click(code)   # ⭐ FIXED: Click count now increments
        st.success(f"Redirecting to {link[1]}...")
        st.markdown(
            f"<meta http-equiv='refresh' content='1; url={link[1]}' />",
            unsafe_allow_html=True
        )
    else:
        st.error("404 — Short code not found")

    st.stop()

# ------------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------------
if st.sidebar.button("Health Check (/healthz)"):
    st.json({"ok": True, "version": "1.0"})
    st.stop()

# ------------------------------------------------------
# UI NAVIGATION
# ------------------------------------------------------
st.title("🔗 TinyLink — URL Shortener")
page = st.sidebar.radio("Navigation", ["Dashboard", "Stats Page"])

# ------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------
if page == "Dashboard":
    st.header("All Links")

    rows = cur.execute("SELECT * FROM links ORDER BY created_at DESC").fetchall()

    if not rows:
        st.info("No links yet.")

    for row in rows:
        code, url, clicks, created_at, last_clicked = row

        with st.expander(f"🔹 {code}"):
            st.write(f"**Target URL:** {url}")
            st.write(f"**Clicks:** {clicks}")
            st.write(f"**Last Clicked:** {last_clicked}")
            st.write(f"**Created At:** {created_at}")
            st.write(f"**Visit:** http://localhost:8501/?code={code}")

            if st.button(f"Delete {code}", key=f"del_{code}"):
                delete_link(code)
                st.success("Deleted!")
                st.rerun()

    st.subheader("Create New Short Link")

    url = st.text_input("Enter long URL")
    custom_code = st.text_input("Custom short code (optional)")

    if st.button("Create"):
        if not url.startswith(("http://", "https://")):
            st.error("Invalid URL. Must start with http:// or https://")
        else:
            ok, result = create_link(url, custom_code.strip() if custom_code else None)
            if ok:
                st.success(f"Created! Short code: **{result}**")
                st.info(f"Visit:  http://localhost:8501/?code={result}")
                st.rerun()
            else:
                st.error(result)

# ------------------------------------------------------
# STATS PAGE
# ------------------------------------------------------
elif page == "Stats Page":
    st.header("Short Link Stats")

    code = st.text_input("Enter code to view stats")

    if st.button("Lookup Stats"):
        link = get_link(code)

        if not link:
            st.error("Short code not found.")
        else:
            code, url, clicks, created_at, last_clicked = link

            st.subheader(f"🔹 Stats for `{code}`")
            st.write(f"**Target URL:** {url}")
            st.write(f"**Created At:** {created_at}")
            st.write(f"**Total Clicks:** {clicks}")
            st.write(f"**Last Clicked:** {last_clicked}")
            st.write("---")
            st.write(f"Open link: http://localhost:8501/?code={code}")

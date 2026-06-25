import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import os

st.set_page_config(page_title="KingsElite School Portal", page_icon="👑", layout="wide", initial_sidebar_state="collapsed")

CLASSES = ["Baby Class", "Middle Class", "Top Class", "P1","P2","P3","P4","P5","P6","P7"]
SUBJECTS = ["Math","English","Science","Social Studies","Reading","Writing"]

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()
def get_grade(s): return 'D1' if s>=80 else 'D2' if s>=75 else 'C3' if s>=70 else 'C4' if s>=65 else 'C5' if s>=60 else 'C6' if s>=55 else 'P7' if s>=50 else 'P8' if s>=45 else 'F9'

# ---------- DATABASE ----------
conn = sqlite3.connect('school.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, class TEXT, admission_no TEXT UNIQUE)''')
c.execute('''CREATE TABLE IF NOT EXISTS marks (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, subject TEXT, term TEXT, score INTEGER, FOREIGN KEY(student_id) REFERENCES students(id))''')
c.execute('''CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, role TEXT DEFAULT 'admin')''')
c.execute('''CREATE TABLE IF NOT EXISTS class_fees (class TEXT PRIMARY KEY, amount REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS fees (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER, paid_amount REAL, term TEXT, date TEXT, description TEXT, FOREIGN KEY(student_id) REFERENCES students(id))''')
c.execute('''CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, class TEXT, subject TEXT, topic TEXT, filename TEXT, file_data BLOB, uploaded_by TEXT, date TEXT)''')

try:
    c.execute("ALTER TABLE admins ADD COLUMN role TEXT DEFAULT 'admin'")
    conn.commit()
except sqlite3.OperationalError:
    pass

c.execute("INSERT OR IGNORE INTO admins (username,password,name,role) VALUES (?,?,?,?)", ('superadmin', hash_pass("admin123"), 'Super Admin', 'super_admin'))
conn.commit()

# ---------- FUNCTIONS ----------
def add_student(u,p,n,cls,a):
    u = u.lower().strip()
    a = a.upper().strip()
    c.execute("SELECT id FROM students WHERE username=?", (u,))
    if c.fetchone(): return "username"
    c.execute("SELECT id FROM students WHERE admission_no=?", (a,))
    if c.fetchone(): return "admission"
    try:
        c.execute("INSERT INTO students (username,password,name,class,admission_no) VALUES (?,?,?,?,?)",
                  (u,hash_pass(p),n,cls,a))
        conn.commit()
        return "success"
    except: return "error"

def update_student_profile(sid, name, username, password, cls):
    username = username.lower().strip()
    c.execute("SELECT id FROM students WHERE username=? AND id!=?", (username, sid))
    if c.fetchone(): return "username"
    if password.strip():
        c.execute("UPDATE students SET name=?, username=?, password=?, class=? WHERE id=?",
                  (name, username, hash_pass(password), cls, sid))
    else:
        c.execute("UPDATE students SET name=?, username=?, class=? WHERE id=?",
                  (name, username, cls, sid))
    conn.commit()
    return "success"

def update_admin_profile(aid, username, password, name, role):
    username = username.lower().strip()
    c.execute("SELECT id FROM admins WHERE username=? AND id!=?", (username, aid))
    if c.fetchone(): return "exists"
    if password.strip():
        c.execute("UPDATE admins SET username=?, password=?, name=?, role=? WHERE id=?",
                  (username, hash_pass(password), name, role, aid))
    else:
        c.execute("UPDATE admins SET username=?, name=?, role=? WHERE id=?",
                  (username, name, role, aid))
    conn.commit()
    return "success"

def delete_student(sid):
    c.execute("DELETE FROM marks WHERE student_id=?", (sid,))
    c.execute("DELETE FROM fees WHERE student_id=?", (sid,))
    c.execute("DELETE FROM students WHERE id=?", (sid,))
    conn.commit()

def add_admin(u,p,n,role):
    u = u.lower().strip()
    c.execute("SELECT id FROM admins WHERE username=?", (u,))
    if c.fetchone(): return "exists"
    try:
        c.execute("INSERT INTO admins (username,password,name,role) VALUES (?,?,?,?)",
                  (u,hash_pass(p),n,role))
        conn.commit()
        return "success"
    except: return "error"

def delete_admin(aid):
    if aid == 1: return "cannot_delete_super"
    c.execute("DELETE FROM admins WHERE id=?", (aid,))
    conn.commit()
    return "success"

def login_user(u,p):
    c.execute("SELECT * FROM students WHERE username=? AND password=?",(u.lower().strip(),hash_pass(p)))
    return c.fetchone()

def login_admin(u,p):
    c.execute("SELECT * FROM admins WHERE username=? AND password=?",(u.lower().strip(),hash_pass(p)))
    return c.fetchone()

def add_marks(sid,subj,term,score):
    c.execute("INSERT INTO marks (student_id,subject,term,score) VALUES (?,?,?,?)",(sid,subj,term,score))
    conn.commit()

def update_mark(mid, score):
    c.execute("UPDATE marks SET score=? WHERE id=?", (score, mid))
    conn.commit()

def delete_mark(mid):
    c.execute("DELETE FROM marks WHERE id=?", (mid,))
    conn.commit()

def get_report(sid):
    c.execute("SELECT s.name,s.class,s.admission_no,m.subject,m.term,m.score FROM students s JOIN marks m ON s.id=m.student_id WHERE s.id=?",(sid,))
    return c.fetchall()

def get_student_marks(sid):
    c.execute("SELECT id,subject,term,score FROM marks WHERE student_id=? ORDER BY subject,term",(sid,))
    return c.fetchall()

def set_class_fee(cls, amount):
    c.execute("INSERT OR REPLACE INTO class_fees (class,amount) VALUES (?,?)", (cls, amount))
    conn.commit()

def get_class_fee(cls):
    c.execute("SELECT amount FROM class_fees WHERE class=?", (cls,))
    res = c.fetchone()
    return res[0] if res else 0

def add_fee_payment(sid, paid, term, desc):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO fees (student_id,paid_amount,term,date,description) VALUES (?,?,?,?,?)",
              (sid, paid, term, date, desc))
    conn.commit()

def get_student_payments(sid):
    c.execute("SELECT id,paid_amount,term,date,description FROM fees WHERE student_id=? ORDER BY date DESC",(sid,))
    return c.fetchall()

def get_student_balance(sid):
    c.execute("SELECT class FROM students WHERE id=?", (sid,))
    cls = c.fetchone()[0]
    total_fee = get_class_fee(cls)
    c.execute("SELECT SUM(paid_amount) FROM fees WHERE student_id=?", (sid,))
    paid = c.fetchone()[0] or 0
    return total_fee, paid, total_fee - paid

def add_document(cls, subj, topic, filename, file_data, admin_name):
    date = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO documents (class,subject,topic,filename,file_data,uploaded_by,date) VALUES (?,?,?,?,?,?,?)",
              (cls, subj, topic, filename, file_data, admin_name, date))
    conn.commit()

def get_documents(cls):
    c.execute("SELECT id,subject,topic,filename,date FROM documents WHERE class=? ORDER BY date DESC",(cls,))
    return c.fetchall() # fixed

def get_document_file(did):
    c.execute("SELECT filename,file_data FROM documents WHERE id=?", (did,))
    return c.fetchone()

def delete_document(did):
    c.execute("DELETE FROM documents WHERE id=?", (did,))
    conn.commit()

# ---------- CSS ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
* {font-family: 'Poppins', sans-serif;}

.stApp {
    background: linear-gradient(-45deg, #667eea, #764ba2, #f093fb, #f5576c, #4facfe, #00f2fe);
    background-size: 600% 600%;
    animation: gradientShift 120s ease infinite;
    min-height: 100vh;
}

@keyframes gradientShift {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

[data-testid="stHeader"] {background: white!important; box-shadow: 0 2px 8px rgba(0,0,0,0.1);}
[data-testid="stHeader"] * {color: #1e40af!important; font-weight: 600!important;}
[data-testid="stHeader"]::after {
    content: "KingsElite School Portal";
    position: absolute; left: 50%; transform: translateX(-50%);
    color: #1e40af; font-size: 20px; font-weight: 700;
}

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],.stDeployButton, [data-testid="collapsedControl"] {display: none!important;}

.glass-card {
    background: rgba(255,255,255,0.95); backdrop-filter: blur(20px);
    border-radius: 20px; padding: 2rem; margin: 1rem 0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.4);
}

.stTextInput input,.stTextArea textarea {color: #000!important; background: white!important; border: 2px solid #ddd; border-radius: 10px; font-size: 15px;}
.stSelectbox div[data-baseweb="select"] > div {color: #000!important; background: white!important; border: 2px solid #ddd; border-radius: 10px;}
.stTextInput label,.stSelectbox label {color: #333!important; font-weight: 600;}

.stButton>button {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white; border: none; border-radius: 12px; font-weight: 600;
    width: 100%; height: 3em; transition: 0.3s;
}
.stButton>button:hover {transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);}

h1,h2,h3,h4 {color: #1a1a1a!important; font-weight: 700;}
.stTabs [data-baseweb="tab-list"] {gap: 20px;}
.stTabs [data-baseweb="tab"] {font-size: 18px; font-weight: 600; color: white!important; text-shadow: 0 2px 4px rgba(0,0,0,0.3);}
.stTabs [aria-selected="true"] {border-bottom: 3px solid white!important;}
.metric-card {text-align: center; padding: 1rem;}
.metric-card h3 {color: #1a1a1a!important; font-size: 2rem;}
.metric-card h4 {color: #666!important;}
.danger-btn button {background: linear-gradient(90deg, #dc2626, #b91c1c)!important;}
.success-badge {background: #10b981; color: white; padding: 5px 12px; border-radius: 20px; font-size: 12px;}
.warning-badge {background: #f59e0b; color: white; padding: 5px 12px; border-radius: 20px; font-size: 12px;}
.danger-badge {background: #ef4444; color: white; padding: 5px 12px; border-radius: 20px; font-size: 12px;}
</style>
""", unsafe_allow_html=True)

# ---------- SESSION ----------
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'reg_success' not in st.session_state: st.session_state.reg_success = False
if 'page' not in st.session_state: st.session_state.page = "Student Login"

# ---------- LOGIN/REGISTER ----------
if st.session_state.user is None and st.session_state.page!= "Admin Panel":
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("👑 KingsElite School Portal")
        tab1, tab2, tab3 = st.tabs(["Student Login", "Student Register", "Admin Login"])

        with tab1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Student Login")
            u = st.text_input("Username", key="login_u")
            p = st.text_input("Password", type="password", key="login_p")
            if st.button("Login Student"):
                user = login_user(u, p)
                if user:
                    st.session_state.user = user
                    st.session_state.is_admin = False
                    st.rerun()
                else:
                    st.error("Invalid student login")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Student Self Registration")
            if not st.session_state.reg_success:
                name = st.text_input("Full Name")
                adm = st.text_input("Admission No")
                user = st.text_input("Username")
                pwd = st.text_input("Password", type="password")
                cls = st.selectbox("Class", CLASSES)
                if st.button("Register Student"):
                    if not all([name.strip(), adm.strip(), user.strip(), pwd]):
                        st.error("Fill all fields")
                    elif len(pwd) < 6:
                        st.error("Password must be 6+ characters")
                    else:
                        result = add_student(user, pwd, name.title().strip(), cls, adm)
                        if result == "success":
                            st.session_state.reg_success = True
                            st.rerun()
                        elif result == "username":
                            st.error(f"Username '{user.lower().strip()}' already exists.")
                        elif result == "admission":
                            st.error(f"Admission No '{adm.upper().strip()}' already exists.")
                        else:
                            st.error("Registration failed.")
            else:
                st.success("✅ Registration successful! Switch to Login tab")
                if st.button("Go to Login"):
                    st.session_state.reg_success = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Admin Login")
            au = st.text_input("Admin Username", key="admin_u", placeholder="superadmin")
            ap = st.text_input("Admin Password", type="password", key="admin_p", placeholder="admin123")
            if st.button("Login Admin"):
                admin = login_admin(au, ap)
                if admin:
                    st.session_state.user = admin
                    st.session_state.is_admin = True
                    st.session_state.page = "Admin Panel"
                    st.rerun()
                else:
                    st.error("Invalid admin credentials")
            st.markdown("</div>", unsafe_allow_html=True)

# ---------- STUDENT DASHBOARD ----------
elif st.session_state.user is not None and not st.session_state.is_admin:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([6,1])
    with col1: st.title(f"Welcome {st.session_state.user[3]}")
    with col2:
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    tabs = st.tabs(["Report Card", "Fees", "Notes & Docs", "Edit Profile"])

    with tabs[0]:
        report = get_report(st.session_state.user[0])
        if report:
            name, cls, adm = report[0][0], report[0][1], report[0][2]
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'><h4>Name</h4><h3>{name}</h3></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'><h4>Class</h4><h3>{cls}</h3></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><h4>Adm No</h4><h3>{adm}</h3></div>", unsafe_allow_html=True)

            df = pd.DataFrame(report, columns=['Name','Class','Adm','Subject','Term','Score'])
            df['Grade'] = df['Score'].apply(get_grade)
            st.dataframe(df[['Subject','Term','Score','Grade']], use_container_width=True)
            st.metric("Average", f"{df['Score'].mean():.1f}%")
        else:
            st.info("No marks yet. Contact admin.")

    with tabs[1]:
        st.subheader("My Fees Statement")
        total_fee, paid, balance = get_student_balance(st.session_state.user[0])
        payments = get_student_payments(st.session_state.user[0])

        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total Fees", f"UGX {total_fee:,.0f}")
        with c2: st.metric("Total Paid", f"UGX {paid:,.0f}")
        with c3:
            if balance <= 0:
                st.markdown(f"<div class='metric-card'><h4>Status</h4><span class='success-badge'>Cleared</span></div>", unsafe_allow_html=True)
            elif balance < total_fee * 0.3:
                st.markdown(f"<div class='metric-card'><h4>Balance</h4><span class='warning-badge'>UGX {balance:,.0f}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='metric-card'><h4>Balance</h4><span class='danger-badge'>UGX {balance:,.0f}</span></div>", unsafe_allow_html=True)

        if payments:
            df_pay = pd.DataFrame(payments, columns=['ID','Paid','Term','Date','Description'])
            st.dataframe(df_pay, use_container_width=True)
        else:
            st.info("No payments recorded yet")

    with tabs[2]:
        st.subheader(f"Notes & Documents - {st.session_state.user[4]}")
        docs = get_documents(st.session_state.user[4])
        if docs:
            for doc in docs:
                with st.expander(f"📄 {doc[1]} - {doc[2]}"):
                    st.caption(f"Uploaded on {doc[4]}")
                    file_data = get_document_file(doc[0])[1]
                    st.download_button(
                        label=f"Download {doc[3]}",
                        data=file_data,
                        file_name=doc[3],
                        mime="application/octet-stream"
                    )
        else:
            st.info("No documents uploaded for your class yet")

    with tabs[3]:
        st.subheader("Edit Your Profile")
        st.caption("Leave password blank to keep current password")
        new_name = st.text_input("Full Name", value=st.session_state.user[3])
        new_user = st.text_input("Username", value=st.session_state.user[1])
        new_pass = st.text_input("New Password", type="password", placeholder="Leave blank to keep current")
        
        user_class = st.session_state.user[4]
        default_index = CLASSES.index(user_class) if user_class in CLASSES else 0
        new_cls = st.selectbox("Class", CLASSES, index=default_index)

        if st.button("Update Profile"):
            if not all([new_name.strip(), new_user.strip()]):
                st.error("Name and Username required")
            else:
                result = update_student_profile(st.session_state.user[0], new_name.title().strip(), new_user, new_pass, new_cls)
                if result == "success":
                    st.success("Profile updated! Please login again")
                    st.session_state.user = None
                    st.rerun()
                elif result == "username":
                    st.error("Username already taken")
                else:
                    st.error("Update failed")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------- ADMIN PANEL ----------
elif st.session_state.page == "Admin Panel" and st.session_state.is_admin:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.title(f"👨‍💼 Admin Dashboard - {st.session_state.user[3]}")
    st.caption(f"Role: {st.session_state.user[4].replace('_',' ').title()}")

    if st.button("← Logout Admin"):
        st.session_state.user = None
        st.session_state.is_admin = False
        st.session_state.page = "Student Login"
        st.rerun()

    is_super = st.session_state.user[4] == 'super_admin'
    tabs = ["Add Student", "Add Marks", "Manage Students", "Edit/Delete Marks", "Class Fees Setup", "Fees Payments", "Upload Documents"]
    if is_super: tabs.append("Manage Admins")

    tab_list = st.tabs(tabs)

    with tab_list[0]:
        st.subheader("Add Student Manually")
        name = st.text_input("Full Name", key="add_name")
        adm = st.text_input("Admission No", key="add_adm")
        user = st.text_input("Username", key="add_user")
        pwd = st.text_input("Password", type="password", key="add_pwd")
        cls = st.selectbox("Class", CLASSES, key="add_cls")
        if st.button("Create Student"):
            if not all([name.strip(), adm.strip(), user.strip(), pwd]):
                st.error("Fill all fields")
            elif len(pwd) < 6:
                st.error("Password 6+ chars")
            else:
                result = add_student(user, pwd, name.title().strip(), cls, adm)
                if result == "success": st.success(f"Student {name} created successfully")
                elif result == "username": st.error("Username exists")
                elif result == "admission": st.error("Admission No exists")
                else: st.error("Failed")

    with tab_list[1]:
        st.subheader("Add Marks")
        c.execute("SELECT id,name,class FROM students")
        studs = c.fetchall()
        if studs:
            sel = st.selectbox("Select Student", [f"{s[1]} - {s[2]}" for s in studs], key="mark_sel")
            sid = [s[0] for s in studs if f"{s[1]} - {s[2]}" == sel][0]
            subj = st.selectbox("Subject", SUBJECTS)
            term = st.selectbox("Term", ["Term 1 2026"])
            score = st.number_input("Score", 0, 100, 70)
            if st.button("Save Marks"):
                add_marks(sid, subj, term, score)
                st.success(f"Marks saved for {sel}")
        else:
            st.warning("No students yet")

    with tab_list[2]:
        st.subheader("Manage Students")
        c.execute("SELECT id,name,class,username,admission_no FROM students")
        studs = c.fetchall()
        if studs:
            df_studs = pd.DataFrame(studs, columns=['ID','Name','Class','Username','Adm No'])
            st.dataframe(df_studs, use_container_width=True)
            del_sel = st.selectbox("Delete Student", ["None"] + [f"{s[1]} - {s[4]}" for s in studs])
            if del_sel!= "None":
                st.warning("⚠️ This will delete student AND all their marks + fees permanently")
                st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
                if st.button("Delete Selected Student", key="del_stud_btn"):
                    sid = [s[0] for s in studs if f"{s[1]} - {s[4]}" == del_sel][0]
                    delete_student(sid)
                    st.success("Student deleted")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No students registered")

    with tab_list[3]:
        st.subheader("Edit/Delete Student Marks")
        c.execute("SELECT id,name,class FROM students")
        studs = c.fetchall()
        if studs:
            sel = st.selectbox("Select Student", [f"{s[1]} - {s[2]}" for s in studs], key="edit_mark_sel")
            sid = [s[0] for s in studs if f"{s[1]} - {s[2]}" == sel][0]
            marks = get_student_marks(sid)

            if marks:
                df_marks = pd.DataFrame(marks, columns=['ID','Subject','Term','Score'])
                df_marks['Grade'] = df_marks['Score'].apply(get_grade)
                st.dataframe(df_marks[['Subject','Term','Score','Grade']], use_container_width=True)

                mark_sel = st.selectbox("Select Mark to Edit/Delete",
                                        ["None"] + [f"{m[1]} - {m[2]}: {m[3]}%" for m in marks])

                if mark_sel!= "None":
                    mid = [m[0] for m in marks if f"{m[1]} - {m[2]}: {m[3]}%" == mark_sel][0]
                    current_score = [m[3] for m in marks if m[0] == mid][0]

                    col1, col2 = st.columns(2)
                    with col1:
                        new_score = st.number_input("New Score", 0, 100, current_score)
                        if st.button("Update Score"):
                            update_mark(mid, new_score)
                            st.success("Score updated")
                            st.rerun()
                    with col2:
                        st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
                        if st.button("Delete This Mark"):
                            delete_mark(mid)
                            st.success("Mark deleted")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("No marks for this student yet")
        else:
            st.warning("No students yet")

    with tab_list[4]:
        st.subheader("Class Fees Setup")
        st.caption("Set total fees amount for each class. Students balance will auto-calculate")

        for cls in CLASSES:
            current_fee = get_class_fee(cls)
            new_fee = st.number_input(f"{cls} - Total Fees UGX", min_value=0.0, value=float(current_fee), step=10000.0, key=f"fee_{cls}")
            if st.button(f"Save {cls} Fees", key=f"btn_{cls}"):
                set_class_fee(cls, new_fee)
                st.success(f"{cls} fees set to UGX {new_fee:,.0f}")

    with tab_list[5]:
        st.subheader("Fees Payments & Balances")
        c.execute("SELECT id,name,class FROM students")
        studs = c.fetchall()
        if studs:
            sel = st.selectbox("Select Student", [f"{s[1]} - {s[2]}" for s in studs], key="pay_sel")
            sid = [s[0] for s in studs if f"{s[1]} - {s[2]}" == sel][0]

            total_fee, paid, balance = get_student_balance(sid)
            cls = [s[2] for s in studs if f"{s[1]} - {s[2]}" == sel][0]

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Class Fees", f"UGX {total_fee:,.0f}")
            with c2: st.metric("Total Paid", f"UGX {paid:,.0f}")
            with c3: st.metric("Balance", f"UGX {balance:,.0f}")

            st.divider()
            st.markdown("#### Record New Payment")
            col1, col2 = st.columns(2)
            with col1:
                pay_amount = st.number_input("Amount Paid UGX", min_value=0.0, step=5000.0)
                term = st.selectbox("Term", ["Term 1 2026", "Term 2 2026", "Term 3 2026"])
            with col2:
                desc = st.text_input("Description", placeholder="Tuition, Registration, etc")

            if st.button("Record Payment"):
                add_fee_payment(sid, pay_amount, term, desc)
                st.success(f"Payment recorded. New balance: UGX {balance - pay_amount:,.0f}")
                st.rerun()

            st.divider()
            st.markdown("#### All Payments")
            payments = get_student_payments(sid)
            if payments:
                df = pd.DataFrame(payments, columns=['ID','Paid','Term','Date','Description'])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No payments yet")

            st.divider()
            st.markdown("#### All Students Balance Overview")
            balance_data = []
            for s in studs:
                t_fee, p_amt, bal = get_student_balance(s[0])
                balance_data.append([s[1], s[2], t_fee, p_amt, bal])
            df_bal = pd.DataFrame(balance_data, columns=['Name','Class','Total Fees','Paid','Balance'])
            st.dataframe(df_bal, use_container_width=True)
        else:
            st.warning("No students yet")

    with tab_list[6]:
        st.subheader("Upload Documents/Notes")
        st.markdown("#### Upload PDF/Notes for Class")
        cls = st.selectbox("Class", CLASSES, key="doc_cls")
        subj = st.selectbox("Subject", SUBJECTS, key="doc_subj")
        topic = st.text_input("Topic/Title")
        uploaded_file = st.file_uploader("Upload PDF/Document", type=['pdf','doc','docx','txt','png','jpg'])

        if st.button("Upload Document"):
            if not topic.strip():
                st.error("Topic title required")
            elif uploaded_file is None:
                st.error("Please select a file")
            else:
                file_data = uploaded_file.read()
                add_document(cls, subj, topic, uploaded_file.name, file_data, st.session_state.user[3])
                st.success(f"Document uploaded for {cls} - {subj}")

        st.divider()
        st.markdown("#### Manage Documents")
        c.execute("SELECT id,class,subject,topic,filename,date FROM documents ORDER BY date DESC")
        docs = c.fetchall()
        if docs:
            df_docs = pd.DataFrame(docs, columns=['ID','Class','Subject','Topic','Filename','Date'])
            st.dataframe(df_docs, use_container_width=True)
            del_doc = st.selectbox("Delete Document", ["None"] + [f"{d[1]} - {d[2]} - {d[3]}" for d in docs])
            if del_doc!= "None":
                did = [d[0] for d in docs if f"{d[1]} - {d[2]} - {d[3]}" == del_doc][0]
                st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
                if st.button("Delete Document"):
                    delete_document(did)
                    st.success("Document deleted")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No documents uploaded yet")

    if is_super:
        with tab_list[7]:
            st.subheader("Manage Admins")
            st.markdown("#### Add New Admin")
            aname = st.text_input("Admin Name", key="aname")
            auser = st.text_input("Admin Username", key="auser")
            apwd = st.text_input("Admin Password", type="password", key="apwd")
            arole = st.selectbox("Role", ["admin", "super_admin"])
            if st.button("Create Admin"):
                if not all([aname.strip(), auser.strip(), apwd]):
                    st.error("Fill all fields")
                else:
                    result = add_admin(auser, apwd, aname.title().strip(), arole)
                    if result == "success": st.success(f"Admin {aname} created as {arole}")
                    elif result == "exists": st.error("Admin username exists")
                    else: st.error("Failed")

            st.divider()
            st.markdown("#### Edit/Delete Admin")
            c.execute("SELECT id,username,name,role FROM admins")
            admins = c.fetchall()
            df_admins = pd.DataFrame(admins, columns=['ID','Username','Name','Role'])
            st.dataframe(df_admins, use_container_width=True)

            edit_admin_sel = st.selectbox("Select Admin to Edit", ["None"] + [f"{a[2]} - {a[1]} - {a[3]}" for a in admins])
            if edit_admin_sel!= "None":
                aid = [a[0] for a in admins if f"{a[2]} - {a[1]} - {a[3]}" == edit_admin_sel][0]
                admin_data = [a for a in admins if a[0] == aid][0]

                col1, col2 = st.columns(2)
                with col1:
                    new_aname = st.text_input("Admin Name", value=admin_data[2])
                    new_auser = st.text_input("Username", value=admin_data[1])
                with col2:
                    new_apwd = st.text_input("New Password", type="password", placeholder="Leave blank to keep")
                    new_arole = st.selectbox("Role", ["admin", "super_admin"],
                                             index=["admin", "super_admin"].index(admin_data[3]))

                if st.button("Update Admin"):
                    result = update_admin_profile(aid, new_auser, new_apwd, new_aname.title().strip(), new_arole)
                    if result == "success":
                        st.success("Admin updated successfully")
                        st.rerun()
                    elif result == "exists":
                        st.error("Username already taken")
                    else:
                        st.error("Update failed")

                st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
                if st.button("Delete This Admin", key="del_admin_btn"):
                    if aid == st.session_state.user[0]:
                        st.error("You cannot delete your own account while logged in")
                    else:
                        result = delete_admin(aid)
                        if result == "success":
                            st.success("Admin deleted")
                            st.rerun()
                        elif result == "cannot_delete_super":
                            st.error("Cannot delete main superadmin account - ID 1 is protected")
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br><center style='color:white;opacity:0.9;font-weight:600;text-shadow:0 2px 4px rgba(0,0,0,0.3);'>© 2026 KingsElite School | Excellence • Discipline • Success</center>", unsafe_allow_html=True)
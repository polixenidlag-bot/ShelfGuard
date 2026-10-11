import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from streamlit_qrcode_scanner import qrcode_scanner

# ----------------------------------------------------
# 1. ΡΥΘΜΙΣΗ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ (SQLITE)
# ----------------------------------------------------
conn = sqlite3.connect("inventory.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS products (
        barcode TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        rule_days INTEGER NOT NULL
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT NOT NULL,
        barcode TEXT NOT NULL,
        product_name TEXT NOT NULL,
        expiry_date DATE NOT NULL,
        withdrawal_date DATE NOT NULL,
        status TEXT DEFAULT 'Pending'
    )
''')
conn.commit()

# ----------------------------------------------------
# 2. ΔΙΑΜΟΡΦΩΣΗ ΣΕΛΙΔΑΣ STREAMLIT
# ----------------------------------------------------
st.set_page_config(page_title="ShelfGuard", page_icon="🧊", layout="centered")

st.title("🧊 ShelfGuard - Έλεγχος Αποσύρσεων")

# Επιλογή Ψυγείου / Τμήματος
DEPARTMENTS = [
    "Ψυγείο 1: Γάλατα-Χυμοί",
    "Ψυγείο 2: Γιαούρτια",
    "Ψυγείο 3: ΣΕΡΒΙΣ",
    "Ψυγείο 4: ΒΟΥΤΥΡΟ",
    "Ψυγεία ΑΠΟΘΗΚΗ"
]

selected_dept = st.selectbox("📍 Επιλέξτε Τμήμα / Ψυγείο:", DEPARTMENTS)

st.divider()

# ----------------------------------------------------
# 3. ΣΑΡΩΣΗ BARCODE & ΚΑΤΑΧΩΡΗΣΗ
# ----------------------------------------------------
st.subheader("📷 Σάρωση / Καταχώρηση Προϊόντος")

# Κουμπί ενεργοποίησης κάμερας σαρωτή (διορθωμένο)
scanned_code = qrcode_scanner(key='barcode_scanner')

# Εναλλακτικά πεδίο χειροκίνητης πληκτρολόγησης αν δεν γίνει σάρωση
if not scanned_code:
    scanned_code = st.text_input("Ή πληκτρολογήστε χειροκίνητα το Barcode:")

if scanned_code:
    c.execute("SELECT name, rule_days FROM products WHERE barcode = ?", (scanned_code,))
    product = c.fetchone()
    
    if product:
        prod_name, rule_days = product
        st.success(f"✅ Βρέθηκε: **{prod_name}** (Κανόνας: -{rule_days} ημέρες)")
        
        expiry_input = st.date_input("📅 Ημερομηνία Λήξης (από τη συσκευασία):", datetime.today())
        
        if st.button("➕ Προσθήκη στις Αποσύρσεις"):
            withdrawal_date = expiry_input - timedelta(days=rule_days)
            c.execute('''
                INSERT INTO withdrawals (department, barcode, product_name, expiry_date, withdrawal_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (selected_dept, scanned_code, prod_name, expiry_input, withdrawal_date))
            conn.commit()
            st.toast(f"Προστέθηκε το {prod_name}!", icon="🎉")
            st.rerun()
            
    else:
        st.warning("⚠️ Νέο Προϊόν! Παρακαλώ καταχωρίστε τα στοιχεία του:")
        new_name = st.text_input("Όνομα Προϊόντος:")
        new_rule = st.number_input("Ημέρες Κανόνα (Πριν τη Λήξη):", min_value=1, max_value=365, value=7)
        expiry_input = st.date_input("📅 Ημερομηνία Λήξης (από τη συσκευασία):", datetime.today(), key="new_exp")
        
        if st.button("💾 Αποθήκευση Προϊόντος & Καταχώρηση"):
            if new_name:
                c.execute("INSERT INTO products (barcode, name, rule_days) VALUES (?, ?, ?)",
                          (scanned_code, new_name, new_rule))
                
                withdrawal_date = expiry_input - timedelta(days=new_rule)
                c.execute('''
                    INSERT INTO withdrawals (department, barcode, product_name, expiry_date, withdrawal_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (selected_dept, scanned_code, new_name, expiry_input, withdrawal_date))
                conn.commit()
                st.success("Το προϊόν αποθηκεύτηκε στη βάση και προστέθηκε στις αποσύρσεις!")
                st.rerun()
            else:
                st.error("Παρακαλώ συμπληρώστε το όνομα του προϊόντος.")

st.divider()

# ----------------------------------------------------
# 4. ΛΙΣΤΑ ΑΠΟΣΥΡΣΕΩΝ ΑΝΑ ΨΥΓΕΙΟ
# ----------------------------------------------------
st.subheader(f"🚨 Λίστα Αποσύρσεων - {selected_dept}")

df_withdrawals = pd.read_sql_query('''
    SELECT id, product_name AS "Προϊόν", expiry_date AS "Λήξη", withdrawal_date AS "Απόσυρση", status
    FROM withdrawals
    WHERE department = ? AND status = 'Pending'
    ORDER BY withdrawal_date ASC
''', conn, params=(selected_dept,))

if not df_withdrawals.empty:
    today = datetime.today().date()
    
    for index, row in df_withdrawals.iterrows():
        w_date = datetime.strptime(str(row['Απόσυρση']), "%Y-%m-%d").date()
        exp_date = datetime.strptime(str(row['Λήξη']), "%Y-%m-%d").date()
        
        w_date_str = w_date.strftime("%d/%m/%Y")
        
        if w_date == today:
            badge = "🚨 ΑΠΟΣΥΡΣΗ ΣΗΜΕΡΑ"
            color = "#ff4b4b"
        elif w_date == today + timedelta(days=1):
            badge = "⚠️ ΑΠΟΣΥΡΣΗ ΑΥΡΙΟ"
            color = "#ffa500"
        else:
            badge = "⏳ OK"
            color = "#4caf50"
            
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{row['Προϊόν']}**")
            st.caption(f"Λήξη: {exp_date.strftime('%d/%m/%Y')} | Απόσυρση: {w_date_str}")
        with col2:
            st.markdown(f"<span style='color:{color}; font-weight:bold;'>{badge}</span>", unsafe_allow_html=True)
        with col3:
            if st.button("✔️", key=f"btn_{row['id']}"):
                c.execute("UPDATE withdrawals SET status = 'Done' WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
        st.markdown("---")
else:
    st.info("Δεν υπάρχουν εκκρεμείς αποσύρσεις για αυτό το τμήμα.")

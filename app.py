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

# Αυτόματη προσθήκη στήλης department αν δεν υπάρχει
try:
    c.execute("ALTER TABLE products ADD COLUMN department TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

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

# Tabs πλοήγησης
tab1, tab2, tab3 = st.tabs(["📷 Σάρωση & Αποσύρσεις", "📦 Λίστα Προϊόντων", "📂 Μαζική Εισαγωγή Excel"])

# Επιλογή Ψυγείου / Τμήματος (κοινή για σάρωση)
DEPARTMENTS = [
    "Ψυγείο 1: Γάλατα-Χυμοί",
    "Ψυγείο 2: Γιαούρτια",
    "Ψυγείο 3: ΣΕΡΒΙΣ",
    "Ψυγείο 4: ΒΟΥΤΥΡΟ",
    "Ψυγεία ΑΠΟΘΗΚΗ"
]

# ----------------------------------------------------
# TAB 1: ΣΑΡΩΣΗ & ΑΠΟΣΥΡΣΕΙΣ
# ----------------------------------------------------
with tab1:
    selected_dept = st.selectbox("📍 Επιλέξτε Τμήμα / Ψυγείο:", DEPARTMENTS, key="dept_tab1")
    st.divider()
    
    st.subheader("📷 Σάρωση / Καταχώρηση Προϊόντος")
    scanned_code = qrcode_scanner(key='barcode_scanner')

    if not scanned_code:
        scanned_code = st.text_input("Ή πληκτρολογήστε χειροκίνητα το Barcode:", key="manual_bc")

    if scanned_code:
        c.execute("SELECT name, rule_days FROM products WHERE barcode = ?", (scanned_code,))
        product = c.fetchone()
        
        if product:
            prod_name, rule_days = product
            st.success(f"✅ Βρέθηκε: **{prod_name}** (Κανόνας: -{rule_days} ημέρες)")
            
            expiry_input = st.date_input("📅 Ημερομηνία Λήξης (από τη συσκευασία):", datetime.today(), format="DD/MM/YYYY", key="exp_date_1")
            
            if st.button("➕ Προσθήκη στις Αποσύρσεις", key="add_w_btn"):
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
            new_name = st.text_input("Όνομα Προϊόντος:", key="new_n")
            new_rule = st.number_input("Ημέρες Κανόνα (Πριν τη Λήξη):", min_value=1, max_value=365, value=7, key="new_r")
            expiry_input = st.date_input("📅 Ημερομηνία Λήξης (από τη συσκευασία):", datetime.today(), key="new_exp", format="DD/MM/YYYY")
            
            if st.button("💾 Αποθήκευση Προϊόντος & Καταχώρηση", key="save_new_btn"):
                if new_name:
                    c.execute("INSERT INTO products (barcode, name, rule_days, department) VALUES (?, ?, ?, ?)",
                              (scanned_code, new_name, new_rule, selected_dept))
                    
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

# ----------------------------------------------------
# TAB 2: ΛΙΣΤΑ ΠΡΟΪΟΝΤΩΝ
# ----------------------------------------------------
with tab2:
    st.subheader("📦 Όλα τα Αποθηκευμένα Προϊόντα")
    try:
        df_products = pd.read_sql_query("SELECT barcode AS 'Barcode', name AS 'Όνομα Προϊόντος', rule_days AS 'Ημέρες Κανόνα', department AS 'Τμήμα' FROM products", conn)
        if not df_products.empty:
            st.dataframe(df_products, use_container_width=True)
            st.caption(f"Συνολικά προϊόντα στη βάση: {len(df_products)}")
        else:
            st.info("Δεν υπάρχουν αποθηκευμένα προϊόντα ακόμα. Μπορείτε να ανεβάσετε το αρχείο σας στο tab 'Μαζική Εισαγωγή Excel'.")
    except Exception as e:
        st.error(f"Σφάλμα ανάγνωσης λίστας: {e}")

# ----------------------------------------------------
# TAB 3: ΜΑΖΙΚΗ ΕΙΣΑΓΩΓΗ EXCEL / CSV
# ----------------------------------------------------
with tab3:
    st.subheader("📂 Μαζική Εισαγωγή από Excel / CSV")
    st.markdown("""
    Ανεβάστε το αρχείο σας (όπως το έχετε στο Google Sheets με στήλες **Barcode**, **Όνομα Προϊόντος**, **Ημέρες Κανόνα** και **Τμήμα**) για να περαστούν όλα αυτόματα!
    """)
    
    uploaded_file = st.file_uploader("Επιλέξτε αρχείο Excel (.xlsx) ή CSV", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_import = pd.read_csv(uploaded_file)
            else:
                df_import = pd.read_excel(uploaded_file)
            
            st.success("Το αρχείο διαβάστηκε επιτυχώς! Προεπισκόπηση:")
            st.dataframe(df_import.head(), use_container_width=True)
            
            if st.button("🚀 Οριστική Εισαγωγή Προϊόντων στη Βάση"):
                imported_count = 0
                for _, row in df_import.iterrows():
                    bc = str(row.get('Barcode', row.iloc[0] if len(row) > 0 else '')).strip()
                    name = str(row.get('Όνομα Προϊόντος', row.iloc[1] if len(row) > 1 else '')).strip()
                    
                    rules_val = 7
                    for col in row.index:
                        if 'Ημέρες' in str(col) or 'Κανόνα' in str(col):
                            try:
                                rules_val = int(row[col])
                            except:
                                pass
                    
                    dept_val = "Ψυγείο 1: Γάλατα-Χυμοί"
                    for col in row.index:
                        if 'Τμήμα' in str(col):
                            val_str = str(row[col]).strip()
                            if val_str and val_str != 'nan':
                                dept_val = val_str
                    
                    if bc and bc != 'nan' and name and name != 'nan':
                        c.execute('''
                            INSERT OR REPLACE INTO products (barcode, name, rule_days, department)
                            VALUES (?, ?, ?, ?)
                        ''', (bc, name, rules_val, dept_val))
                        imported_count += 1
                        
                conn.commit()
                st.success(f"Επιτυχής εισαγωγή / ενημέρωση {imported_count} προϊόντων! Πηγαίνετε στο tab 'Λίστα Προϊόντων' για να τα δείτε.")
        except Exception as e:
            st.error(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")

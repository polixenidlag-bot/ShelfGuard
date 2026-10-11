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
# 2. ΜΟΝΤΕΡΝΑ ΔΙΑΜΟΡΦΩΣΗ ΣΕΛΙΔΑΣ & UI (CSS)
# ----------------------------------------------------
st.set_page_config(page_title="ShelfGuard", page_icon="🧊", layout="centered")

modern_ui_style = """
<style>
/* Απόκρυψη Streamlit Header/Footer/Menu */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Γενικό φόντο & γραμματοσειρά */
.stApp {
    background-color: #f4f6f9;
}

/* Στρογγυλεμένα κουμπιά */
.stButton>button {
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.3s ease;
}

/* Καρτέλες (Tabs) ομορφότερες */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0px 0px;
    padding: 10px 20px;
    background-color: #e9ecef;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #0d6efd !important;
}
</style>
"""
st.markdown(modern_ui_style, unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #1e293b;'>🧊 ShelfGuard</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 20px;'>Έξυπνος Έλεγχος Αποσύρσεων & Ημερομηνιών</p>", unsafe_allow_html=True)

# Tabs πλοήγησης
tab1, tab2 = st.tabs(["📷 Σάρωση & Αποσύρσεις", "📦 Λίστα Προϊόντων"])

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
    with st.container(border=True):
        selected_dept = st.selectbox("📍 Επιλέξτε Τμήμα / Ψυγείο:", DEPARTMENTS, key="dept_tab1")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("📷 Σάρωση / Καταχώρηση Προϊόντος")
        scanned_code = qrcode_scanner(key='barcode_scanner')

        if not scanned_code:
            scanned_code = st.text_input("Ή πληκτρολογήστε χειροκίνητα το Barcode:", key="manual_bc", placeholder="π.χ. 520101...")

        if scanned_code:
            c.execute("SELECT name, rule_days FROM products WHERE barcode = ?", (scanned_code,))
            product = c.fetchone()
            
            if product:
                prod_name, rule_days = product
                st.success(f"✅ Βρέθηκε: **{prod_name}** (Κανόνας: -{rule_days} ημέρες)")
                
                c.execute("UPDATE products SET department = ? WHERE barcode = ?", (selected_dept, scanned_code))
                conn.commit()
                
                expiry_input = st.date_input("📅 Ημερομηνία Λήξης (από τη συσκευασία):", datetime.today(), format="DD/MM/YYYY", key="exp_date_1")
                
                if st.button("➕ Προσθήκη στις Αποσύρσεις", key="add_w_btn", type="primary"):
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
                new_name = st.text_input("Όνομα Προϊόντος:", key="new_n", placeholder="π.χ. ΓΑΛΑ ΦΡΕΣΚΟ 1L")
                new_rule = st.number_input("Ημέρες Κανόνα (Πριν τη Λήξη):", min_value=1, max_value=365, value=7, key="new_r")
                expiry_input = st.date_input("📅 Ημερομηνία Λήξης (από τη συσκευασία):", datetime.today(), key="new_exp", format="DD/MM/YYYY")
                
                if st.button("💾 Αποθήκευση Προϊόντος & Καταχώρηση", key="save_new_btn", type="primary"):
                    if new_name:
                        c.execute("INSERT OR REPLACE INTO products (barcode, name, rule_days, department) VALUES (?, ?, ?, ?)",
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

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(f"🚨 Λίστα Αποσύρσεων - {selected_dept}")

    # --- Εργαλεία: Αναζήτηση & Ιστορικό ---
    col_search, col_hist = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Αναζήτηση...", key="search_w", placeholder="Όνομα προϊόντος...")
    with col_hist:
        st.markdown("<br>", unsafe_allow_html=True)
        show_history = st.checkbox("📂 Ιστορικό", key="show_hist_cb")

    if show_history:
        query_str = '''
            SELECT id, product_name AS "Προϊόν", expiry_date AS "Λήξη", withdrawal_date AS "Απόσυρση", status
            FROM withdrawals
            WHERE department = ?
            ORDER BY withdrawal_date ASC
        '''
    else:
        query_str = '''
            SELECT id, product_name AS "Προϊόν", expiry_date AS "Λήξη", withdrawal_date AS "Απόσυρση", status
            FROM withdrawals
            WHERE department = ? AND status = 'Pending'
            ORDER BY withdrawal_date ASC
        '''

    df_withdrawals = pd.read_sql_query(query_str, conn, params=(selected_dept,))

    if search_query and not df_withdrawals.empty:
        df_withdrawals = df_withdrawals[df_withdrawals['Προϊόν'].str.contains(search_query, case=False, na=False)]

    # --- Κουμπί Ημερήσιας Αναφοράς για Viber ---
    pending_df = pd.read_sql_query('''
        SELECT product_name, expiry_date, withdrawal_date 
        FROM withdrawals 
        WHERE department = ? AND status = 'Pending' 
        ORDER BY withdrawal_date ASC
    ''', conn, params=(selected_dept,))

    if not pending_df.empty:
        with st.expander("📋 Δημιουργία Ημερήσιας Αναφοράς για Viber"):
            report_lines = [f"📊 *ΑΝΑΦΟΡΑ ΑΠΟΣΥΡΣΕΩΝ* - *{selected_dept}*"]
            report_lines.append(f"📅 Ημερομηνία: {datetime.today().strftime('%d/%m/%Y')}\n")
            for _, r in pending_df.iterrows():
                p_name = r['product_name']
                exp_d = datetime.strptime(str(r['expiry_date']), "%Y-%m-%d").strftime("%d/%m/%Y")
                w_d = datetime.strptime(str(r['withdrawal_date']), "%Y-%m-%d").strftime("%d/%m/%Y")
                report_lines.append(f"• *{p_name}* | Λήξη: {exp_d} | Απόσυρση: {w_d}")
            
            report_text = "\n".join(report_lines)
            st.text_area("Αντιγράψτε το κείμενο:", value=report_text, height=140, key="report_textarea")
            st.caption("Αντιγράψτε και στείλτε το απευθείας στο Viber!")

    st.markdown("<br>", unsafe_allow_html=True)

    if not df_withdrawals.empty:
        today = datetime.today().date()
        
        for index, row in df_withdrawals.iterrows():
            w_date = datetime.strptime(str(row['Απόσυρση']), "%Y-%m-%d").date()
            exp_date = datetime.strptime(str(row['Λήξη']), "%Y-%m-%d").date()
            status = row['status']
            
            w_date_str = w_date.strftime("%d/%m/%Y")
            
            if status == 'Done':
                badge = "✅ ΟΛΟΚΛΗΡΩΘΗΚΕ"
                border_color = "#e9ecef"
            elif w_date == today:
                badge = "🚨 ΑΠΟΣΥΡΣΗ ΣΗΜΕΡΑ"
                border_color = "#ff4b4b"
            elif w_date == today + timedelta(days=1):
                badge = "⚠️ ΑΠΟΣΥΡΣΗ ΑΥΡΙΟ"
                border_color = "#ffa500"
            else:
                badge = "⏳ OK"
                border_color = "#4caf50"
                
            # Εμφάνιση μέσα σε όμορφα "Cards" με περίγραμμα
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{row['Προϊόν']}**")
                    st.caption(f"🗓️ Λήξη: {exp_date.strftime('%d/%m/%Y')} | ⏰ Απόσυρση: {w_date_str}")
                with col2:
                    st.markdown(f"<span style='font-size: 13px; font-weight: bold;'>{badge}</span>", unsafe_allow_html=True)
                with col3:
                    if status == 'Pending':
                        if st.button("✔️", key=f"done_{row['id']}"):
                            c.execute("UPDATE withdrawals SET status = 'Done' WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.rerun()
                    else:
                        if st.button("↩️", key=f"undo_{row['id']}"):
                            c.execute("UPDATE withdrawals SET status = 'Pending' WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.rerun()
    else:
        st.info("Δεν βρέθηκαν προϊόντα στη λίστα για αυτό το τμήμα.")

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
            st.info("Δεν υπάρχουν αποθηκευμένα προϊόντα ακόμα.")
    except Exception as e:
        st.error(f"Σφάλμα ανάγνωσης λίστας: {e}")


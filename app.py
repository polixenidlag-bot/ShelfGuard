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
# 2. ΕΝΤΥΠΩΣΙΑΚo UI & MODERN CSS
# ----------------------------------------------------
st.set_page_config(page_title="ShelfGuard", page_icon="🧊", layout="centered")

st.markdown("""
<style>
/* Απόκρυψη Streamlit Header/Footer/Menu */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Γενικό φόντο */
.stApp {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

/* Κάρτες / Containers με σκιά και στρογγυλεμένες γωνίες */
div[data-testid="stVerticalBlock"] > div[style*="border"] {
    background: #ffffff;
    border-radius: 16px !important;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(226, 232, 240, 0.8) !important;
}

/* Κουμπιά με εφέ */
.stButton>button {
    border-radius: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
    transition: all 0.2s ease-in-out;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* Custom Tabs Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background-color: transparent;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 12px 12px 0px 0px;
    padding: 12px 24px;
    background-color: #ffffff;
    font-weight: 700;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
    color: #ffffff !important;
}

/* Metric boxes custom look */
div[data-testid="stMetric"] {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 14px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.04);
    border: 1px solid #e2e8f0;
}
</style>
""", unsafe_allow_html=True)

# Τίτλος εφαρμογής
st.markdown("<h1 style='text-align: center; color: #0f172a; font-weight: 800; font-size: 24px; margin-bottom: 0px;'>🧊 ShelfGuard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #1e293b; font-size: 14px; font-weight: 700; margin-top: 5px; margin-bottom: 25px;'>ΣΥΣΤΗΜΑ ΑΣΦΑΛΟΥΣ ΕΛΕΓΧΟΥ ΗΜΕΡΟΜΗΝΙΩΝ ΚΑΙ ΑΠΟΣΥΡΣΕΩΝ</p>", unsafe_allow_html=True)

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
    with st.container():
        selected_dept = st.selectbox("📍 Επιλέξτε Τμήμα / Ψυγείο:", DEPARTMENTS, key="dept_tab1")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- Υπολογισμός Metrics ---
    today_metric_date = datetime.today().date()
    c.execute("SELECT COUNT(*) FROM withdrawals WHERE department = ? AND status = 'Pending' AND withdrawal_date = ?", (selected_dept, today_metric_date))
    count_today = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM withdrawals WHERE department = ? AND status = 'Pending'", (selected_dept,))
    count_total_pending = c.fetchone()[0]

    m1, m2 = st.columns(2)
    with m1:
        st.metric("🚨 Σημερινές Αποσύρσεις", count_today)
    with m2:
        st.metric("⏳ Εκκρεμείς Αποσύρσεις", count_total_pending)
        
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
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
                
                if st.button("➕ Προσθήκη στις Αποσύρσεις", key="add_w_btn", type="primary", use_container_width=True):
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
                
                if st.button("💾 Αποθήκευση Προϊόντος & Καταχώρηση", key="save_new_btn", type="primary", use_container_width=True):
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

    # --- ΟΡΓΑΝΩΜΕΝΕΣ ΕΝΕΡΓΕΙΕΣ & ΕΡΓΑΛΕΙΑ (Ψηλά και ευδιάκριτα) ---
    with st.container():
        col_search, col_hist = st.columns([2, 1])
        with col_search:
            search_query = st.text_input("🔍 Αναζήτηση προϊόντος...", key="search_w", placeholder="Γράψτε όνομα...")
        with col_hist:
            st.markdown("<br>", unsafe_allow_html=True)
            show_history = st.checkbox("📂 Εμφάνιση Ιστορικού", key="show_hist_cb")

    # Κουμπί / Expander Αναφοράς Viber οργανωμένο ξεχωριστά
    pending_df = pd.read_sql_query('''
        SELECT product_name, expiry_date, withdrawal_date 
        FROM withdrawals 
        WHERE department = ? AND status = 'Pending' 
        ORDER BY withdrawal_date ASC
    ''', conn, params=(selected_dept,))

    if not pending_df.empty:
        with st.expander("📋 Ενέργεια: Δημιουργία Αναφοράς για Viber"):
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

    if not df_withdrawals.empty:
        today = datetime.today().date()
        
        for index, row in df_withdrawals.iterrows():
            w_date = datetime.strptime(str(row['Απόσυρση']), "%Y-%m-%d").date()
            exp_date = datetime.strptime(str(row['Λήξη']), "%Y-%m-%d").date()
            status = row['status']
            
            w_date_str = w_date.strftime("%d/%m/%Y")
            
            # --- ΝΕΑ ΧΡΩΜΑΤΙΚΗ ΛΟΓΙΚΗ STATUS ---
            if status == 'Done':
                badge = "✅ ΟΛΟΚΛΗΡΩΘΗΚΕ"
                badge_bg = "#f1f5f9"
                badge_color = "#64748b"
            elif w_date < today:
                badge = "🔴 ΕΧΕΙ ΠΕΡΑΣΕΙ Η ΗΜΕΡΟΜΗΝΙΑ"
                badge_bg = "#fee2e2"
                badge_color = "#991b1b"
            elif w_date == today or w_date == today + timedelta(days=1):
                badge = "🟠 ΑΠΟΣΥΡΣΗ ΣΗΜΕΡΑ/ΑΜΕΣΑ"
                badge_bg = "#ffedd5"
                badge_color = "#c2410c"
            else:
                badge = "🟢 ΕΝΕΡΓΟ (OK)"
                badge_bg = "#dcfce7"
                badge_color = "#166534"
                
            # Κάρτα προϊόντος
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"<div style='font-size: 18px; font-weight: 800; color: #0f172a; margin-bottom: 6px;'>{row['Προϊόν']}</div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='line-height: 1.6;'>"
                        f"<span style='background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 6px; font-size: 15px; font-weight: 800;'>🗓️ Λήξη: {exp_date.strftime('%d/%m/%Y')}</span>"
                        f"<br>"
                        f"<span style='background: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 6px; font-size: 16px; font-weight: 900;'>⏰ Απόσυρση: {w_date_str}</span>"
                        f"</div>", 
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(f"<div style='font-size: 11px; font-weight: 700; background: {badge_bg}; color: {badge_color}; padding: 6px 10px; border-radius: 8px; text-align: center;'>{badge}</div>", unsafe_allow_html=True)
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


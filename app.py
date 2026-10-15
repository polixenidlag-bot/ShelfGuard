import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image

# Προσπάθεια εισαγωγής βιβλιοθήκης ανάγνωσης barcode από φωτογραφία
try:
    from pyzbar.pyzbar import decode
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False

st.set_page_config(page_title="ShelfGuard", page_icon="🧊", layout="centered")

st.title("🧊 ShelfGuard")
st.write("ΣΥΣΤΗΜΑ ΑΣΦΑΛΟΥΣ ΕΛΕΓΧΟΥ ΗΜΕΡΟΜΗΝΙΩΝ ΚΑΙ ΑΠΟΣΥΡΣΕΩΝ")

# Αρχικοποίηση τοπικής μνήμης
if "products_db" not in st.session_state:
    st.session_state.products_db = pd.DataFrame(columns=["barcode", "name", "rule_days", "department"])

if "withdrawals_db" not in st.session_state:
    st.session_state.withdrawals_db = pd.DataFrame(columns=[
        "department", "barcode", "product_name", "expiry_date", "withdrawal_date", "quantity", "status"
    ])

if "scanned_code" not in st.session_state:
    st.session_state.scanned_code = ""

tab1, tab2 = st.tabs(["📋 Σάρωση & Αποσύρσεις", "📦 Λίστα Προϊόντων"])

DEPARTMENTS = [
    "Ψυγείο 1: Γάλατα-Χυμοί",
    "Ψυγείο 2: Γιαούρτια",
    "Ψυγείο 3: ΣΕΡΒΙΣ",
    "Ψυγείο 4: ΒΟΥΤΥΡΟ",
    "Ψυγεία ΑΠΟΘΗΚΗ"
]

if "list_filter" not in st.session_state:
    st.session_state.list_filter = "pending_all"

df_products = st.session_state.products_db
df_withdrawals = st.session_state.withdrawals_db

with tab1:
    selected_dept = st.selectbox("📍 Επιλέξτε Τμήμα / Ψυγείο:", DEPARTMENTS, key="dept_tab1")
    
    today_metric_date = datetime.today().date()
    count_today = 0
    count_total_pending = 0
    
    if not df_withdrawals.empty and all(col in df_withdrawals.columns for col in ['department', 'status', 'withdrawal_date']):
        dept_w = df_withdrawals[df_withdrawals['department'] == selected_dept]
        pending_w = dept_w[dept_w['status'] == 'Pending']
        count_total_pending = len(pending_w)
        if 'withdrawal_date' in pending_w.columns:
            today_str = today_metric_date.strftime("%Y-%m-%d")
            count_today = len(pending_w[pending_w['withdrawal_date'].astype(str).str.startswith(today_str)])

    m1, m2 = st.columns(2)
    with m1:
        st.metric("🚨 Σημερινές Αποσύρσεις", count_today)
        if st.button("🔍 Φίλτρο: Σημερινά", key="btn_f_today", use_container_width=True):
            st.session_state.list_filter = "today"
            st.rerun()
    with m2:
        st.metric("⏳ Εκκρεμείς Αποσύρσεις", count_total_pending)
        if st.button("🔍 Φίλτρο: Εκκρεμείς", key="btn_f_pend", use_container_width=True):
            st.session_state.list_filter = "pending_all"
            st.rerun()
        
    st.divider()
    st.subheader("📦 Καταχώρηση Προϊόντος")
    
    # Έλεγχος αν τραβήχτηκε φωτογραφία από την κάμερα
    camera_file = st.camera_input("📷 Τραβήξτε φωτογραφία το Barcode", key="cam_input_tab1")
    
    if camera_file is not None:
        if HAS_PYZBAR:
            try:
                img = Image.open(camera_file)
                decoded_objs = decode(img)
                if decoded_objs:
                    scanned_text = decoded_objs[0].data.decode('utf-8')
                    st.session_state.scanned_code = scanned_text
                    st.success(f"Επιτυχής σάρωση Barcode: {scanned_text}")
                else:
                    st.warning("Δεν εντοπίστηκε barcode στη φωτογραφία. Δοκιμάστε ξανά πιο κοντά.")
            except Exception as e:
                st.error(f"Σφάλμα ανάγνωσης: {e}")
        else:
            st.error("⚠️ Απαιτείται η βιβλιοθήκη `pyzbar` στο `requirements.txt` για την αυτόματη ανάγνωση. (Εναλλακτικά, πληκτρολογήστε τον κωδικό χειροκίνητα παρακάτω).")

    # 1. ΠΡΩΤΑ εμφανίζεται το πεδίο κειμένου (με τιμή από τη σάρωση ή χειροκίνητη)
    default_val = st.session_state.scanned_code if st.session_state.scanned_code else ""
    active_code = st.text_input(
        "Barcode Προϊόντος:", 
        value=default_val,
        key="manual_bc_tab1", 
        placeholder="Σκαναρίστε με την κάμερα ή πληκτρολογήστε..."
    )

    if active_code:
        product_row = None
        if not df_products.empty and 'barcode' in df_products.columns:
            match = df_products[df_products['barcode'].astype(str) == str(active_code)]
            if not match.empty:
                product_row = match.iloc[0]
        
        if product_row is not None:
            prod_name = product_row['name']
            rule_days = int(product_row['rule_days'])
            st.success(f"✅ Βρέθηκε: {prod_name} (Κανόνας: -{rule_days} ημέρες)")
            
            expiry_input = st.date_input("📅 Ημερομηνία Λήξης:", datetime.today(), format="DD/MM/YYYY", key="exp_date_1")
            qty_input = st.number_input("📦 Τεμάχια:", min_value=1, value=1, key="qty_input_1")
            
            if st.button("➕ Προσθήκη στις Αποσύρσεις", key="add_w_btn", use_container_width=True):
                withdrawal_date = expiry_input - timedelta(days=rule_days)
                new_row = pd.DataFrame([{
                    "department": selected_dept,
                    "barcode": str(active_code),
                    "product_name": prod_name,
                    "expiry_date": str(expiry_input),
                    "withdrawal_date": str(withdrawal_date),
                    "quantity": qty_input,
                    "status": "Pending"
                }])
                st.session_state.withdrawals_db = pd.concat([st.session_state.withdrawals_db, new_row], ignore_index=True)
                st.session_state.scanned_code = ""
                st.success("Προστέθηκε επιτυχώς!")
                st.rerun()
                
        else:
            st.warning("⚠️ Νέο Προϊόν! Καταχωρίστε τα στοιχεία του:")
            new_name = st.text_input("Όνομα Προϊόντος:", key="new_n")
            new_rule = st.number_input("Ημέρες Κανόνα (Πριν τη Λήξη):", min_value=1, max_value=365, value=7, key="new_r")
            expiry_input = st.date_input("📅 Ημερομηνία Λήξης:", datetime.today(), key="new_exp", format="DD/MM/YYYY")
            qty_input_new = st.number_input("📦 Τεμάχια:", min_value=1, value=1, key="qty_input_new")
            
            if st.button("💾 Αποθήκευση Προϊόντος & Καταχώρηση", key="save_new_btn", use_container_width=True):
                if new_name:
                    new_prod = pd.DataFrame([{
                        "barcode": str(active_code),
                        "name": new_name,
                        "rule_days": new_rule,
                        "department": selected_dept
                    }])
                    st.session_state.products_db = pd.concat([st.session_state.products_db, new_prod], ignore_index=True)
                    
                    withdrawal_date = expiry_input - timedelta(days=new_rule)
                    new_w = pd.DataFrame([{
                        "department": selected_dept,
                        "barcode": str(active_code),
                        "product_name": new_name,
                        "expiry_date": str(expiry_input),
                        "withdrawal_date": str(withdrawal_date),
                        "quantity": qty_input_new,
                        "status": "Pending"
                    }])
                    st.session_state.withdrawals_db = pd.concat([st.session_state.withdrawals_db, new_w], ignore_index=True)
                    st.session_state.scanned_code = ""
                    
                    st.success("Αποθηκεύτηκε επιτυχώς!")
                    st.rerun()
                else:
                    st.error("Παρακαλώ συμπληρώστε το όνομα του προϊόντος.")

    st.divider()
    st.subheader(f"🚨 Λίστα Αποσύρσεων - {selected_dept}")

    col_search, col_fbtn = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Αναζήτηση ανά Barcode ή Όνομα...", key="search_w", placeholder="Γράψτε όνομα...")
    with col_fbtn:
        filter_mode = st.radio(
            "Προβολή:",
            ["⏳ Εκκρεμείς", "🚨 Σημερινά", "📂 Όλα"],
            index=0 if st.session_state.list_filter == "pending_all" else (1 if st.session_state.list_filter == "today" else 2),
            horizontal=True,
            key="radio_filter_mode"
        )

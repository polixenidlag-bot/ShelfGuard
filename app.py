import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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
    
    active_code = st.text_input("📷 Barcode Προϊόντος (Πατήστε εδώ και σκανάρετε με το πληκτρολόγιο/κάμερα):", key="manual_bc_tab1", placeholder="Σκαναρίστε ή πληκτρολογήστε...")

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
        if filter_mode == "⏳ Εκκρεμείς":
            st.session_state.list_filter = "pending_all"
        elif filter_mode == "🚨 Σημερινά":
            st.session_state.list_filter = "today"
        else:
            st.session_state.list_filter = "history"

    current_dept_w = pd.DataFrame()
    df_w_current = st.session_state.withdrawals_db
    if not df_w_current.empty and 'department' in df_w_current.columns:
        current_dept_w = df_w_current[df_w_current['department'] == selected_dept].copy()

        if st.session_state.list_filter == "today":
            today_str = today_metric_date.strftime("%Y-%m-%d")
            current_dept_w = current_dept_w[(current_dept_w['status'] == 'Pending') & (current_dept_w['withdrawal_date'].astype(str).str.startswith(today_str))]
        elif st.session_state.list_filter == "pending_all":
            current_dept_w = current_dept_w[current_dept_w['status'] == 'Pending']
        
        if search_query:
            current_dept_w = current_dept_w[
                current_dept_w['product_name'].str.contains(search_query, case=False, na=False) |
                current_dept_w['barcode'].astype(str).str.contains(search_query, case=False, na=False)
            ]

    if not current_dept_w.empty:
        for idx, row in current_dept_w.iterrows():
            try:
                w_date = datetime.strptime(str(row['withdrawal_date'])[:10], "%Y-%m-%d").date()
                exp_date = datetime.strptime(str(row['expiry_date'])[:10], "%Y-%m-%d").date()
            except:
                continue
            
            qty = row['quantity'] if pd.notnull(row['quantity']) else 1
            status = row['status']
            
            with st.container():
                st.write(f"**{row['product_name']}** ({qty} τεμ.) — Barcode: `{row['barcode']}`")
                st.write(f"🗓️ Λήξη: {exp_date.strftime('%d/%m/%Y')} | ⏰ Απόσυρση: {w_date.strftime('%d/%m/%Y')}")
                st.write(f"Κατάσταση: {status}")
                
                if status == 'Pending':
                    if st.button("✔️ Ολοκλήρωση", key=f"done_{idx}"):
                        st.session_state.withdrawals_db.loc[idx, 'status'] = 'Done'
                        st.rerun()
                else:
                    if st.button("↩️ Επαναφορά", key=f"undo_{idx}"):
                        st.session_state.withdrawals_db.loc[idx, 'status'] = 'Pending'
                        st.rerun()
                st.divider()
    else:
        st.info("Δεν βρέθηκαν προϊόντα.")

with tab2:
    st.subheader("📦 Προσθήκη Προϊόντος στη Βάση")
    # Προσθήκη πεδίου barcode και στην καρτέλα 2
    db_barcode = st.text_input("📷 Barcode Νέου Προϊόντος (Πατήστε εδώ για σκανάρισμα):", key="db_manual_bc", placeholder="Σκαναρίστε ή πληκτρολογήστε...")
    
    db_name = st.text_input("Όνομα Προϊόντος:", key="db_name_input")
    db_rule = st.number_input("Ημέρες Κανόνα (Πριν τη Λήξη):", min_value=1, max_value=365, value=7, key="db_rule_input")
    db_dept = st.selectbox("Τμήμα:", DEPARTMENTS, key="db_dept_input")
    
    if st.button("💾 Αποθήκευση Προϊόντος", key="save_db_only_btn", use_container_width=True):
        if db_barcode and db_name:
            new_prod = pd.DataFrame([{
                "barcode": str(db_barcode),
                "name": db_name,
                "rule_days": db_rule,
                "department": db_dept
            }])
            st.session_state.products_db = pd.concat([st.session_state.products_db, new_prod], ignore_index=True)
            st.success("Αποθηκεύτηκε επιτυχώς!")
            st.rerun()
        else:
            st.error("Συμπληρώστε barcode και όνομα.")

    st.divider()
    st.subheader("📋 Λίστα Αποθηκευμένων Προϊόντων")
    if not st.session_state.products_db.empty:
        st.dataframe(st.session_state.products_db, use_container_width=True)
    else:
        st.info("Δεν υπάρχουν προϊόντα ακόμα.")

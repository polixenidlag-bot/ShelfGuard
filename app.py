import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image

st.set_page_config(page_title="ShelfGuard", page_icon="🧊", layout="centered")

try:
    from pyzbar.pyzbar import decode
    HAS_PYZBAR = True
except Exception:
    HAS_PYZBAR = False

st.title("🧊 ShelfGuard")
st.write("ΣΥΣΤΗΜΑ ΑΣΦΑΛΟΥΣ ΕΛΕΓΧΟΥ ΗΜΕΡΟΜΗΝΙΩΝ ΚΑΙ ΑΠΟΣΥΡΣΕΩΝ")

if "products_db" not in st.session_state:
    st.session_state.products_db = pd.DataFrame(columns=["barcode", "name", "rule_days", "department"])

if "withdrawals_db" not in st.session_state:
    st.session_state.withdrawals_db = pd.DataFrame(columns=[
        "department", "barcode", "product_name", "expiry_date", "withdrawal_date", "quantity", "status"
    ])

DEPARTMENTS = [
    "Ψυγείο 1: Γάλατα-Χυμοί",
    "Ψυγείο 2: Γιαούρτια",
    "Ψυγείο 3: ΣΕΡΒΙΣ",
    "Ψυγείο 4: ΒΟΥΤΥΡΟ",
    "Ψυγεία ΑΠΟΘΗΚΗ"
]

tab1, tab2 = st.tabs(["📋 Σάρωση & Αποσύρσεις", "📦 Λίστα Προϊόντων"])

with tab1:
    st.subheader("📍 Επιλογή Τμήματος")
    selected_dept = st.selectbox("Επιλέξτε Ψυγείο/Τμήμα:", DEPARTMENTS, key="dept_1")
    
    st.divider()
    st.subheader("📷 Σάρωση Barcode")
    
    camera_file = st.camera_input("Τραβήξτε φωτογραφία το Barcode", key="cam_1")
    
    if camera_file is not None:
        if HAS_PYZBAR:
            try:
                img = Image.open(camera_file)
                decoded_objs = decode(img)
                if decoded_objs:
                    scanned_text = decoded_objs[0].data.decode('utf-8')
                    # Αποθηκεύουμε απευθείας στο session_state του πεδίου κειμένου και κάνουμε ανανέωση
                    st.session_state["bc_input_1"] = scanned_text
                    st.success(f"Επιτυχής σάρωση: {scanned_text}")
                    st.rerun()
                else:
                    st.warning("Δεν εντοπίστηκε barcode. Δοκιμάστε πιο κοντά.")
            except Exception as e:
                st.error(f"Σφάλμα: {e}")
        else:
            st.info("Η βιβλιοθήκη pyzbar εγκαθίσταται. Μπορείτε να γράψετε τον κωδικό χειροκίνητα παρακάτω.")

    # Πεδίο κειμένου που διαβάζει απευθείας από τη μνήμη
    barcode_input = st.text_input("Barcode Προϊόντος:", key="bc_input_1", placeholder="Σκαναρίστε ή πληκτρολογήστε...")

    if barcode_input:
        prod_match = None
        df_p = st.session_state.products_db
        if not df_p.empty and 'barcode' in df_p.columns:
            m = df_p[df_p['barcode'].astype(str) == str(barcode_input)]
            if not m.empty:
                prod_match = m.iloc[0]

        if prod_match is not None:
            p_name = prod_match['name']
            rule = int(prod_match['rule_days'])
            st.success(f"Βρέθηκε προϊόν: **{p_name}** (Κανόνας: -{rule} μέρες)")
            
            exp_date = st.date_input("Ημερομηνία Λήξης:", datetime.today(), format="DD/MM/YYYY", key="exp_d1")
            qty = st.number_input("Τεμάχια:", min_value=1, value=1, key="qty_d1")
            
            if st.button("➕ Προσθήκη στην Απόσυρση", use_container_width=True, key="add_btn_1"):
                w_date = exp_date - timedelta(days=rule)
                new_w = pd.DataFrame([{
                    "department": selected_dept,
                    "barcode": str(barcode_input),
                    "product_name": p_name,
                    "expiry_date": str(exp_date),
                    "withdrawal_date": str(w_date),
                    "quantity": qty,
                    "status": "Pending"
                }])
                st.session_state.withdrawals_db = pd.concat([st.session_state.withdrawals_db, new_w], ignore_index=True)
                st.success("Καταχωρήθηκε επιτυχώς!")
                st.rerun()
        else:
            st.warning("⚠️ Νέο προϊόν! Συμπληρώστε τα στοιχεία του:")
            new_name = st.text_input("Όνομα Προϊόντος:", key="new_p_name")
            new_rule = st.number_input("Ημέρες πριν τη λήξη για απόσυρση:", min_value=1, value=7, key="new_p_rule")
            exp_date = st.date_input("Ημερομηνία Λήξης:", datetime.today(), format="DD/MM/YYYY", key="new_exp_d")
            qty = st.number_input("Τεμάχια:", min_value=1, value=1, key="new_qty")
            
            if st.button("💾 Αποθήκευση & Καταχώρηση", use_container_width=True, key="save_new_p"):
                if new_name:
                    new_prod = pd.DataFrame([{
                        "barcode": str(barcode_input),
                        "name": new_name,
                        "rule_days": new_rule,
                        "department": selected_dept
                    }])
                    st.session_state.products_db = pd.concat([st.session_state.products_db, new_prod], ignore_index=True)
                    
                    w_date = exp_date - timedelta(days=new_rule)
                    new_w = pd.DataFrame([{
                        "department": selected_dept,
                        "barcode": str(barcode_input),
                        "product_name": new_name,
                        "expiry_date": str(exp_date),
                        "withdrawal_date": str(w_date),
                        "quantity": qty,
                        "status": "Pending"
                    }])
                    st.session_state.withdrawals_db = pd.concat([st.session_state.withdrawals_db, new_w], ignore_index=True)
                    st.success("Αποθηκεύτηκε και καταχωρήθηκε!")
                    st.rerun()
                else:
                    st.error("Βάλτε όνομα προϊόντος.")

        st.divider()
        st.subheader(f"📋 Εκκρεμείς Αποσύρσεις - {selected_dept}")
        df_w = st.session_state.withdrawals_db
        if not df_w.empty and 'department' in df_w.columns:
            dept_pending = df_w[(df_w['department'] == selected_dept) & (df_w['status'] == 'Pending')]
            if not dept_pending.empty:
                for idx, row in dept_pending.iterrows():
                    st.write(f"**{row['product_name']}** ({row['quantity']} τεμ.) | Λήξη: {row['expiry_date']}")
                    if st.button("✔️ Ολοκλήρωση", key=f"done_{idx}"):
                        st.session_state.withdrawals_db.loc[idx, 'status'] = 'Done'
                        st.rerun()
                    st.divider()
            else:
                st.info("Δεν υπάρχουν εκκρεμείς αποσύρσεις για αυτό το τμήμα.")
        else:
            st.info("Δεν υπάρχουν καταχωρήσεις ακόμα.")

with tab2:
    st.subheader("📦 Διαχείριση Προϊόντων Βάσης")
    if not st.session_state.products_db.empty:
        st.dataframe(st.session_state.products_db, use_container_width=True)
    else:
        st.info("Η λίστα προϊόντων είναι άδειη. Προσθέστε προϊόντα κάνοντας σάρωση στην πρώτη καρτέλα.")

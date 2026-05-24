import streamlit as st
import polars as pl
import duckdb
import os

from dotenv import load_dotenv
load_dotenv()

# Import core modules
from parser import extract_text_from_pdf
from agent import extract_structured_data_from_text
from pipeline import process_extracted_invoice_to_table

st.set_page_config(page_title="Enterprise Invoice Ingestion MVP", layout="wide")

st.title("📑 AI Document Ingestion & Audit Platform")
st.subheader("Dashboard — Human-in-the-Loop Review Console")
st.markdown("---")

db_path = os.path.join("data", "invoice_warehouse.db")
upload_dir = os.path.join("data", "raw_synthetic")

# --- INITIALIZE DATABASE SCHEMA ---
def get_db_connection():
    conn = duckdb.connect(db_path)
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    
    if "invoice_ledger" not in table_names:
        conn.execute("""
            CREATE TABLE invoice_ledger (
                invoice_id VARCHAR, vendor_name VARCHAR, invoice_date DATE, 
                po_reference VARCHAR, item_code VARCHAR, description VARCHAR, 
                quantity INTEGER, unit_price DOUBLE, extracted_total DOUBLE, 
                verified_total DOUBLE, calculation_anomaly BOOLEAN, 
                source_filename VARCHAR, review_status VARCHAR, auditor_notes VARCHAR
            )
        """)
    return conn

conn = get_db_connection()

# --- STREAMLIT SESSION STATE MEMORY ---
# Keep track of which files were processed in the CURRENT active upload batch
if "current_batch_files" not in st.session_state:
    st.session_state.current_batch_files = []

# --- SIDEBAR: DYNAMIC FILE UPLOADER ---
st.sidebar.header("📥 Upload New Invoices")
uploaded_files = st.sidebar.file_uploader(
    "Drag and drop vendor PDFs here", 
    type=["pdf"], 
    accept_multiple_files=True,
    key="file_uploader_widget"
)

if uploaded_files:
    if st.sidebar.button("🚀 Process Uploaded Files", width='stretch'):
        os.makedirs(upload_dir, exist_ok=True)
        
        # CLEAR previous session history so the view refreshes to blank for this new run
        new_batch_list = []
        
        for uploaded_file in uploaded_files:
            target_path = os.path.join(upload_dir, uploaded_file.name)
            with open(target_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            st.sidebar.info(f"Analyzing {uploaded_file.name}...")
            
            try:
                parsed_doc = extract_text_from_pdf(target_path)
                extracted_json = extract_structured_data_from_text(parsed_doc["raw_content"])
                
                if extracted_json and extracted_json.get("line_items"):
                    invoice_df = process_extracted_invoice_to_table(extracted_json)
                    invoice_df = invoice_df.with_columns([
                        pl.lit(uploaded_file.name).alias("source_filename"),
                        pl.lit("Pending Review").alias("review_status"),
                        pl.lit("").alias("auditor_notes")
                    ])
                    
                    # Deduplicate: Remove previous logs of this file from the DB before re-inserting
                    conn.execute("DELETE FROM invoice_ledger WHERE source_filename = ?", (uploaded_file.name,))
                    
                    # Append rows directly to the database
                    conn.execute("INSERT INTO invoice_ledger SELECT * FROM invoice_df")
                    new_batch_list.append(uploaded_file.name)
                    st.sidebar.success(f"✅ Ingested: {uploaded_file.name}")
                else:
                    st.sidebar.error(f"❌ Extraction error on: {uploaded_file.name}")
            except Exception as e:
                st.sidebar.error(f"⚠️ Pipeline fault: {str(e)}")
        
        # Commit the names of only the freshly processed files to the view state memory
        st.session_state.current_batch_files = new_batch_list
        st.rerun()


# --- FETCH DATA SCOPED TO CURRENT ACTIVE UPLOADS ---
if st.session_state.current_batch_files:
    # SQL query filtered tightly to only display files from the current upload action
    placeholders = ",".join(["?"] * len(st.session_state.current_batch_files))
    query_df = conn.execute(
        f"SELECT * FROM invoice_ledger WHERE source_filename IN ({placeholders})", 
        st.session_state.current_batch_files
    ).pl()
else:
    # Empty schema fallback if no upload action has occurred yet in this session
    query_df = pl.DataFrame()


# --- ANALYTICAL KPI METRIC CARDS ---
if not query_df.is_empty():
    total_invoices = query_df.select("invoice_id").n_unique()
    total_items = query_df.height
    active_anomalies = query_df.filter(
        (pl.col("calculation_anomaly") == True) & (pl.col("review_status") == "Pending Review")
    )
    anomaly_invoice_count = active_anomalies.select("invoice_id").n_unique() if not active_anomalies.is_empty() else 0
else:
    total_invoices, total_items, anomaly_invoice_count = 0, 0, 0
    active_anomalies = pl.DataFrame()

col1, col2, col3 = st.columns(3)
col1.metric("Total Invoices Extracted", f"{total_invoices} Bills")
col2.metric("Total Line Items Audited", f"{total_items} Items")
col3.metric("Unresolved Audit Anomalies", f"{anomaly_invoice_count} Flags", 
            delta=f"{anomaly_invoice_count} Active" if anomaly_invoice_count > 0 else "Clear 🎉", 
            delta_color="inverse" if anomaly_invoice_count > 0 else "normal")


# --- DATA VIEW DISPLAY LOGIC ---
st.markdown("### 📋 Current Batch Processing Workspace")

if not query_df.is_empty():
    st.dataframe(query_df.to_pandas(), width='stretch', hide_index=True)
    
    # --- HUMAN-IN-THE-LOOP SIDEBAR CONTROLLER ---
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Audit Exception Queue")

    if anomaly_invoice_count > 0:
        unresolved_invoice_ids = active_anomalies.select("invoice_id").to_series().unique().to_list()
        selected_invoice = st.sidebar.selectbox("Select Flagged Invoice to Reconcile:", unresolved_invoice_ids)
        
        invoice_rows = query_df.filter(pl.col("invoice_id") == selected_invoice)
        vendor = invoice_rows["vendor_name"][0]
        
        st.sidebar.error(f"**Vendor:** {vendor}\n\nInvoice contains arithmetic discrepancies.")
        auditor_notes = st.sidebar.text_input("Auditor Override Justification Notes:", "Approved by procurement.")
        
        if st.sidebar.button("✍️ Clear Anomaly & Force Approve Payment", width='stretch'):
            conn.execute("""
                UPDATE invoice_ledger 
                SET review_status = 'Approved via Override',
                    auditor_notes = ? 
                WHERE invoice_id = ?
            """, (auditor_notes, selected_invoice))
            st.sidebar.success(f"Invoice {selected_invoice} updated!")
            st.rerun()
    else:
        st.sidebar.success("🎉 Current batch is completely clear! Zero audit exceptions remain.")
else:
    st.info("The active workspace workspace is currently empty. Drop fresh vendor invoice PDFs into the sidebar uploader above to trigger the high-speed extraction engine!")

conn.close()
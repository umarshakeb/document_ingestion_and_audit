import os
import json
import polars as pl
from parser import extract_text_from_pdf
from agent import extract_structured_data_from_text
from pipeline import process_extracted_invoice_to_table, save_dataframe_outputs

def run_batch_ingestion_pipeline():
    """
    Scans the local source intake directory, orchestrates raw extraction loops 
    via agent schemas, and compiles structured analytical data matrices.
    """
    raw_dir = os.path.join("data", "raw_synthetic")
    
    if not os.path.exists(raw_dir):
        print(f"[CRITICAL] Intake directory paths missing: {raw_dir}. Please run generator first.")
        return

    # Gather all available PDF invoice assets
    pdf_files = [f for f in os.listdir(raw_dir) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print("[WARNING] Zero matching raw PDF files located inside data directory maps.")
        return
        
    print(f"[INITIATING] Discovered {len(pdf_files)} local document assets for agent processing loop...")
    
    # Storage container array to append our parsed polars data matrices
    master_frames_list = []
    
    for idx, filename in enumerate(pdf_files, start=1):
        file_path = os.path.join(raw_dir, filename)
        base_name = os.path.splitext(filename)[0]
        
        print(f"\n==================================================")
        print(f" PROCESSING FILE {idx}/{len(pdf_files)}: {filename}")
        print(f"==================================================")
        
        # 1. Structural Text Extraction
        print("[STEP 1] Extraction layer parsing text layouts...")
        parsed_doc = extract_text_from_pdf(file_path)
        
        # 2. Local LLM Partition Processing Engine
        print("[STEP 2] Orchestrating Dual-Partition LLM mapping agents...")
        extracted_json = extract_structured_data_from_text(parsed_doc["raw_content"])
        
        # Verify valid dictionaries returned before hitting analytical step rows
        if not extracted_json or not extracted_json.get("line_items"):
            print(f"[SKIP ERROR] Extraction mapping failed or cut empty for item: {filename}")
            continue
            
        # 3. Transpile into clean DataFrames via Polars Pipeline 
        print("[STEP 3] Cleaning, casting, and running mathematical anomaly rules via Polars...")
        invoice_df = process_extracted_invoice_to_table(extracted_json)
        
        if not invoice_df.is_empty():
            # Tag the current rows with their source asset file coordinates
            invoice_df = invoice_df.with_columns(pl.lit(filename).alias("source_filename"))
            master_frames_list.append(invoice_df)
            print("[SUCCESS] Core structured row entities mapped correctly.")
            
    # --- CONSOLIDATE MASTER TABLE ---
    if master_frames_list:
        print("\n==================================================")
        print(" CONSOLIDATING BATCH ANALYTICAL WAREHOUSE...")
        print("==================================================")
        
        # Vectorized stack allocation across our frames list
        master_warehouse_df = pl.concat(master_frames_list)
        
        # Export out comprehensive files containing all 10 unified invoice parameters
        save_dataframe_outputs(master_warehouse_df, "unified_enterprise_invoice_lake")
        
        print("\n--- Summary Structural Matrix Preview ---")
        print(master_warehouse_df.select([
            "invoice_id", "vendor_name", "item_code", "verified_total", "calculation_anomaly"
        ]).head(15))
        
        # Print anomaly metrics to see if our rules caught the generator's trick bills
        anomalies_detected = master_warehouse_df.filter(pl.col("calculation_anomaly") == True)
        print(f"\n[AUDIT REPORT] Data Pipeline intercepted {len(anomalies_detected)} line-item billing mismatch anomalies inside the file layers.")
    else:
        print("[CRITICAL ERROR] Zero document frames processed into final stack matrices safely.")

if __name__ == "__main__":
    run_batch_ingestion_pipeline()
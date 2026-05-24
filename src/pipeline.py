import polars as pl
import json
import os

def process_extracted_invoice_to_table(extracted_json: dict) -> pl.DataFrame:
    """
    Takes raw dictionary output from our extraction agent, normalizes 
    nested line-item structures, cleans formatting anomalies, and returns 
    a highly optimized Polars DataFrame.
    """
    if not extracted_json or "line_items" not in extracted_json:
        print("[WARNING] Empty payload received or line items missing.")
        return pl.DataFrame()

    # Extract base metadata fields
    invoice_id = extracted_json.get("invoice_id", "UNKNOWN")
    vendor_name = extracted_json.get("vendor_name", "UNKNOWN")
    invoice_date = extracted_json.get("invoice_date", "UNKNOWN")
    po_ref = extracted_json.get("po_reference", "UNKNOWN")
    
    line_items_list = extracted_json["line_items"]
    
    # Flatten the JSON list into a flat list of dictionaries for tabular loading
    flattened_rows = []
    for item in line_items_list:
        row = {
            "invoice_id": invoice_id,
            "vendor_name": vendor_name,
            "invoice_date": invoice_date,
            "po_reference": po_ref,
            "item_code": item.get("item_code", "").strip(),
            "description": item.get("description", ""),
            "quantity": int(item.get("quantity", 0)),
            "unit_price": float(item.get("unit_price", 0.0)),
            "extracted_total": float(item.get("total_amount", 0.0))
        }
        flattened_rows.append(row)
        
    # Convert instantly to a Polars DataFrame
    df = pl.DataFrame(flattened_rows)
    
    # --- Polars Optimization & Data Sanitization ---
    # 1. Cast data types clearly and compute verified totals programmatically 
    df = df.with_columns([
        pl.col("invoice_date").str.to_date(format="%Y-%m-%d", strict=False),
        (pl.col("quantity") * pl.col("unit_price")).round(2).alias("verified_total")
    ])
    
    # 2. Add an anomaly flag if the LLM's extracted calculation disagrees with programmatic math
    df = df.with_columns(
        (pl.col("extracted_total") != pl.col("verified_total")).alias("calculation_anomaly")
    )
    
    return df

def save_dataframe_outputs(df: pl.DataFrame, output_base_name: str):
    """Saves structured data arrays out to enterprise formats safely."""
    output_dir = os.path.join("data", "processed_output")
    os.makedirs(output_dir, exist_ok=True)
    
    if df.is_empty():
        return
        
    csv_path = os.path.join(output_dir, f"{output_base_name}.csv")
    parquet_path = os.path.join(output_dir, f"{output_base_name}.parquet")
    
    # Export data matrices
    df.write_csv(csv_path)
    df.write_parquet(parquet_path)
    print(f"[SUCCESS] Saved clean tables to:\n -> {csv_path}\n -> {parquet_path}")

if __name__ == "__main__":
    # Mock runtime verification step 
    mock_json = {
        "invoice_id": "INV-2026-TEST",
        "vendor_name": "ACME LOGISTICS CORPS",
        "invoice_date": "2026-05-24",
        "po_reference": "PO-99999",
        "line_items": [
            {"item_code": "TYR-444-X12 ", "description": "HD Truck Tires", "quantity": 10, "unit_price": 150.0, "total_amount": 1500.0},
            {"item_code": "FST-101-NUT", "description": "Locking Bolts", "quantity": 5, "unit_price": 20.0, "total_amount": 95.0} # Intentionally wrong total
        ],
        "declared_subtotal": 1595.0
    }
    
    print("Testing Polars Pipeline transformations...")
    result_df = process_extracted_invoice_to_table(mock_json)
    print("\n--- Processed Polars Matrix View ---")
    print(result_df)
    
    save_dataframe_outputs(result_df, "test_pipeline_run")
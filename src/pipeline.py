import polars as pl
import json
import os


def process_extracted_invoice_to_table(extracted_json: dict) -> pl.DataFrame:
    """
    Transforms raw JSON extraction envelopes into structured Polars rows,
    calculates full line-item matrix aggregates, and cross-references them
    against the invoice's declared subtotal to detect corporate billing anomalies.
    """
    line_items = extracted_json.get("line_items", [])
    if not line_items:
        return pl.DataFrame()
        
    # 1. Parse the extracted dictionary metadata keys
    invoice_id = extracted_json.get("invoice_id", "UNKNOWN")
    vendor_name = extracted_json.get("vendor_name", "UNKNOWN")
    invoice_date = extracted_json.get("invoice_date", None)
    po_reference = extracted_json.get("po_reference", "UNKNOWN")
    declared_subtotal = float(extracted_json.get("declared_subtotal", 0.0))
    
    # 2. Convert raw line item lists into a Polars DataFrame
    df = pl.DataFrame(line_items)
    
    # Ensure standard schema column datatypes are enforced cleanly
    df = df.with_columns([
        pl.col("quantity").cast(pl.Int64, strict=False).fill_null(0),
        pl.col("unit_price").cast(pl.Float64, strict=False).fill_null(0.0),
        pl.col("total_amount").cast(pl.Float64, strict=False).fill_null(0.0)
    ])
    
    # 3. Perform granular data engineering validations using Polars expressions
    # Calculate what the true line total SHOULD be
    df = df.with_columns(
        (pl.col("quantity") * pl.col("unit_price")).round(2).alias("calculated_line_total")
    )
    
    # Calculate the grand sum total of all lines processed in this single document invoice container
    calculated_subtotal_sum = df.select(pl.col("total_amount").sum()).item()
    calculated_subtotal_sum = round(float(calculated_subtotal_sum), 2)
    
    # 4. Apply Multi-Layered Audit Anomaly Flags
    # Trigger an alert if:
    #   A) Any single line item's arithmetic is wrong OR
    #   B) The sum of all items doesn't match the stated subtotal on the document invoice header
    df = df.with_columns([
        pl.lit(invoice_id).alias("invoice_id"),
        pl.lit(vendor_name).alias("vendor_name"),
        pl.lit(invoice_date).alias("invoice_date"),
        pl.lit(po_reference).alias("po_reference"),
        pl.lit(declared_subtotal).alias("extracted_subtotal"),
        pl.lit(calculated_subtotal_sum).alias("verified_subtotal_sum"),
        
        # Core conditional anomaly flag assignment expression
        pl.when(
            (pl.col("total_amount") != pl.col("calculated_line_total")) | 
            (pl.lit(declared_subtotal) != pl.lit(calculated_subtotal_sum))
        )
        .then(True)
        .else_(False)
        .alias("calculation_anomaly")
    ])
    
    # Rearrange column positioning sequence for dashboard layout rendering
    final_column_order = [
        "invoice_id", "vendor_name", "invoice_date", "po_reference", 
        "item_code", "description", "quantity", "unit_price", "total_amount", 
        "extracted_subtotal", "verified_subtotal_sum", "calculation_anomaly"
    ]
    
    # Dynamic structural selection safely checking for column existence variations
    existing_columns = [col for col in final_column_order if col in df.columns]
    return df.select(existing_columns)

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
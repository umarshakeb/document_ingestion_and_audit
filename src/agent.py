import os
import json
import re
from groq import Groq

def clean_and_parse_llm_json(raw_text: str) -> dict:
    """Extracts and parses JSON structures safely from text envelopes."""
    text = raw_text.replace("```json", "").replace("```", "").strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    
    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        return {}
        
    try:
        return json.loads(text[start_idx:end_idx + 1])
    except Exception:
        return {}

def extract_structured_data_from_text(raw_text: str) -> dict:
    """
    Partitions the document text and passes it to Groq API for 
    blazing fast, sub-2-second cloud extraction.
    """
    # Initialize the Groq client. It automatically fetches the key 
    # from the GROQ_API_KEY environment variable.
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY environment variable not found!")
        return {}
        
    client = Groq(api_key=api_key)
    
    # We use Llama 3.3 70B on Groq for state-of-the-art accuracy
    target_model = "llama-3.3-70b-versatile"
    
    metadata_prompt = (
        "You are an expert data extractor. Extract the general invoice details from the text.\n"
        "Look closely at the bottom of tables or text sections to find the explicitly stated Subtotal or Total amount.\n"
        "Respond with ONLY a JSON object matching this sample structure:\n"
        "{\n"
        '  "invoice_id": "STRING",\n'
        '  "vendor_name": "STRING",\n'
        '  "invoice_date": "YYYY-MM-DD",\n'
        '  "po_reference": "STRING",\n'
        '  "declared_subtotal": 0.0\n'
        "}"
    )
    
    line_items_prompt = (
        "You are an expert data extractor. Extract all line items listed inside tables within the text.\n"
        "Respond with ONLY a JSON object matching this sample structure:\n"
        "{\n"
        '  "line_items": [\n'
        "    {\n"
        '      "item_code": "STRING",\n'
        '      "description": "STRING",\n'
        '      "quantity": 0,\n'
        '      "unit_price": 0.0,\n'
        '      "total_amount": 0.0\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    try:
        # Partition 1: Metadata
        meta_res = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": metadata_prompt},
                {"role": "user", "content": f"Text:\n{raw_text}"}
            ],
            temperature=0.0
        )
        metadata_dict = clean_and_parse_llm_json(meta_res.choices[0].message.content)
        
        # Partition 2: Tables
        items_res = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": line_items_prompt},
                {"role": "user", "content": f"Text:\n{raw_text}"}
            ],
            temperature=0.0
        )
        items_dict = clean_and_parse_llm_json(items_res.choices[0].message.content)
        
        # Consolidate envelopes
        final_payload = {
            "invoice_id": metadata_dict.get("invoice_id", "UNKNOWN"),
            "vendor_name": metadata_dict.get("vendor_name", "UNKNOWN"),
            "invoice_date": metadata_dict.get("invoice_date", "UNKNOWN"),
            "po_reference": metadata_dict.get("po_reference", "UNKNOWN"),
            "line_items": items_dict.get("line_items", []),
            "declared_subtotal": metadata_dict.get("declared_subtotal", 0.0)
        }
        return final_payload
        
    except Exception as e:
        print(f"[ERROR] Groq API partition execution failure: {str(e)}")
        return {}
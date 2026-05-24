import os
from pypdf import PdfReader
import io

def extract_text_from_pdf(file_target) -> dict:
    """
    Extracts raw text payload matrix from a file path or an active in-memory binary stream.
    """
    # If it's a file path string, open it; if it's already an uploaded file buffer object, read it directly
    if isinstance(file_target, str):
        with open(file_target, "rb") as f:
            reader = pypdf.PdfReader(f)
            text_content = "".join([page.extract_text() for page in reader.pages])
    else:
        # Streamlit upload streams act like raw byte payloads natively
        pdf_stream = io.BytesIO(file_target.read())
        reader = pypdf.PdfReader(pdf_stream)
        text_content = "".join([page.extract_text() for page in reader.pages])
        
    return {"raw_content": text_content}

if __name__ == "__main__":
    # Test our parser locally against invoice_mock_01.pdf
    sample_path = os.path.join("data", "raw_synthetic", "invoice_mock_01.pdf")
    
    if os.path.exists(sample_path):
        print(f"Testing Parser Engine on: {sample_path}\n")
        parsed_data = extract_text_from_pdf(sample_path)
        
        print(f"--- File Metadata ---")
        print(f"Filename: {parsed_data['file_name']}")
        print(f"Pages: {parsed_data['total_pages']}")
        print(f"\n--- Extracted Content Snippet ---")
        # Print the first 400 characters to verify layout preservation
        print(parsed_data['raw_content'][:400])
        print("\n[Parser Test Successful]")
    else:
        print(f"Could not find sample invoice file at {sample_path}. Please run src/generator.py first.")
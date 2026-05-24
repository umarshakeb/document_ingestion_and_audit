import os
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    """
    Reads a PDF file and extracts raw text string contents along with basic metadata.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Target PDF file not found at: {pdf_path}")
        
    reader = PdfReader(pdf_path)
    extracted_pages = []
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            extracted_pages.append(text)
            
    # Combine pages into a single payload structural string block
    full_text = "\n--- PAGE BREAK ---\n".join(extracted_pages)
    
    return {
        "file_name": os.path.basename(pdf_path),
        "file_path": pdf_path,
        "total_pages": len(reader.pages),
        "raw_content": full_text
    }

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
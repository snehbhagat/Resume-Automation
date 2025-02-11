import pdfplumber
import pytesseract
import re  # ✅ FIXED: Import Regular Expressions
import os
from pdf2image import convert_from_path

# Function to extract text using OCR (for scanned PDFs)
def ocr_extract_text(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
    return text

# Function to extract text from a PDF (with OCR fallback)
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n" if page.extract_text() else ""

    # If no text was extracted, try OCR
    if not text.strip():
        print(f"🔍 Running OCR on {pdf_path} (Scanned PDF detected)")
        text = ocr_extract_text(pdf_path)

    return text

# Function to extract Name, Email, Phone
def extract_details(text):
    email_pattern = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+"
    phone_pattern = r"\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}"

    email = re.findall(email_pattern, text)  # ✅ FIXED: re is now imported
    phone = re.findall(phone_pattern, text)

    name_lines = text.split("\n")[:5]
    name = "N/A"
    for line in name_lines:
        if len(line.split()) >= 2:
            name = line.strip()
            break

    return {"Name": name, "Email": email[0] if email else "N/A", "Phone": phone[0] if phone else "N/A"}

# Function to extract details from all PDFs in a folder
def extract_details_from_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"❌ Folder '{folder_path}' does not exist!")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]

    if not pdf_files:
        print("❌ No PDF files found in the folder!")
        return

    print(f"📂 Found {len(pdf_files)} resumes. Extracting details...")

    extracted_data = []
    for file in pdf_files:
        file_path = os.path.join(folder_path, file)
        pdf_text = extract_text_from_pdf(file_path)
        details = extract_details(pdf_text)
        extracted_data.append(details)

    print("✅ Extraction complete!")
    return extracted_data

# Extract details from all resumes in 'Resume' folder
resume_data = extract_details_from_folder("./Resume")

# Print extracted data
if resume_data:
    for i, data in enumerate(resume_data, 1):
        print(f"\n📄 Resume {i}:")
        print(data)

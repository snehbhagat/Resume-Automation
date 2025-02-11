import gspread
from google.oauth2.service_account import Credentials
import os  # Import for handling file operations

# Define API Scope and Credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "credential_sheet.json"  # Ensure this file exists in your project folder

# Authenticate with Google Sheets API
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Open your Google Sheet by its ID
SHEET_ID = "1Mx674i2GPSTl2LK280ou4yyfgBHcmg42bV76YJ6iYTQ"  # Replace with your actual Sheet ID
sheet = client.open_by_key(SHEET_ID).sheet1  # Select first sheet

print("✅ Google Sheets API authentication successful!")

# Function to add headers if missing
def add_headers():
    existing_headers = sheet.row_values(1)  # Get first row
    required_headers = ["Name", "Email Address", "Phone No"]

    if existing_headers != required_headers:
        sheet.insert_row(required_headers, index=1)
        print("✅ Headers added to Google Sheets!")
    else:
        print("✅ Headers already exist.")

# Function to check if email already exists (to prevent duplicates)
def check_duplicate(email):
    existing_emails = sheet.col_values(2)  # Get all emails from column 2
    return email in existing_emails

# Function to save extracted data to Google Sheets
def save_to_sheet(data):
    add_headers()  # Ensure headers exist before saving

    if check_duplicate(data["Email"]):
        print(f"⚠️ Duplicate entry found for {data['Email']}! Skipping...")
    else:
        sheet.append_row([data["Name"], data["Email"], data["Phone"]])
        print(f"✅ Data saved: {data}")

# Ensure extract_text_from_pdf and extract_details are defined
def extract_text_from_pdf(pdf_path):
    import pdfplumber
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n" if page.extract_text() else ""
    return text

def extract_details(text):
    import re
    email_pattern = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+"
    phone_pattern = r"\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}"

    email = re.findall(email_pattern, text)
    phone = re.findall(phone_pattern, text)

    name_lines = text.split("\n")[:5]
    name = "N/A"
    for line in name_lines:
        if len(line.split()) >= 2:
            name = line.strip()
            break

    return {"Name": name, "Email": email[0] if email else "N/A", "Phone": phone[0] if phone else "N/A"}

# Function to extract details from resumes and save to Google Sheets
def extract_and_store_details(folder_path):
    if not os.path.exists(folder_path):
        print(f"❌ Folder '{folder_path}' does not exist!")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]

    if not pdf_files:
        print("❌ No PDF files found in the folder!")
        return

    print(f"📂 Found {len(pdf_files)} resumes. Extracting and saving details...")

    for file in pdf_files:
        file_path = os.path.join(folder_path, file)
        pdf_text = extract_text_from_pdf(file_path)
        details = extract_details(pdf_text)
        
        # Save extracted details to Google Sheets
        save_to_sheet(details)

    print("✅ All details extracted and saved to Google Sheets!")

# Run the pipeline
extract_and_store_details("./Resume")  # Folder containing all resumes

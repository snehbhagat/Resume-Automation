import os
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
import re
from io import BytesIO
import pdfplumber
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ✅ Step 1: Authenticate Google Drive & Google Sheets APIs
SCOPES_DRIVE = ["https://www.googleapis.com/auth/drive"]
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]

# Load credentials from environment variables
DRIVE_CREDENTIALS = os.getenv("DRIVE_CREDENTIALS", "credential.json")
SHEETS_CREDENTIALS = os.getenv("SHEETS_CREDENTIALS", "credential_sheet.json")
SHEET_ID = os.getenv("SHEET_ID")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

# Authenticate with Google Drive API
drive_creds = Credentials.from_service_account_file(DRIVE_CREDENTIALS, scopes=SCOPES_DRIVE)
drive_service = build("drive", "v3", credentials=drive_creds)

# Authenticate with Google Sheets API
sheets_creds = Credentials.from_service_account_file(SHEETS_CREDENTIALS, scopes=SCOPES_SHEETS)
client = gspread.authorize(sheets_creds)

# Open Google Sheet
sheet = client.open_by_key(SHEET_ID).sheet1  # First sheet

# ✅ Step 2: Ensure Headers Exist in Google Sheets
def add_headers():
    required_headers = ["Name", "Email Address", "Phone No", "Google Drive Link"]
    existing_headers = sheet.row_values(1)
    
    if existing_headers != required_headers:
        sheet.insert_row(required_headers, index=1)
        print("✅ Headers added to Google Sheets!")

# ✅ Step 3: Check if a File Exists in Google Drive
def file_exists(file_name, folder_id):
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, webViewLink)").execute()
    files = results.get("files", [])
    return files[0] if files else None  # Return file details if found

# ✅ Step 4: Upload a Resume to Google Drive (if not already uploaded)
def upload_to_drive(file_path, folder_id):
    file_name = os.path.basename(file_path)

    existing_file = file_exists(file_name, folder_id)
    if existing_file:
        print(f"⚠️ Skipping {file_name}, already in Google Drive.")
        return existing_file["id"], existing_file["webViewLink"]

    file_metadata = {"name": file_name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype="application/pdf")

    uploaded_file = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id, webViewLink"
    ).execute()

    print(f"✅ Uploaded {file_name} to Google Drive.")
    return uploaded_file["id"], uploaded_file["webViewLink"]

# ✅ Step 5: Upload All Resumes from Local Folder to Google Drive
def upload_all_resumes(local_folder, drive_folder_id):
    if not os.path.exists(local_folder):
        print(f"❌ Folder '{local_folder}' does not exist!")
        return []

    pdf_files = [f for f in os.listdir(local_folder) if f.endswith(".pdf")]

    if not pdf_files:
        print("❌ No PDF resumes found in the folder!")
        return []

    print(f"📂 Found {len(pdf_files)} resumes. Uploading to Google Drive...")

    drive_files = []
    for file in pdf_files:
        file_path = os.path.join(local_folder, file)
        file_id, file_link = upload_to_drive(file_path, drive_folder_id)
        drive_files.append({"id": file_id, "name": file, "link": file_link})

    print("✅ All resumes uploaded successfully!")
    return drive_files  # Return uploaded file info

# ✅ Step 6: Extract Text from a Google Drive PDF
def extract_text_from_drive(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    file_stream = BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    
    done = False
    while not done:
        _, done = downloader.next_chunk()

    text = ""
    file_stream.seek(0)
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n" if page.extract_text() else ""

    return text

# ✅ Step 7: Extract Candidate Details (Name, Email, Phone)
def extract_details(text):
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

# ✅ Step 8: Check for Duplicate Email in Google Sheets
def check_duplicate(email):
    existing_emails = sheet.col_values(2)
    return email in existing_emails

# ✅ Step 9: Save Extracted Details to Google Sheets
def save_to_sheet(data):
    add_headers()

    if check_duplicate(data["Email"]):
        print(f"⚠️ Duplicate entry found for {data['Email']}! Skipping...")
    else:
        sheet.append_row([data["Name"], data["Email"], data["Phone"], data["Drive Link"]])
        print(f"✅ Data saved: {data}")

# ✅ Step 10: Process All Resumes from Google Drive
def process_drive_resumes(uploaded_files):
    if not uploaded_files:
        print("❌ No resumes available in Google Drive!")
        return

    print(f"📂 Extracting details from {len(uploaded_files)} resumes...")

    for file in uploaded_files:
        file_text = extract_text_from_drive(file["id"])
        details = extract_details(file_text)
        details["Drive Link"] = file["link"]  # Add Drive link
        save_to_sheet(details)

    print("✅ All resume details extracted and saved to Google Sheets!")

# ✅ Step 11: Run the Complete Pipeline
LOCAL_FOLDER = "./Resume"  # Folder where resumes are stored locally

if not SHEET_ID or not DRIVE_FOLDER_ID:
    raise ValueError("Missing required environment variables: SHEET_ID or DRIVE_FOLDER_ID")

uploaded_files = upload_all_resumes(LOCAL_FOLDER, DRIVE_FOLDER_ID)  # Upload resumes to Drive
process_drive_resumes(uploaded_files)  # Extract details & save to Sheets

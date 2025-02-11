import os
import re
import imaplib
import email
import gspread
import pdfplumber
from io import BytesIO
from email.header import decode_header
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials

# ✅ Gmail Credentials (Use App Password)
EMAIL_USER = "snehbhagat12@gmail.com"
EMAIL_PASSWORD = "obzh dxyu xfgq myiy"  # Use Google App Password
IMAP_SERVER = "imap.gmail.com"

# ✅ Google API Credentials
DRIVE_CREDENTIALS = "credential.json"
SHEETS_CREDENTIALS = "credential_sheet.json"
SHEET_ID = "1Mx674i2GPSTl2LK280ou4yyfgBHcmg42bV76YJ6iYTQ"  # Replace with actual Sheet ID
DRIVE_FOLDER_ID = "1UYzFDDRaS__DucpWXU4Ul2r2rpbz0AH2"  # Google Drive Folder ID
LOCAL_FOLDER = "./Resume"  # Local storage for resumes

# ✅ Authenticate Google Drive & Google Sheets APIs
SCOPES_DRIVE = ["https://www.googleapis.com/auth/drive"]
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]

drive_creds = Credentials.from_service_account_file(DRIVE_CREDENTIALS, scopes=SCOPES_DRIVE)
drive_service = build("drive", "v3", credentials=drive_creds)

sheets_creds = Credentials.from_service_account_file(SHEETS_CREDENTIALS, scopes=SCOPES_SHEETS)
client = gspread.authorize(sheets_creds)
sheet = client.open_by_key(SHEET_ID).sheet1  # First sheet

# =============================================================
# ✅ STEP 1: FETCH JOB EMAILS WITH RESUME ATTACHMENTS
# =============================================================

def connect_to_email():
    """Connect to Gmail using IMAP."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    mail.select("inbox")  # Select the inbox
    return mail

def search_emails_with_attachments():
    """Find emails with job-related subjects containing resume attachments."""
    mail = connect_to_email()
    
    # 📩 Search for job-related emails
    search_query = '(OR SUBJECT "Job Application" SUBJECT "Application for" SUBJECT "Resume" SUBJECT "CV" SUBJECT "Candidate Application")'
    result, messages = mail.search(None, search_query)

    if result != "OK":
        print("⚠️ Error searching emails.")
        mail.logout()
        return []

    email_ids = messages[0].split()
    mail.logout()
    return email_ids[-10:]  # Return last 10 emails

def download_resumes():
    """Download PDF and DOCX resumes from job-related emails."""
    mail = connect_to_email()
    email_ids = search_emails_with_attachments()

    if not email_ids:
        print("⚠️ No job-related emails with attachments found.")
        return

    os.makedirs(LOCAL_FOLDER, exist_ok=True)

    for email_id in email_ids:
        res, msg_data = mail.fetch(email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                subject = subject.decode(encoding if encoding else "utf-8") if isinstance(subject, bytes) else subject
                print(f"📩 Processing email: {subject}")

                for part in msg.walk():
                    if part.get_content_disposition() and part.get_content_disposition() == "attachment":
                        filename = part.get_filename()
                        filename, encoding = decode_header(filename)[0]
                        filename = filename.decode(encoding if encoding else "utf-8") if isinstance(filename, bytes) else filename

                        if filename.endswith((".pdf", ".docx")):
                            filepath = os.path.join(LOCAL_FOLDER, filename)
                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                            print(f"✅ Resume downloaded: {filename}")

    mail.logout()

# =============================================================
# ✅ STEP 2: UPLOAD TO GOOGLE DRIVE
# =============================================================

def upload_to_drive(file_path):
    """Upload resume to Google Drive and return file ID and link."""
    file_name = os.path.basename(file_path)
    file_metadata = {"name": file_name, "parents": [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(file_path, mimetype="application/pdf")

    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    print(f"✅ Uploaded {file_name} to Google Drive.")
    return uploaded_file["id"], uploaded_file["webViewLink"]

# =============================================================
# ✅ STEP 3: EXTRACT TEXT FROM RESUMES
# =============================================================

def extract_text_from_drive(file_id):
    """Extract text from a PDF resume stored in Google Drive."""
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

# =============================================================
# ✅ STEP 4: EXTRACT CANDIDATE DETAILS
# =============================================================

def extract_details(text):
    """Extract Name, Email, and Phone from resume text."""
    email_pattern = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+"
    phone_pattern = r"\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
    
    email = re.findall(email_pattern, text)
    phone = re.findall(phone_pattern, text)

    name = "N/A"
    for line in text.split("\n")[:5]:  # Check top lines for a probable name
        if len(line.split()) >= 2:
            name = line.strip()
            break

    return {"Name": name, "Email": email[0] if email else "N/A", "Phone": phone[0] if phone else "N/A"}

# =============================================================
# ✅ STEP 5: SAVE DATA TO GOOGLE SHEETS
# =============================================================

def save_to_sheet(data):
    """Save extracted candidate details to Google Sheets."""
    headers = ["Name", "Email Address", "Phone No", "Google Drive Link"]
    if sheet.row_values(1) != headers:
        sheet.insert_row(headers, index=1)

    existing_emails = sheet.col_values(2)
    if data["Email"] in existing_emails:
        print(f"⚠️ Duplicate entry found for {data['Email']}! Skipping...")
    else:
        sheet.append_row([data["Name"], data["Email"], data["Phone"], data["Drive Link"]])
        print(f"✅ Data saved: {data}")

# =============================================================
# ✅ MAIN EXECUTION: RUN PIPELINE
# =============================================================

def process_resumes():
    """Complete pipeline: Fetch emails → Download resumes → Upload to Drive → Extract details → Save to Sheets."""
    
    print("📩 Step 1: Fetching resumes from emails...")
    download_resumes()
    
    pdf_files = [f for f in os.listdir(LOCAL_FOLDER) if f.endswith(".pdf")]
    if not pdf_files:
        print("❌ No PDF resumes found in the folder!")
        return

    for file in pdf_files:
        file_path = os.path.join(LOCAL_FOLDER, file)
        file_id, file_link = upload_to_drive(file_path)
        text = extract_text_from_drive(file_id)
        details = extract_details(text)
        details["Drive Link"] = file_link
        save_to_sheet(details)

    print("✅ Process completed!")

# ✅ Run the script
process_resumes()

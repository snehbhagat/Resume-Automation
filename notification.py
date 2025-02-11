import gspread
import smtplib
import pdfplumber
import re
import os
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials

# ✅ Step 1: Set Up Google Sheets API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "credential_sheet.json"  # Ensure this file exists

# Authenticate Google Sheets API
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Open your Google Sheet
SHEET_ID = "1Mx674i2GPSTl2LK280ou4yyfgBHcmg42bV76YJ6iYTQ"  # Replace with actual Sheet ID
sheet = client.open_by_key(SHEET_ID).sheet1

print("✅ Google Sheets API authentication successful!")

# ✅ Step 2: Email Notification Setup
HR_EMAIL = "snehkumar.bhagat2022@vitstudent.ac.in"  # HR Email
SENDER_EMAIL = "snehbhagat12@gmail.com"  # Your Gmail
SENDER_PASSWORD = "obzh dxyu xfgq myiy"  # App Password from Google (NOT your real password)

# Function to send an email notification
def send_email_notification(applicant):
    subject = f"New Job Application: {applicant['Name']}"
    body = f"""
    A new job application has been received.
    
    📌 **Applicant Details:**
    - **Name:** {applicant['Name']}
    - **Email:** {applicant['Email']}
    - **Phone:** {applicant['Phone']}
    
    Please review the application in Google Sheets.
    """

    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = HR_EMAIL

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, HR_EMAIL, msg.as_string())
        print(f"📧 Email notification sent to HR for {applicant['Name']}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

# ✅ Step 3: Function to Check & Add Headers in Google Sheets
def add_headers():
    existing_headers = sheet.row_values(1)
    required_headers = ["Name", "Email Address", "Phone No"]
    if existing_headers != required_headers:
        sheet.insert_row(required_headers, index=1)
        print("✅ Headers added to Google Sheets!")
    else:
        print("✅ Headers already exist.")

# ✅ Step 4: Function to Check for Duplicate Entries
def check_duplicate(email):
    existing_emails = sheet.col_values(2)  # Get all emails from column 2
    return email in existing_emails

# ✅ Step 5: Function to Extract Text from PDFs
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n" if page.extract_text() else ""
    return text

# ✅ Step 6: Function to Extract Name, Email, Phone from Text
def extract_details(text):
    email_pattern = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+"
    phone_pattern = r"\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}"

    email = re.findall(email_pattern, text)
    phone = re.findall(phone_pattern, text)

    # Extracting name: Assuming name is in the first 5 lines
    name_lines = text.split("\n")[:5]
    name = "N/A"
    for line in name_lines:
        if len(line.split()) >= 2:
            name = line.strip()
            break

    return {"Name": name, "Email": email[0] if email else "N/A", "Phone": phone[0] if phone else "N/A"}

# ✅ Step 7: Function to Process Resumes & Store Data
def extract_and_store_details(folder_path):
    if not os.path.exists(folder_path):
        print(f"❌ Folder '{folder_path}' does not exist!")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]

    if not pdf_files:
        print("❌ No PDF files found in the folder!")
        return

    print(f"📂 Found {len(pdf_files)} resumes. Extracting and saving details...")
    add_headers()  # Ensure headers exist

    for file in pdf_files:
        file_path = os.path.join(folder_path, file)
        pdf_text = extract_text_from_pdf(file_path)
        details = extract_details(pdf_text)
        
        # Save extracted details to Google Sheets
        if check_duplicate(details["Email"]):
            print(f"⚠️ Duplicate entry found for {details['Email']}! Skipping...")
        else:
            sheet.append_row([details["Name"], details["Email"], details["Phone"]])
            print(f"✅ Data saved: {details}")

            # Send Email Notification
            send_email_notification(details)

    print("✅ All details extracted and saved to Google Sheets!")

# ✅ Step 8: Run the Pipeline
extract_and_store_details("./Resume")  # Folder containing all resumes

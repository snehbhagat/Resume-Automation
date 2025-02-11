import email
import imaplib
import os
import datetime
import hashlib
from email.header import decode_header
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import re
from io import BytesIO
import pdfplumber
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ResumeProcessor:
    def __init__(self):
        # Configuration from environment variables
        self.LOCAL_FOLDER = os.getenv('LOCAL_FOLDER', 'Resume')
        self.DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')
        self.SHEET_ID = os.getenv('SHEET_ID')
        
        # API Scopes
        self.SCOPES_DRIVE = ["https://www.googleapis.com/auth/drive"]
        self.SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
        
        # Initialize APIs
        self._init_google_apis()
        
        # Create hash storage file if it doesn't exist
        self.hash_file = os.path.join(self.LOCAL_FOLDER, "processed_files.txt")
        if not os.path.exists(self.hash_file):
            with open(self.hash_file, 'w') as f:
                f.write('')

    def _init_google_apis(self):
        """Initialize Google Drive and Sheets APIs"""
        try:
            # Drive API setup
            drive_creds = Credentials.from_service_account_file(
                "credentials.json", 
                scopes=self.SCOPES_DRIVE
            )
            self.drive_service = build("drive", "v3", credentials=drive_creds)
            
            # Sheets API setup
            sheets_creds = Credentials.from_service_account_file(
                "credentials.json", 
                scopes=self.SCOPES_SHEETS
            )
            client = gspread.authorize(sheets_creds)
            self.sheet = client.open_by_key(self.SHEET_ID).sheet1
            
            print("✅ Google APIs initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Google APIs: {str(e)}")
            raise

    def _calculate_file_hash(self, file_content):
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()

    def _is_file_processed(self, file_hash):
        """Check if file hash exists in processed files"""
        with open(self.hash_file, 'r') as f:
            processed_hashes = f.read().splitlines()
        return file_hash in processed_hashes

    def _mark_file_processed(self, file_hash):
        """Add file hash to processed files"""
        with open(self.hash_file, 'a') as f:
            f.write(f"{file_hash}\n")

    def _is_duplicate_in_sheets(self, email):
        """Check if email already exists in Google Sheets"""
        existing_emails = self.sheet.col_values(2)[1:]  # Skip header
        return email in existing_emails

    def fetch_email_attachments(self, email_address, password, search_criteria='(SUBJECT "Job Application")'):
        """Fetch attachments from Gmail"""
        if not os.path.exists(self.LOCAL_FOLDER):
            os.makedirs(self.LOCAL_FOLDER)
        
        saved_files = []
        try:
            print("📧 Connecting to Gmail...")
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_address, password)
            print("✅ Gmail login successful")
            
            mail.select("inbox")
            status, message_numbers = mail.search(None, search_criteria)
            
            if status != 'OK' or not message_numbers[0]:
                print("ℹ️ No matching emails found")
                return saved_files
            
            print(f"📥 Found {len(message_numbers[0].split())} matching emails")
            
            for num in message_numbers[0].split():
                try:
                    _, msg_data = mail.fetch(num, "(RFC822)")
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    subject = decode_header(email_message["subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    
                    sender = email_message.get("from")
                    print(f"\n📨 Processing email from: {sender}")
                    
                    for part in email_message.walk():
                        if part.get_content_maintype() == "multipart" or part.get("Content-Disposition") is None:
                            continue
                        
                        filename = part.get_filename()
                        if filename and filename.lower().endswith('.pdf'):
                            # Get file content and calculate hash
                            content = part.get_payload(decode=True)
                            file_hash = self._calculate_file_hash(content)
                            
                            # Check if file was already processed
                            if self._is_file_processed(file_hash):
                                print(f"ℹ️ Skipping duplicate file: {filename}")
                                continue
                            
                            # Save new file
                            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            new_filename = f"{timestamp}_{filename}"
                            filepath = os.path.join(self.LOCAL_FOLDER, new_filename)
                            
                            with open(filepath, "wb") as f:
                                f.write(content)
                            
                            # Mark file as processed
                            self._mark_file_processed(file_hash)
                            saved_files.append(filepath)
                            print(f"✅ Saved new file: {new_filename}")
                
                except Exception as e:
                    print(f"⚠️ Error processing email: {str(e)}")
                    continue
            
            mail.close()
            mail.logout()
            print(f"✅ Email processing complete. Saved {len(saved_files)} new files")
            
        except Exception as e:
            print(f"❌ Email error: {str(e)}")
            if 'mail' in locals():
                try:
                    mail.close()
                    mail.logout()
                except:
                    pass
        
        return saved_files

    def _file_exists_in_drive(self, file_hash):
        """Check if file exists in Google Drive using custom properties"""
        query = f"'{self.DRIVE_FOLDER_ID}' in parents and trashed=false"
        results = self.drive_service.files().list(
            q=query,
            fields="files(id, name, properties)",
            supportsAllDrives=True
        ).execute()
        
        for file in results.get('files', []):
            if file.get('properties', {}).get('file_hash') == file_hash:
                return file
        return None

    def upload_to_drive(self, file_path):
        """Upload a single file to Google Drive"""
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = self._calculate_file_hash(f.read())
        
        # Check for duplicate in Drive
        existing_file = self._file_exists_in_drive(file_hash)
        if existing_file:
            print(f"ℹ️ File already exists in Drive")
            return existing_file["id"], existing_file.get("webViewLink")
        
        # Prepare file metadata with hash property
        file_name = os.path.basename(file_path)
        file_metadata = {
            "name": file_name,
            "parents": [self.DRIVE_FOLDER_ID],
            "properties": {"file_hash": file_hash}
        }
        
        media = MediaFileUpload(file_path, mimetype="application/pdf")
        uploaded_file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()
        
        print(f"✅ Uploaded new file to Drive: {file_name}")
        return uploaded_file["id"], uploaded_file["webViewLink"]

    def extract_text_from_pdf(self, file_id):
        """Extract text from PDF in Google Drive"""
        request = self.drive_service.files().get_media(fileId=file_id)
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

    def extract_details(self, text):
        """Extract candidate details from text"""
        email_pattern = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+"
        phone_pattern = r"\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
        
        email = re.findall(email_pattern, text)
        phone = re.findall(phone_pattern, text)
        
        # Try to find name in first few lines
        name_lines = text.split("\n")[:5]
        name = "N/A"
        for line in name_lines:
            if len(line.split()) >= 2:
                name = line.strip()
                break
        
        return {
            "Name": name,
            "Email": email[0] if email else "N/A",
            "Phone": phone[0] if phone else "N/A"
        }

    def save_to_sheet(self, data):
        """Save data to Google Sheets"""
        # Ensure headers exist
        headers = ["Name", "Email Address", "Phone No", "Google Drive Link"]
        if not self.sheet.row_values(1):
            self.sheet.insert_row(headers, 1)
        
        # Check for duplicates
        if self._is_duplicate_in_sheets(data["Email"]):
            print(f"ℹ️ Entry already exists for {data['Email']}")
            return False
        
        self.sheet.append_row([
            data["Name"],
            data["Email"],
            data["Phone"],
            data["Drive Link"]
        ])
        return True

    def process_resume(self, file_path):
        """Process a single resume"""
        try:
            # Read file content and calculate hash
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = self._calculate_file_hash(content)
            
            # Upload to Drive (handles duplicates internally)
            file_id, drive_link = self.upload_to_drive(file_path)
            
            # Extract text
            text = self.extract_text_from_pdf(file_id)
            
            # Extract details
            details = self.extract_details(text)
            details["Drive Link"] = drive_link
            
            # Save to sheet (handles duplicates internally)
            if self.save_to_sheet(details):
                print(f"✅ Processed new resume for {details['Name']}")
            
            # Clean up local file
            os.remove(file_path)
            print(f"✅ Removed local file: {os.path.basename(file_path)}")
            
            return True
        except Exception as e:
            print(f"❌ Error processing resume {file_path}: {str(e)}")
            return False

def main():
    # Get credentials from environment variables
    EMAIL = os.getenv('EMAIL')
    PASSWORD = os.getenv('PASSWORD')
    
    if not all([EMAIL, PASSWORD]):
        raise ValueError("Missing required environment variables. Please check your .env file.")
    
    # Initialize processor
    processor = ResumeProcessor()
    
    # Fetch new resumes from email
    print("\n1️⃣ Fetching resumes from email...")
    saved_files = processor.fetch_email_attachments(EMAIL, PASSWORD)
    
    if not saved_files:
        print("ℹ️ No new resumes to process")
        return
    
    # Process each resume
    print("\n2️⃣ Processing resumes...")
    for file_path in saved_files:
        processor.process_resume(file_path)
        time.sleep(1)  # Avoid API rate limits
    
    print("\n✨ Resume processing complete!")

if __name__ == "__main__":
    main()
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# ✅ Step 1: Authenticate with Google Drive API
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SERVICE_ACCOUNT_FILE = "credential.json"  # Ensure this file exists

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build("drive", "v3", credentials=creds)

print("✅ Google Drive API authentication successful!")

# ✅ Step 2: Function to Check if File Already Exists in Google Drive
def file_exists(file_name, folder_id):
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    return len(results.get("files", [])) > 0  # Returns True if file exists

# ✅ Step 3: Function to Upload a Single File (Only if Not Duplicate)
def upload_to_drive(file_path, folder_id):
    file_name = os.path.basename(file_path)  # Extract filename

    if file_exists(file_name, folder_id):  # Check if file exists
        print(f"⚠️ Skipping {file_name}, already uploaded.")
        return  # Skip duplicate upload

    file_metadata = {
        "name": file_name,
        "parents": [folder_id]  # Upload inside the specified folder
    }

    media = MediaFileUpload(file_path, mimetype="application/pdf")

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    print(f"✅ Uploaded {file_name} to Google Drive with File ID: {uploaded_file.get('id')}")

# ✅ Step 4: Function to Upload All Resumes in a Folder
def upload_all_resumes(folder_path, drive_folder_id):
    if not os.path.exists(folder_path):
        print(f"❌ Folder '{folder_path}' does not exist!")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]

    if not pdf_files:
        print("❌ No PDF files found in the folder!")
        return

    print(f"📂 Found {len(pdf_files)} resumes. Uploading to Google Drive...")

    for file in pdf_files:
        file_path = os.path.join(folder_path, file)
        upload_to_drive(file_path, drive_folder_id)

    print("✅ All new resumes uploaded successfully!")

# ✅ Step 5: Run the Script
FOLDER_ID = "1UYzFDDRaS__DucpWXU4Ul2r2rpbz0AH2"  # Replace with your actual Google Drive Folder ID
upload_all_resumes("./Resume", FOLDER_ID)  # Make sure this folder exists

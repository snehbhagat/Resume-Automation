# 📄 Resume Automation System 🚀  

An automated system that fetches resumes from email, uploads them to Google Drive, extracts applicant details, and stores the information in Google Sheets. It also notifies HR via email and provides a Streamlit dashboard for managing applicants.  

---

## 📌 Features  

✅ **Fetch New Resumes** – Automatically fetches unread resumes from Gmail using IMAP.  
✅ **Save Locally** – Stores resumes (PDF/DOCX) in a local folder (`./Resumes`).  
✅ **Upload to Google Drive** – Checks for duplicates before uploading resumes.  
✅ **Extract Resume Details** – Extracts **Name, Email, Phone** using OCR & regex.  
✅ **Store in Google Sheets** – Saves extracted details for HR access.  
✅ **Send Email Notifications** – Notifies HR when a new resume is processed.  
✅ **Streamlit Dashboard** – Allows HR to view, search, and download applicant details.  
✅ **Runs Automatically** – Checks for new resumes every **5 minutes**.  

---

## 📌 Requirements  

Before running the system, ensure you have the following installed:  

### **🔹 Required Software**  
- **Python 3.8+** (Recommended)  
- **Google Cloud Account** (For Drive & Sheets API)  
- **Gmail Account with IMAP Enabled**  

### **🔹 Required Python Libraries**  
Install all dependencies using:  
```bash
pip install -r requirements.txt
2️⃣ Set Up Gmail IMAP & Generate App Password
🔹 Enable IMAP Access in Gmail (Guide).
🔹 Generate a Google App Password (Guide).

3️⃣ Set Up Google Drive & Google Sheets API
🔹 Enable Google Drive API and Google Sheets API in Google Cloud Console.
🔹 Download the credentials.json file and save it in your project folder.

4️⃣ Add Your Credentials
Create a .env file (or update the script) with your credentials:

📌 Running the System
1️⃣ Start the Automated Pipeline
bash
Copy
Edit
python auto_resume_pipeline.py
✅ Fetches new resumes from email
✅ Saves them locally
✅ Uploads to Google Drive (avoids duplicates)
✅ Extracts details & stores in Google Sheets
✅ Sends email notifications to HR
✅ Runs every 5 minutes

2️⃣ Run the Streamlit Dashboard
bash
Copy
Edit
streamlit run dashboard.py
✅ View all applicants
✅ Search by Name, Email, or Phone
✅ Download applicant data in CSV/Excel


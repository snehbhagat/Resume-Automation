import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ✅ Step 1: Authenticate and Fetch Data from Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "credential_sheet.json"  # Ensure this file exists in your project folder

# Authenticate Google Sheets API
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Open your Google Sheet
SHEET_ID = "1Mx674i2GPSTl2LK280ou4yyfgBHcmg42bV76YJ6iYTQ"  # Replace with your actual Sheet ID
sheet = client.open_by_key(SHEET_ID).sheet1  # Select first sheet

# Function to fetch data from Google Sheets
def fetch_data():
    data = sheet.get_all_records()  # Get all data as a list of dictionaries
    return pd.DataFrame(data)  # Convert to Pandas DataFrame

# ✅ Step 2: Build the Streamlit Dashboard
st.title("📄 Job Applicant Dashboard")
st.markdown("### View and Manage Job Applications")

# Fetch data from Google Sheets
df = fetch_data()

# ✅ Step 3: Search & Filter Options
search_query = st.text_input("🔍 Search Applicants (Name, Email, Phone):").lower()

if search_query:
    df = df[df.astype(str).apply(lambda row: row.str.lower().str.contains(search_query).any(), axis=1)]

# ✅ Step 4: Display Data in a Table
st.dataframe(df, use_container_width=True)

# ✅ Step 5: Download Data as Excel/CSV
st.markdown("### 📥 Download Data")
file_format = st.selectbox("Choose Format", ["CSV", "Excel"])
if st.button("Download"):
    if file_format == "CSV":
        df.to_csv("applicants.csv", index=False)
        st.success("✅ Data saved as `applicants.csv`")
    else:
        df.to_excel("applicants.xlsx", index=False)
        st.success("✅ Data saved as `applicants.xlsx`")

st.markdown("---")
st.markdown("⚡ **Built with Streamlit**")


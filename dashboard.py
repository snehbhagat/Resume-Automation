import os
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="Job Applicant Dashboard",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
        /* Main container padding */
        .main > div {
            padding: 2rem 3rem;
        }
        
        /* Headers */
        h1 {
            color: #1E3D59;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e0e0e0;
        }
        
        h3 {
            color: #2E5077;
            margin-top: 2rem;
        }
        
        /* Table styling */
        table {
            font-size: 14px;
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        th {
            background-color: #1E3D59;
            color: white;
            font-weight: 500;
            text-align: left;
            padding: 12px 15px;
        }
        
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tr:hover {
            background-color: #f5f5f5;
        }
        
        /* Link styling */
        a.drive-link {
            background-color: #4CAF50;
            color: white;
            padding: 6px 12px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            transition: background-color 0.3s;
        }
        
        a.drive-link:hover {
            background-color: #45a049;
        }
        
        /* Stats container */
        .stats-box {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            margin-bottom: 20px;
        }
        
        /* Search box */
        .stTextInput > div > div {
            padding: 5px 10px;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# Configuration
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH")
SHEET_ID = os.getenv("SHEET_ID")

@st.cache_data(ttl=300)
def initialize_google_sheets():
    """Initialize Google Sheets connection"""
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

@st.cache_data(ttl=60)
def fetch_data():
    """Fetch data from Google Sheets"""
    sheet = initialize_google_sheets()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def make_clickable_drive_link(link):
    """Convert Google Drive link to a direct viewable link"""
    if pd.isna(link) or not str(link).startswith("http"):
        return "❌ No Resume"
    
    # Extract file ID from Google Drive link
    file_id = None
    if "drive.google.com" in link:
        parts = link.split("/")
        if "d" in parts:
            file_id = parts[parts.index("d") + 1]
        elif "file/d" in link:
            file_id = link.split("file/d/")[1].split("/")[0]
    
    # Construct direct view link
    if file_id:
        view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        return f'<a class="drive-link" href="{view_link}" target="_blank">📄 View Resume</a>'
    
    return f'<a class="drive-link" href="{link}" target="_blank">📄 View Resume</a>'

def main():
    # Header
    st.title("📄 Job Applicant Tracking System")
    
    try:
        # Fetch data
        with st.spinner("Loading applicant data..."):
            df = fetch_data()
        
        # Convert Google Drive Links to Clickable Buttons
        if "Google Drive Link" in df.columns:
            df["View Resume"] = df["Google Drive Link"].apply(make_clickable_drive_link)
            df = df.drop(columns=["Google Drive Link"])
        
        # Sidebar filters and search
        st.sidebar.title("🔍 Search & Filters")
        
        # Search box with multiple field support
        search_query = st.sidebar.text_input(
            "Search by Name, Email, or Phone:",
            placeholder="Enter search term...",
            help="Search across all fields"
        ).lower()
        
        # Apply filters
        filtered_df = df.copy()
        if search_query:
            mask = filtered_df.astype(str).apply(
                lambda x: x.str.lower().str.contains(search_query, na=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]
        
        # Display stats
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
                <div class="stats-box">
                    <h3 style="margin-top:0">📊 Dashboard Stats</h3>
                    <p><strong>Total Applicants:</strong> {len(df)}</p>
                    <p><strong>Filtered Results:</strong> {len(filtered_df)}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Display applicants table
        st.markdown("### 👥 Applicants List")
        st.markdown(
            filtered_df.to_html(
                escape=False,
                index=False,
                classes=['styled-table']
            ),
            unsafe_allow_html=True
        )
        
        # Download section
        st.markdown("### 📥 Export Data")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            file_format = st.selectbox(
                "Format:",
                ["Excel", "CSV"],
                help="Choose export format"
            )
        
        with col2:
            if st.button("Download Data", help="Download filtered data"):
                try:
                    # Remove HTML from View Resume column for export
                    export_df = filtered_df.copy()
                    if "View Resume" in export_df.columns:
                        export_df = export_df.drop(columns=["View Resume"])
                    
                    if file_format == "CSV":
                        export_df.to_csv("applicants.csv", index=False)
                        st.success("✅ Data saved as `applicants.csv`")
                    else:
                        export_df.to_excel("applicants.xlsx", index=False)
                        st.success("✅ Data saved as `applicants.xlsx`")
                except Exception as e:
                    st.error(f"Error saving file: {str(e)}")
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.info("Please check your Google Sheets configuration and credentials.")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
        ⚡ Built with Streamlit | © 2024
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

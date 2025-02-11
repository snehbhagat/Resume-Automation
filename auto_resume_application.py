import email
import imaplib
import os
from email.header import decode_header
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_attachments(email_address, password, search_criteria='(SUBJECT "Job Application")', folder="Resume"):
    """
    Fetch attachments from emails matching search criteria and save them to specified folder.
    
    Parameters:
    email_address (str): Your email address
    password (str): Your email password or app-specific password
    search_criteria (str): IMAP search criteria to filter emails
    folder (str): Local folder to save attachments
    """
    
    # Create folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    try:
        # Connect to Gmail's IMAP server
        print("Connecting to Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, password)
        print("Successfully logged in")
        
        # Select inbox
        mail.select("inbox")
        print("Searching for matching emails...")
        
        # Search for emails matching criteria
        status, message_numbers = mail.search(None, search_criteria)
        
        if status != 'OK':
            raise Exception(f"Search failed with status: {status}")
            
        if not message_numbers[0]:
            print("No matching emails found")
            return
            
        print(f"Found {len(message_numbers[0].split())} matching emails")
        
        for num in message_numbers[0].split():
            try:
                # Fetch email message
                _, msg_data = mail.fetch(num, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Get email subject
                subject = decode_header(email_message["subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                # Get sender
                sender = email_message.get("from")
                
                print(f"\nProcessing email from: {sender}")
                print(f"Subject: {subject}")
                
                # Process attachments
                attachments_found = False
                for part in email_message.walk():
                    if part.get_content_maintype() == "multipart":
                        continue
                    if part.get("Content-Disposition") is None:
                        continue
                    
                    # Get filename of attachment
                    filename = part.get_filename()
                    if filename:
                        attachments_found = True
                        # Clean filename and add timestamp
                        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        new_filename = f"{timestamp}_{filename}"
                        
                        # Save attachment
                        filepath = os.path.join(folder, new_filename)
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        
                        print(f"Saved attachment: {new_filename}")
                
                if not attachments_found:
                    print("No attachments found in this email")
                    
            except Exception as e:
                print(f"Error processing email: {str(e)}")
                continue
        
        mail.close()
        mail.logout()
        print("\nFinished processing emails")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if 'mail' in locals():
            try:
                mail.close()
                mail.logout()
            except:
                pass

# Example usage
if __name__ == "__main__":
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    
    if not EMAIL or not PASSWORD:
        raise ValueError("Missing EMAIL or PASSWORD in environment variables")

    # Different search criteria examples:
    SEARCH_OPTIONS = {
        'job_applications': '(SUBJECT "Job Application")',
        'resumes': '(OR (SUBJECT "Job Application") (SUBJECT "Resume"))',
        'last_30_days': '(AND (SINCE "30-days-ago") (SUBJECT "Job Application"))'
    }
    
    fetch_attachments(
        email_address=EMAIL,
        password=PASSWORD,
        search_criteria=SEARCH_OPTIONS['job_applications'],  # Choose the search criteria you want
        folder="Resume"
    )

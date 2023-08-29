import streamlit as st
import pymongo
import imaplib
import email
import re
from dateutil import parser
import unchecked_mails, checked_mails
import datetime
import threading
import time
import pandas as pd
from io import BytesIO
from xlsxwriter.workbook import Workbook








#Database connections
@st.cache_resource
def init_connection():
   
    try:
        db_username = st.secrets.db_username
        db_password = st.secrets.db_password

        mongo_uri_template = "mongodb+srv://{username}:{password}@emailreader.elzbauk.mongodb.net/"
        mongo_uri = mongo_uri_template.format(username=db_username, password=db_password)

        client = pymongo.MongoClient(mongo_uri)
        return client
    except:
        st.write("Connection Could not be Established with database")
#  Database
client = init_connection()
db= client['EmailDatabase']
collection_clients = db["Emails"]
collection_usersdetail = db['Users']
collection_searchwords= db['Searchwords']

def extract():
    query = {}
    results = collection_usersdetail.find(query)
    for result in results:
        emailid = result['emailid']
        passwordid = result['password']
        imap_server_id = result['imapserver']
        if emailid:
            input_extract(passwordid, imap_server_id, emailid)


def home_page():
    st.subheader("Registered Users")
    col1, col2 = st.columns(2)
    with col1:
        download_button =st.button("Click to download all emails")
    with col2:
        generate_button = st.button("Export to excel")
    
    # Query the collection and project emailid and username fields
    query = {}
    projection = {"emailid": 1, "username": 1, "_id": 0}
    
    results = collection_usersdetail.find(query, projection)
    
    # Display the results as a list
    for result in results:
        st.write(f"Handler: <span style='color: orange;'>{result['username']}</span>,"
                 f"<span style='margin-right: 10px;'></span>"
             f"Email ID: <span style='color: green;'>{result['emailid']}</span>", unsafe_allow_html=True)
        st.write("")
    
    if download_button:
        st.error("Downloading.........")
        t1 = threading.Thread(target=extract)
        t1.start()
        t1.join()
        st.success("**Downloading completed**")
        st.write("**************************************************************")

    if generate_button:
        export_to_excel()
        st.write("**************************************************************")

    
    
    st.sidebar.subheader("Auto-Extract Emails")
    passwordid=""
    imap_server_id=""
    emailid = st.sidebar.text_input("Enter Email Id")
    if st.sidebar.button("Read Mails"):
    
        passwordid, imap_server_id = get_user_credentials(emailid)
        input_extract(passwordid, imap_server_id, emailid)


        
def input_extract(passwordid, imap_server_id, emailid):
    # Fetch the email status from the database
    st.sidebar.warning(f"{emailid} extraction under progress")
    user_data = collection_usersdetail.find_one({"emailid": emailid})
    email_status = user_data.get("status")
    if email_status == "Inactive":
       st.sidebar.error(f"{emailid} is not active")
       time.sleep(1)
       
    elif email_status != "Inactive":
        
        # Connect to inbox
        try:
                imap_server = imaplib.IMAP4_SSL(host=imap_server_id)
                imap_server.login(emailid, passwordid)
                #Default select is for inbox
                imap_server.select()
                _, message_numbers_raw = imap_server.search(None, 'ALL')
                count=0
                for message_number in message_numbers_raw[0].split():
                    count=0
                    _, msg = imap_server.fetch(message_number, '(RFC822)')

                    # Rest of your email processing code
                    message = email.message_from_bytes(msg[0][1])
                    content = "" 
                    for part in message.walk():
                        if (part.get_content_type() == "text/plain"):
                            
                            content = part.get_payload()
                    
                    
                    # Format the date to match the desired format
                    parsed_date = parser.parse(message["date"])
                    formatted_date = parsed_date.strftime("%d %b %Y")  

                    existing_document = collection_clients.find_one({
                        "sender":message["from"], "reciever":message["to"] , "date":formatted_date,
                        "subject":message["subject"], "description":content })
                    if existing_document is None:
                            # Document doesn't exist, insert data into the collection
                            # Your email,designation, remarks from content extract_job_title
                            d, e, r = extract_job_title(content)
                            designation, emails, remarks = list(set(d)),list(set(e)),list(set(r))
 
                            new_document = {"sender":message["from"], "reciever":message["to"] , "date":formatted_date ,
                            "subject":message["subject"], "description":content, "jobtitle":designation,"emails":emails, "remark":remarks , "status":"unchecked", "comments":""}
                            collection_clients.insert_one(new_document)
                            status = "updated" 

                    else: 
                            count+=1
                    if (count>0):
                            status= "already updated"

        except imaplib.IMAP4.error:
                    status = "failed."

                # Update the corresponding document in 'collection_searchwords'
        search_query = {"emailid": emailid}
        search_update = {"$set": {"inbox": status}}  # Update the 'inbox' field with the status
        collection_usersdetail.update_one(search_query, search_update)
        
        st.sidebar.write(status)
        time.sleep(1)  # Introduce a 1-second delay

        try:
    

                imap_server = imaplib.IMAP4_SSL(host=imap_server_id)
                imap_server.login(emailid, passwordid)
                #Default select is for inbox
                imap_server.select('[Gmail]/Spam')
                _, message_numbers_raw = imap_server.search(None, 'ALL')
                count=0
                for message_number in message_numbers_raw[0].split():
                    count=0
                    _, msg = imap_server.fetch(message_number, '(RFC822)')

                     # Rest of your email processing code
                    message = email.message_from_bytes(msg[0][1])
                    content = "" 
                    for part in message.walk():
                        if (part.get_content_type() == "text/plain"):
                            
                            content = part.get_payload()

                    # Format the date to match the desired format
                    parsed_date = parser.parse(message["date"])
                    formatted_date = parsed_date.strftime("%d %b %Y")  
                    existing_document = collection_clients.find_one({
                        "sender":message["from"], "reciever":message["to"] , "date":formatted_date,
                        "subject":message["subject"], "description":content })
                    
                    if existing_document is None:
                            # Document doesn't exist, insert data into the collection
                            # Your email,designation, remarks from content extract_job_title
                            d, e, r = extract_job_title(content)
                            designation, emails, remarks = list(set(d)),list(set(e)),list(set(r))

                            new_document = {"sender":message["from"], "reciever":message["to"] , "date":formatted_date ,
                            "subject":message["subject"], "description":content, "jobtitle":designation,"emails":emails, "remark":remarks , "status":"unchecked", "comments":""}
                            collection_clients.insert_one(new_document)
                            status = "updated" 

                    else: 
                            count+=1
                if (count>0):
                            status= "already updated"

        except imaplib.IMAP4.error:
                    status = "failed."

        search_query = {"emailid": emailid}
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%H:%M:%S")
        search_update = {"$set": {"spam": status, "lastupdated":formatted_time}}  # Update the 'inbox' field with the status
        collection_usersdetail.update_one(search_query, search_update)
        # st.sidebar.write(status)
        
        st.sidebar.write(status)
        time.sleep(1)


def extract_job_title(content):
    remarks=[]
    job_list=[]
    emails=[]
    # Create a Collection so that keywords can be added and removed in words_to_find
    # Query to extract data from the "Searchwords" collection
    search_words_data = collection_searchwords.find({}, {"_id": 0, "keyword": 1})

    # Extract "keyword" values and store them in a list
    search_words_list = [item["keyword"] for item in search_words_data]
    words_to_find = search_words_list
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    job_title_keywords = ["job title","job role","role","job", "position"]
    emails = re.findall(email_pattern, content)
    job_title_pattern = rf'({"|".join(job_title_keywords)})\s*(?:of|as|is)?\s*(\w+\s*\w*)'
    job_title_match = re.findall(job_title_pattern, content, flags=re.I)
    for word in words_to_find:
        if re.search(r'\b' + re.escape(word) + r'\b', content, re.IGNORECASE):
            remarks.append(word)
    for match in job_title_match:
        job_title, name = match
        job_list.append(name)
    return job_list, emails, remarks

def get_user_credentials(emailid):
    try:
        user_data = collection_usersdetail.find_one({"emailid": emailid})
        passwordid = user_data.get("password")
        imap_server_id = user_data.get("imapserver")
        return passwordid, imap_server_id
    except:
        st.sidebar.write("user not found")
        time.sleep(1)
    
        st.experimental_rerun()


def export_to_excel():
    # Create a new Excel workbook
    
    
    query = {}
    projection = {"date": 1, "sender": 1, "reciever":1, "subject":1, "emails":1, "remark":1, "comments":1, "_id": 0}
    data = list(collection_clients.find(query, projection))
    
    # Convert data to a DataFrame
    df = pd.DataFrame(data)
    df.sort_values(by='date', inplace=True, ascending=False)
    df['date'] = pd.to_datetime(df['date'], format='%d %b %Y')
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df = df.sort_values(by='date', ascending=False)

    # Display the DataFrame (optional)
    st.write(df)
    output = BytesIO()

    # Create an Excel writer and write the DataFrame to it
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        format1 = workbook.add_format({'num_format': '0.00'}) 
        worksheet.set_column('B:B', None, format1)  # Formatting the 'Age' column

    # Get the value of the Excel file from the BytesIO object
    excel_file = output.getvalue()

    # Provide a download button
    st.download_button(
        label='Download Excel File',
        data=excel_file,
        file_name='email_data.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key="download_button"
    )
    

def main():
        # Radio buttons to navigate between pages
    st.sidebar.subheader("Navigation Menu")
    navigation = st.sidebar.radio("", ("Home", "Fresh Emails", "Processed Emails"))
    st.sidebar.write("----------------------------------")
    if navigation == "Home":
        home_page()
    elif navigation == "Fresh Emails":
        unchecked_mails.main()
        #st.write("unchecked")
    elif navigation == "Processed Emails":
        checked_mails.main()
        #st.write("checked")


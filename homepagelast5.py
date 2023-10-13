import streamlit as st
import pymongo
import imaplib
import email
import re
from dateutil import parser
import  freshmails, processedmails
from email.header import decode_header
from datetime import timedelta
import datetime
import threading
import time
import pandas as pd
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb
import xlsxwriter 
from xlsxwriter.workbook import Workbook
from datetime import datetime, timedelta


#Database connections
@st.cache_resource
def init_connection():
   
    try:
        # db_username = st.secrets.db_username
        # db_password = st.secrets.db_password

        # mongo_uri_template = "mongodb+srv://{username}:{password}@emailreader.elzbauk.mongodb.net/"
        # mongo_uri = mongo_uri_template.format(username=db_username, password=db_password)

        # client = pymongo.MongoClient(mongo_uri)
        client=pymongo.MongoClient("mongodb+srv://Vedsu:CVxB6F2N700cQ0qu@cluster0.thbmwqi.mongodb.net/")
        
        return client
    
    except:
        
        st.write("Connection Could not be Established with database")

#Database
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
    
    st.write("--------------------------------------------------------------")
    
    col1, col2 = st.columns(2)
    
    with col1:
    
        download_button =st.button("Click to download all emails")
    
    with col2:
    
        generate_button = st.button("Sync Database")
    
    st.write("--------------------------------------------------------------")
    
    # Query the collection and project emailid and username fields
    query = {}
    
    projection = {"emailid": 1, "username": 1, "_id": 0}
    
    results = collection_usersdetail.find(query, projection)
    
    # Display the results as a list
    col1, col2 = st.columns(2)
    
    for result in results:
        
        with col1:
            st.write(f"Handler: {result['username']}" )
        
        with col2:
            st.write(f"Email ID: <span style='color: green;'>{result['emailid']}</span>", unsafe_allow_html=True)
        
        
    
    if download_button:
        
        st.error("Downloading.........")
        
        t1 = threading.Thread(target=extract)
        
        t1.start()
        
        t1.join()
        
        st.success("**Downloading completed**")
        
        st.write("**************************************************************")

    if generate_button:
        
        remove_duplicate_values()
        
        st.write("**************************************************************")

    
    
    st.sidebar.subheader("Auto-Extract Emails")
    selected_option = st.sidebar.selectbox("Select auto-read days", ["1", "3", "5"])
    no_of_days = int(selected_option)
    
    passwordid=""
    
    imap_server_id=""
    
    emailid = st.sidebar.text_input("Enter Email Id")
    
    if st.sidebar.button("Read Mails"):
    
        passwordid, imap_server_id = get_user_credentials(emailid)
        
        input_extract(passwordid, imap_server_id, emailid, no_of_days)



def input_extract(passwordid, imap_server_id, emailid, no_of_days):
        
        st.sidebar.warning(f"{emailid} extraction under progress")
        
        user_data = collection_usersdetail.find_one({"emailid": emailid})
        
        email_status = user_data.get("status")
        
        

        if email_status == "Inactive":
            
            st.sidebar.error(f"{emailid} is not active")
            
            time.sleep(1)
            # Connect to inbox
        
        
        elif email_status != "Inactive":
            # st.sidebar.warning("Extraction in Progess")
            
            document_to_insert =[]
            inbox_status = ""
            spam_status = ""
        
            try:
                    imap_server = imaplib.IMAP4_SSL(host=imap_server_id)
                    
                    imap_server.login(emailid, passwordid)
                    
                    #Default select is for inbox
                    status, messages = imap_server.select()

                    
                    # Calculate the date 5 days ago from today
                    since_date = (datetime.now() - timedelta(days=no_of_days)).strftime("%d-%b-%Y")

                    # Create a search criteria to fetch emails sent since the calculated date
                    search_criteria = f'SINCE {since_date}'

                    # Search for emails based on the search criteria
                    status, message_numbers_raw = imap_server.search(None, search_criteria)

                    # If you want to fetch all emails sent in the last 5 days, you can get the message numbers as a list
                    message_numbers_list = message_numbers_raw[0].split()
                    
                    
                    N = int(len(message_numbers_list))
                    
                    st.sidebar.write("Inbox:", N)

                    # messages = int(messages[0])
                    
                   
                    
                    for message_number in message_numbers_list:
                        sender = None
                        reciever = None
                        date = None
                        subject = None
                        description = None
                        # st.write(message_number)
                        text_string = message_number.decode('utf-8')

                        # Convert the text string to an integer
                        number = int(text_string)
                        # fetch the email message by ID
                        
                        res, msg = imap_server.fetch(str(number), "(RFC822)")    
                        
                        for response in msg:
                            
                            try:
                
                                if isinstance(response, tuple):
                                    
                                    # parse a bytes email into a message object
                                    msg = email.message_from_bytes(response[1])
                                       
                                    # decode email sender
                                    From, encoding = decode_header(msg.get("from"))[0]
                                    
                                    sender = From
                                    
                                    if isinstance(From, bytes):
                                    
                                        From = From.decode(encoding)
                                        sender = From
                            
                                        # st.write(sender)
                                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                    sender_matches = re.findall(email_pattern, sender)
                                    
                                    # Convert the list of matches to a single string, separated by a delimiter (e.g., comma)
                                    sender = ', '.join(sender_matches)

                                    if(sender.split('@')[0].lower() != "mailer-daemon" and sender.split('@')[0].lower() != "postmaster" and sender.split('@')[0].lower() != "emailsecurity" and sender.split('@')[0].lower() != "bounce"):
                            
                                        # decode the email subject
                                        
                                        Subject, encoding = decode_header(msg["subject"])[0]
                                        subject = Subject
                                        
                                        if isinstance(Subject, bytes):
                                            
                                            # if it's a bytes, decode to str
                                            Subject = Subject.decode(encoding)
                                            subject = Subject


                                        # decode the email reciever
                                        To, encoding = decode_header(msg["to"])[0]
                                        
                                        reciever = To
                                        
                                        if isinstance(To, bytes):
                                            
                                            # if it's a bytes, decode to str
                                            To = To.decode(encoding)
                                            # st.write(To)
                                            reciever = To

                                            # st.write(reciever)
                                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                        reciever_matches = re.findall(email_pattern, reciever)

                                        reciever = ', '.join(reciever_matches)

                                        # decode the email subject
                                        Date, encoding = decode_header(msg["date"])[0]
                                        parsed_date = parser.parse(Date)
                                        date = parsed_date.strftime("%Y-%m-%d")
                                        
                                        if isinstance(Date, bytes):
                                            
                                            # if it's a bytes, decode to str
                                            Date = Date.decode(encoding)
                                            parsed_date = parser.parse(Date)
                                            date = parsed_date.strftime("%Y-%m-%d")
                                            # st.write(date)


                                        # if the email message is multipart
                                        if msg.is_multipart():
                                                
                                            # iterate over email parts
                                            for part in msg.walk():
                                                # extract content type of email
                                                content_type = part.get_content_type()
                                                content_disposition = str(part.get("Content-Disposition"))

                                                try:
                                                    # get the email body
                                                    body = part.get_payload(decode=True).decode()
                                                
                                                except:
                                                    
                                                    pass
                                                
                                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                                    
                                                    # print text/plain emails and skip attachments
                                                    description =  body
                                                
                                                elif "attachment" in content_disposition:
                                                    pass

                                        else:
                                            # extract content type of email
                                            content_type = msg.get_content_type()
                                            
                                            # get the email body
                                            body = msg.get_payload(decode=True).decode()
                                            
                                            if content_type == "text/plain":
                                                
                                                # print only text email parts
                                                description = body

                                        designation, emails, remarks = extract_job_title(description)
                                
                                        #designation, emails, remarks = list(set(d)),list(set(e)),list(set(r))
                                        
                                        new_document = {"sender":sender, "reciever":reciever , "date":date ,
                                        "subject":subject, "description":description, "jobtitle":designation,"emails":emails, "remark":remarks , "status":"unchecked", "comments":" "}
                                        
                                        #extending the list 
                                        # st.write(new_document)
                                        document_to_insert.append(new_document)
                            except:
                                pass

                    try:
                        #st.write("insert the list into collection")
                        collection_clients.insert_many(document_to_insert)
                        
                        st.sidebar.write("Inbox Updated:", len(document_to_insert))
                        
                        inbox_status = "updated"

                    except:
    
                        st.sidebar.write("No New mails found")
                        
                        inbox_status = "already updated"



            except imaplib.IMAP4.error:
                                
                st.sidebar.write("failed to connect to inbox")
                
                inbox_status = "failed"

            
            
            document_to_insert =[]
            
            # try:
                
            #     imap_server = imaplib.IMAP4_SSL(host=imap_server_id)

            #     imap_server.login(emailid, passwordid)

            #     #Default select is for inbox
            #     status, messages = imap_server.select('[Gmail]/Spam')
            #     # Calculate the date 5 days ago from today
            #     since_date = (datetime.now() - timedelta(days=5)).strftime("%d-%b-%Y")

            #     # Create a search criteria to fetch emails sent since the calculated date
            #     search_criteria = f'SINCE {since_date}'

            #     # Search for emails based on the search criteria
            #     status, message_numbers_raw = imap_server.search(None, search_criteria)

            #     # Search for emails based on the search criteria
            #     # status, message_numbers_raw = imap_server.search(None, 'ALL')

            #     message_numbers_list = message_numbers_raw[0].split()
                
            #     N = int(len(message_numbers_list))
            #     st.sidebar.write("Spam :", N)

            #     for message_number in message_numbers_list:
            #         sender = None
            #         reciever = None
            #         date = None
            #         subject = None
            #         description = None
            #         # st.write(message_number)
            #         text_string = message_number.decode('utf-8')

            #         # Convert the text string to an integer
            #         number = int(text_string)
                    
            #         # fetch the email message by ID
            #         res, msg = imap_server.fetch(str(number), "(RFC822)")    
                    
            #         for response in msg:
                        
            #             try:
                        
            #                 if isinstance(response, tuple):
                                
            #                     # parse a bytes email into a message object
            #                     msg = email.message_from_bytes(response[1])
                                
            #                     # decode email sender
            #                     From, encoding = decode_header(msg.get("from"))[0]
            #                     sender = From
                                
            #                     if isinstance(From, bytes):
                                
            #                         From = From.decode(encoding)
            #                         sender = From
            #                         # st.write(sender)

            #                     email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                
            #                     sender_matches = re.findall(email_pattern, sender)
                                
            #                     # Convert the list of matches to a single string, separated by a delimiter (e.g., comma)
            #                     sender = ', '.join(sender_matches)
                                
            #                     if(sender.split('@')[0].lower() != "mailer-daemon" and sender.split('@')[0].lower() != "postmaster"):
                                
            #                         # decode the email subject
                                    
            #                         Subject, encoding = decode_header(msg["subject"])[0]
            #                         subject = Subject
                                    
            #                         if isinstance(Subject, bytes):
                                        
            #                             # if it's a bytes, decode to str
            #                             Subject = Subject.decode(encoding)
            #                             subject = Subject

                                    

            #                         # decode the email reciever
            #                         To, encoding = decode_header(msg["to"])[0]
                                    
            #                         reciever = To
                                    
            #                         if isinstance(To, bytes):
                                        
            #                             # if it's a bytes, decode to str
            #                             To = To.decode(encoding)
            #                             # st.write(To)
            #                             reciever = To
            #                             # st.write(reciever)
            #                         email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                    
            #                         reciever_matches = re.findall(email_pattern, reciever)

            #                         reciever = ', '.join(reciever_matches)

            #                         # decode the email subject
            #                         Date, encoding = decode_header(msg["date"])[0]
            #                         parsed_date = parser.parse(Date)
            #                         date = parsed_date.strftime("%Y-%m-%d")
                                    
            #                         if isinstance(Date, bytes):
                                        
            #                             # if it's a bytes, decode to str
            #                             Date = Date.decode(encoding)
            #                             parsed_date = parser.parse(Date)
            #                             date = parsed_date.strftime("%Y-%m-%d")
            #                             # st.write(date)
                                
                                    
            #                         if msg.is_multipart():
                                            
            #                             # iterate over email parts
            #                             for part in msg.walk():
            #                                 # extract content type of email
            #                                 content_type = part.get_content_type()
            #                                 content_disposition = str(part.get("Content-Disposition"))

            #                                 try:
            #                                     # get the email body
            #                                     body = part.get_payload(decode=True).decode()
            #                                 except:
            #                                     pass
                                            
            #                                 if content_type == "text/plain" and "attachment" not in content_disposition:
                                                
            #                                     # print text/plain emails and skip attachments
            #                                     description =  body
                                            
            #                                 elif "attachment" in content_disposition:
            #                                     pass

            #                         else:
            #                             # extract content type of email
            #                             content_type = msg.get_content_type()
                                        
            #                             # get the email body
            #                             body = msg.get_payload(decode=True).decode()
                                        
            #                             if content_type == "text/plain":
                                            
            #                                 # print only text email parts
            #                                 description = body

            #                         designation, emails, remarks = extract_job_title(description)
                            
            #                         #designation, emails, remarks = list(set(d)),list(set(e)),list(set(r))
                                    
            #                         new_document = {"sender":sender, "reciever":reciever , "date":date ,
            #                         "subject":subject, "description":description, "jobtitle":designation,"emails":emails, "remark":remarks , "status":"unchecked", "comments":" "}
                                    
            #                         #extending the list 
            #                         # st.write(new_document)
            #                         document_to_insert.append(new_document)
            #             except:
            #                 pass

            try:
                    #st.write("insert the list into collection")
                    collection_clients.insert_many(document_to_insert)
                    st.sidebar.write("Spam Updated:", len(document_to_insert))
                    spam_status = "updated"

            except:

                    st.sidebar.write("Spam Stopped")
                    spam_status = "Not extracted"



            # except imaplib.IMAP4.error:
            #     st.sidebar.write("failed to connect to spam")
            #     spam_status="failed"


            
            search_query = {"emailid": emailid}
            
            current_time = datetime.now()
            
            formatted_time = current_time.strftime("%H:%M:%S")
            
            search_update = {"$set": {"inbox": inbox_status, "spam": spam_status, "lastupdated":formatted_time}}  # Update the 'inbox' field with the status
            
            collection_usersdetail.update_one(search_query, search_update)
            
            
            time.sleep(1)


def extract_job_title(content):
    remarks_matches=[]
    job_list_matches=[]
    emails_matches=[]
    
    # Create a Collection so that keywords can be added and removed in words_to_find
    # Query to extract data from the "Searchwords" collection
    search_words_data = collection_searchwords.find({}, {"_id": 0, "keyword": 1})

    # Extract "keyword" values and store them in a list
    search_words_list = [item["keyword"] for item in search_words_data]
    
    words_to_find = search_words_list
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    job_title_keywords = ["job title","job role","role","job", "position"]
    
    emails_matches = re.findall(email_pattern, content)
    
    emails = ', '.join(emails_matches)
    
    job_title_pattern = rf'({"|".join(job_title_keywords)})\s*(?:of|as|is)?\s*(\w+\s*\w*)'
    
    job_title_match = re.findall(job_title_pattern, content, flags=re.I)

    
    
    for word in words_to_find:
       
        if re.search(r'\b' + re.escape(word) + r'\b', content, re.IGNORECASE):
            remarks_matches.append(word)
    
    remarks = ', '.join(remarks_matches)
    
    for match in job_title_match:
    
        job_title, name = match
        job_list_matches.append(name)
    
    job_list = ', '.join(job_list_matches)
    
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


def remove_duplicate_values():
    # Calculate the date 5 days ago from the current date
    # five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    # query = {"date": {"$gte": five_days_ago}}

    # Define the aggregation pipeline to find duplicates based on the specified fields
    pipeline = [
#         {
#     "$match": {
#         "date": {"$gte": five_days_ago}
#     }
# }
#         # {
#         #     "$match": {
#         #         "date": {"$gte": five_days_ago}  # Filter documents within the last 5 days
#         #     }
#         # },
        {
            "$group": {
                "_id": {
                    "sender": "$sender",
                    "description": "$description",
                    "reciever": "$reciever",
                    "subject":"$subject",
                    "date": "$date"
                },
                "duplicates": {"$addToSet": "$_id"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}  # Find documents with more than one occurrence
            }
        }
    ]
    data = list(collection_clients.aggregate(pipeline))
    #data = list(collection_clients.distinct("date"))

    # df=pd.DataFrame(data)
    # st.write(data)
    # Use the query to retrieve data from the last five days
    # results = collection_clients.find(query)

    # Process the results as needed
    # for document in results:
    # # Process each document from the last five days
    #     st.write(document)
    # Find and remove duplicate documents based on the filter
    # for doc in collection_clients.aggregate(pipeline):
    #     # Keep one copy (first occurrence) and delete the rest
    #     duplicates_to_remove = doc["duplicates"][1:]
    #     collection_clients.delete_many({"_id": {"$in": duplicates_to_remove}})
    
#     # Calculate the date 5 days ago from the current date
#     five_days_ago = datetime.now() - timedelta(days=5)
    
#     # Define the aggregation pipeline to find duplicates based on multiple fields
#     
#  pipeline = [
    # {
    #     "$group": {
    #         "_id": {
    #             field: f"${field}" for field in fields_to_match
    #         },
    #         "count": {"$sum": 1},
    #         "document_id": {"$first": "$_id"},
    #     }
    # },
    # {
    #     "$match": {
    #         "count": {"$gt": 1}
    #     }
    # }
    # ]
    # # Execute the aggregation pipeline to identify duplicates
    # duplicate_results = list(collection_clients.aggregate(pipeline))
    # df = pd.DataFrame(duplicate_results)
    # st.write(df)
    # time.sleep(2)
    
    # duplicates_to_remove =[]
    # # Find and remove duplicate documents based on the filter
    # for doc in duplicate_results:
    #      # Keep one copy (first occurrence) and delete the rest
    #      duplicates_to_remove.append(doc["document_id"])
         
    # collection_clients.delete_many({"_id": {"$in": duplicates_to_remove}})pipeline = [
    
#         {
#             "$group": {
#                 "_id": {
#                     "sender": "$sender",
#                     "reciever": "$reciever",
#                     "subject":"$subject",   # Field to check for duplicates (change to your field names)
#                     "description": "$description",
#                     "date": "$date"
#                 },
#                 "duplicates": {"$addToSet": "$_id"},
#                 "count": {"$sum": 1}
#             }
#         },
#         {
#             "$match": {
#                 "count": {"$gt": 1}  # Find documents with more than one occurrence
#             }
#         }
#     ]

#     # Find and remove duplicate documents based on the filter
    for doc in collection_clients.aggregate(pipeline):
        # Keep one copy (first occurrence) and delete the rest
        duplicates_to_remove = doc["duplicates"][1:]
        collection_clients.delete_many({"_id": {"$in": duplicates_to_remove}})
# #     # Create a new Excel workbook
    
    
#     query = {}
#     projection = {"date": 1, "sender": 1, "reciever":1, "subject":1, "emails":1, "remark":1, "comments":1, "_id": 0}
#     data = list(collection_clients.find(query, projection))
    
#     # Convert data to a DataFrame
#     df = pd.DataFrame(data)
#     df.sort_values(by='date', inplace=True, ascending=False)
#     df['date'] = pd.to_datetime(df['date'], format='%d %b %Y')
#     df["date"] = df["date"].dt.strftime("%Y-%m-%d")
#     df = df.sort_values(by='date', ascending=False)
    
#     st.write(df)

# #   csv = df.to_excel(None, index=False, engine='openpyxl')
# #     st.download_button(
# #         label="Download data as CSV",
# #         data=csv,
# #         file_name='large_df.csv',
# #         mime='text/csv',)

#     # Create a BytesIO object to hold the Excel file in memory
#     output = BytesIO()

#     # Create an Excel writer and write the DataFrame to it
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         df.to_excel(writer, index=False, sheet_name='Sheet1')
#         workbook = writer.book
#         worksheet = writer.sheets['Sheet1']
#         format1 = workbook.add_format({'num_format': '0.00'}) 
#         worksheet.set_column('B:B', None, format1)  # Formatting the 'Age' column

#     # Get the value of the Excel file from the BytesIO object
#     excel_file = output.getvalue()

#     # Provide a download button
#     st.download_button(
#         label='Download Excel File',
#         data=excel_file,
#         file_name='sample_data.xlsx',
#         mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
    


def main():
        # Radio buttons to navigate between pages
    st.sidebar.subheader("Navigation Menu")
    navigation = st.sidebar.radio("", ("Home", "Fresh Emails", "Processed Emails"))
    st.sidebar.write("----------------------------------")
    if navigation == "Home":
        home_page()
    elif navigation == "Fresh Emails":
        #unchecked_mails.main()
        freshmails.main()
        #st.write("unchecked")
    elif navigation == "Processed Emails":
        processedmails.main()
        #st.write("checked")


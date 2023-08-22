import streamlit as st
st.set_page_config(page_title="Vedsu Technology", page_icon="📧")
import yaml
import pymongo
import imaplib
import email
import re
from dateutil import parser
from yaml.loader import SafeLoader
from streamlit_authenticator import Authenticate 
import threading
import datetime
#import home
import homepage
st.subheader("Welcome to Email Reader")
#Database connections
@st.cache_resource
def init_connection():
   
    try:
        #client=pymongo.MongoClient("mongodb+srv://shubhamsrivastava:hzQ2IckGfmoJb4XS@emailreader.elzbauk.mongodb.net/")
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
#collection_test = db["test"]
collection_usersdetail = db['Users']
collection_searchwords= db['Searchwords']

def extract():
    query = {}
    st.write("Hello")
    results = collection_usersdetail.find(query)
    for result in results:
        emailid = result['emailid']
        passwordid = result['password']
        imap_server_id = result['imapserver']
        if emailid:
            input_extract(passwordid, imap_server_id, emailid)
            


def input_extract(passwordid, imap_server_id, emailid):
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
                            "subject":message["subject"], "description":content, "designations":designation,"emails":emails, "remark":remarks , "status":"unchecked", "info":""}
                            collection_clients.insert_one(new_document)
                            status = "Emails inserted successfully into Database" 

                    else: 
                            count+=1
                    if (count>0):
                            status= "Inbox is already updated"

        except imaplib.IMAP4.error:
                    status = "Login failed. Please enter correct credentials."

        # Update the corresponding document in 'collection_searchwords'
        search_query = {"emailid": emailid}
        search_update = {"$set": {"inbox": status}}  # Update the 'inbox' field with the status
        collection_usersdetail.update_one(search_query, search_update)
        #st.sidebar.write(status)

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
                            "subject":message["subject"], "description":content, "designations":designation,"emails":emails, "remark":remarks , "status":"unchecked", "info":""}
                            collection_clients.insert_one(new_document)
                            status = "Spam inserted successfully into Database" 

                    else: 
                            count+=1
                if (count>0):
                            status= "Spam is already updated"

        except imaplib.IMAP4.error:
                    status = "Spam could not be extracted."

        search_query = {"emailid": emailid}
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%H:%M:%S")
        search_update = {"$set": {"spam": status, "lastupdated":formatted_time}}  # Update the 'inbox' field with the status
        collection_usersdetail.update_one(search_query, search_update)
        # st.sidebar.write(status)

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


# Load configuration from YAML file
with open('./.streamlit/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Initialize the authenticator
authenticator = Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

col1, col2 = st.columns(2)
name, authentication_status, username = authenticator.login('Login', 'main')
if authentication_status:
    with col1:
        authenticator.logout('Logout', 'main')
        
    with col2:
        st.markdown(f'Welcome - <span style="color: orange;">*{name}*</span>', unsafe_allow_html=True)

    homepage.main()

elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')





if __name__=='__main__':
    current_time = datetime.datetime.now().time()
    target_time_start = datetime.time(14, 0)
    target_time_end = datetime.time(15, 0)
    if target_time_start <= current_time < target_time_end:
        t1 = threading.Thread(target=extract)
        t1.start()
        t1.join()




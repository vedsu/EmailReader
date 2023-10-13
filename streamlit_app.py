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
import datetime
#import home
import homepagelast5
st.subheader("Welcome to Email Reader")
#Database connections
@st.cache_resource
def init_connection():
   
    try:
        
        # db_username = st.secrets.db_username
        # db_password = st.secrets.db_password

        # mongo_uri_template = "mongodb+srv://{username}:{password}@emailreader.elzbauk.mongodb.net/"
        # mongo_uri = mongo_uri_template.format(username=db_username, password=db_password)

        # client = pymongo.MongoClient(mongo_uri)
        client=pymongo.MongoClient("mongodb+srv://Vedsu:CVxB6F2N700cQ0qu@cluster0.thbmwqi.mongodb.net/"

        # client = pymongo.MongoClient("mongodb://localhost:27017")
        
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

    homepagelast5.main()

elif authentication_status == False:

    st.error('Username/password is incorrect')

elif authentication_status == None:

    st.warning('Please enter your username and password')




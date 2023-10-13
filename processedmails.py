import streamlit as st
import pymongo
import math
import time

# Database connections
@st.cache_resource
def init_connection():
   
    try:
        # db_username = st.secrets.db_username
        # db_password = st.secrets.db_password

        # mongo_uri_template = "mongodb+srv://{username}:{password}@emailreader.elzbauk.mongodb.net/"
        # mongo_uri = mongo_uri_template.format(username=db_username, password=db_password)

        # client = pymongo.MongoClient(mongo_uri)
        client = pymongo.MongoClient("mongodb://localhost:27017")

        return client
    
    except:
       
        st.write("Connection Could not be Established with database")# Database

client = init_connection()

db= client['EmailDatabase']

collection_clients = db["Emails"]

collection_usersdetail = db['Users']

collection_searchwords= db['Searchwords']



if 'query_key' not in st.session_state:

    st.session_state.query_key = {}

if 'page_size' not in st.session_state:
    
    st.session_state.page_size = False

if 'read_checkbox_key' not in st.session_state:
    
    st.session_state.read_checkbox_key = None



def state_callback():
    
    st.session_state.page_size = True

def input_callback(search_value):
        
    st.session_state.query_key = {"$text": {"$search": search_value}}

def radio_callback(item):
    st.session_state.query_key = {"$text": {"$search": item}}

def date_callback(selected_date):
    st.session_state.query_key = {"date": selected_date.strftime("%Y-%m-%d")}

def reload_function():
      st.session_state.query_key = {}







item=""
read_mail=0
def main():
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Processed Mails")  
    with col2:
        st.button("Reload", on_click=reload_function )    
    # Values to store query results, total number of mails and unchecked mails

    total_mail=0

    menu = st.columns((4, 1, 1))
    
    
    with menu[0]:
        batch_size = st.selectbox("Page Size", options=[5, 10, 25, 50, 100], on_change=state_callback)

        
        
    
    #     st.markdown(f"Page **{current_page}** of **{total_pages}** ")
    # skip_count = (current_page - 1) * batch_size if current_page>1 else 0

    with menu[1]:
        # User input for pagination
        page_number = st.number_input("Page number:", min_value=1, value=1)
        
        # Calculate the start index for pagination
        start_index = (page_number - 1) * batch_size
    
     # Adding a search bar
    search_value = st.sidebar.text_input("Search:", None)
    
    #input_search_button = 
    st.sidebar.button("Search:", on_click=input_callback,args=(search_value, ))
    
    # st.write(st.session_state.date_input_key)
    # st.write(st.session_state.read_item_key)

    
    st.sidebar.write("----------------------------------")
    
    # Creating a date search
    selected_date = st.sidebar.date_input("Select a Date")
    
    #date_search_button = 
    st.sidebar.button("Date Search", on_click=date_callback, args=(selected_date, ))
    
        
    
    # if st.session_state.date_input_key is True:
        
        
    #     query = {"date": selected_date.strftime("%d %b %Y")}
    
    # if st.session_state.text_input_key is True:
        
    #     query = {"$text": {"$search": search_value}}
    

    


    st.sidebar.write("----------------------------------")

    # Query to extract data from the "Searchwords" collection
    search_words_data = collection_searchwords.find({}, {"_id": 0, "keyword": 1})

    # Extract "keyword" values and store them in a list
    search_words_list = [item["keyword"] for item in search_words_data]
    
    # List of predefined items
    predefined_items = search_words_list
    
    # Add a custom item in the sidebar
    search_word = st.sidebar.text_input("You can create or remove custom search words")
    
    if st.sidebar.button("Create"):
        
        collection_searchwords.insert_one({"keyword": search_word})
        
        st.sidebar.write("search word created")
        
        time.sleep(1)  # Introduce a 1-second delay
        
        st.experimental_rerun()
    
    if st.sidebar.button("Remove"):
        
        try:
        
            # Delete the document with the specified keyword
            collection_searchwords.delete_one({"keyword": search_word})
            
            st.sidebar.write("search word removed")
            
        except:
            
            st.sidebar.write("search word doesnot exists")
        
        time.sleep(1)  # Introduce a 1-second delay
        
        st.experimental_rerun()
        
    st.sidebar.write("----------------------------------")
    

    # item_search = st.sidebar.button(item)
    item =  st.sidebar.radio("Select an item:", predefined_items,)
    
    st.sidebar.button("Search", on_click=radio_callback, args=(item, ))

    
    total_mail = collection_clients.count_documents(st.session_state.query_key)
    
    count_results = collection_clients.find(st.session_state.query_key)
    
    read_mail=0
    
    for docs in count_results:
    
        if docs.get("status")!= 'unchecked':  # If status is False (unread)
    
                    read_mail += 1
    
    
    st.write("Total Records:", total_mail)
    
    st.write("Processed Mails:",read_mail)
    
    st.write("------------------------------------------")
    
    
    display(batch_size, start_index)

st.cache_data
def display( batch_size, start_index):
    
# Searching documents using query

    # search_results = collection_clients.find(st.session_state.query_key).sort("date", pymongo.DESCENDING).skip(start_index).limit(batch_size)
    
    pipeline = [
    {"$match": st.session_state.query_key},  # Match documents based on your query condition
    # Add a match stage to filter by "status" field
    {"$match": {"status": "checked"}},
    {"$skip": start_index},
    {"$limit": (start_index+batch_size)},
    {"$sort": {"date": 1}},
    ]

    search_results = collection_clients.aggregate(pipeline)
    
    
    # Get the number of search results
    with st.container():    
    
        #iterating over individual documents extracted through the query
        for doc in search_results:
            col1, col2 = st.columns(2)
            # if doc.get("status")!='unchecked':
            with st.container():
                    with col1:
                        st.write("Date:", doc.get("date"))
                        st.write("Reciever:", doc.get("reciever"))
                        st.write("Sender:", doc.get("sender"))
                        st.write("Subject:", doc.get("subject"))
                        st.write("Emails:", doc.get("emails"))
                        st.write("Job Titles:", doc.get("jobtitle"))
                        st.write("Remarks:", doc.get('remark'))
            
                        # Checkbox to mark email as Read
                        
                        st.session_state.read_checkbox_key = f"read_checkbox_{doc['_id']}"
                        
                        un_read = st.checkbox("Mark as Unread", key=st.session_state.read_checkbox_key) 

                        if un_read:
                                
                                collection_clients.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"status": "unchecked"}})
                                st.success("Unmarked successfully!")
                                time.sleep(1)
                                st.experimental_rerun()   
                    
                    with col2:
                        with st.expander(" View Details"):
        
                            st.write("Content:", doc.get("description"))
                        
                            additional_info = st.text_area("Additional Information:",doc.get("comments"),height=100,key=f"additional_info_{doc['_id']}")
                            update_form_key = f"update_form_{doc['_id']}"
            
                            
                        
                            update_button = st.button(label="Submit", key= update_form_key)
                            
                            if update_button:
                            
                                new_info = additional_info
                            
                                # Update the additional information field in the MongoDB document
                                collection_clients.update_one(
                                {"_id": doc["_id"]},
                                {"$set": {"comments": new_info}})
                                st.success("Additional information updated successfully!")
                                time.sleep(1)
                                st.experimental_rerun()
                            
                        
                        delete_button_key = f"delete_button_{doc['_id']}"
                        
                        delete_button = st.button("Delete", key= delete_button_key)
                        
                        if delete_button:
                            result = collection_clients.delete_one({"_id": doc["_id"]})
                            
                            if result.deleted_count > 0:
                                st.success("Document deleted successfully.")
                            
                            else:
                                st.error("Failed to delete document.")
                            
                            time.sleep(1)
                            st.experimental_rerun()

            st.write("--------------------------------------------------------------------------")
    

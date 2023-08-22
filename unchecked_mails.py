import streamlit as st
import pymongo
import math
import time


# Database connections
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
        st.write("Connection Could not be Established with database")# Database
client = init_connection()
db= client['EmailDatabase']
collection_clients = db["Emails"]
collection_usersdetail = db['Users']
collection_searchwords= db['Searchwords']



unread_mail=0
def main():
    
    st.subheader("Fresh Mails")    
    if 'load_query' not in st.session_state:
        st.session_state['load_query'] = {}
    # Values to store query results, total number of mails and unchecked mails
    query={}
    total_mail=0
    
    # Adding a search bar
    search_value = st.sidebar.text_input("Search:", "")
    input_search = st.sidebar.button("Search")
    if input_search:
        #query = {"$text": {"$search": search_value}}
        query = {
    "$or": [
        {"subject": {"$regex": search_value, "$options": "i"}},
        {"description": {"$regex": search_value, "$options": "i"}}
    ]
}

        st.session_state['load_query']= query
    #    search(query)
    st.sidebar.write("----------------------------------")
    

# Creating a date search
    selected_date = st.sidebar.date_input("Select a Date")
    date_search = st.sidebar.button("Date Search")
    if date_search:
        query = {"date": selected_date.strftime("%d %b %Y")}
        st.session_state['load_query']= query

    #    search(query)
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
            time.sleep(1)  # Introduce a 1-second delay
        except:
            st.sidebar.write("search word doesnot exists")
        time.sleep(1)  # Introduce a 1-second delay
        st.experimental_rerun()
        
    st.sidebar.write("----------------------------------")
    # Display predefined items in the sidebar as clickable buttons
    for index, item in enumerate(predefined_items):
       button_key = f"button_{index}"  # Generate a unique key for each button
       if st.sidebar.button(item, key=button_key): 
            # Create the query using $text operator
            query = {"$or": [{"subject": {"$regex": item, "$options": "i"}},
        {"description": {"$regex": item, "$options": "i"}}]}
            st.session_state['load_query']= query
    

    total_mail = collection_clients.count_documents(query)
    count_results = collection_clients.find(query)
    unread_mail=0
    for docs in count_results:
        if docs.get("status")== 'unchecked':  # If status is False (unread)
                    unread_mail += 1
    st.write("Total Records:", total_mail)
    st.write("Fresh Mails:",unread_mail)
    st.write("------------------------------------------")
    menu = st.columns((4, 1, 1))
    with menu[2]:
        batch_size = st.selectbox("Page Size", options=[5, 10, 25, 50, 100])
    with menu[1]:
        total_pages = (
            math.ceil(unread_mail / batch_size) if math.ceil(unread_mail / batch_size) > 0 else 1
        )
        current_page = st.number_input(
            "Page", min_value=1, max_value=total_pages, step=1
        )
    with menu[0]:
        st.markdown(f"Page **{current_page}** of **{total_pages}** ")
    skip_count = (current_page - 1) * batch_size if current_page>1 else 0
    display(query, batch_size, skip_count)

#@st.cache_resource(experimental_allow_widgets=True)
st.cache_data
def display(query,batch_size, skip_count):
    
# Searching documents using query

    search_results = collection_clients.find(query).sort("date", pymongo.DESCENDING).skip(skip_count).limit(batch_size)
    
    # Get the number of search results
    with st.container():    
        #terating over individual documents extracted through the query
        for doc in search_results:
            if doc.get("status")=='unchecked':
                st.write("Date:", doc.get("date"))
                st.write("Reciever:", doc.get("reciever"))
                st.write("Sender:", doc.get("sender"))
                st.write("Subject:", doc.get("subject"))
                st.write("Emails:", doc.get("emails"))
                st.write("Job Titles:", doc.get("designations"))
                st.write("Remarks:", doc.get('remark'))
                with st.expander(" View Details"):
                    st.write("Content:", doc.get("description"))
                    
                    additional_info = st.text_area("Additional Information:",doc.get("info"),height=100,key=f"additional_info_{doc['_id']}")
                    # option=["Unchecked", "checked"]
                    
                    # Checkbox to mark email as Read
                    update_button_key = f"update_button_{doc['_id']}"
                    #load = st.button("Update",update_button_key)
                    update_button = st.button("Update", key=update_button_key)
                    if update_button:
                        new_info = additional_info
                    
                    # Update the additional information field in the MongoDB document
                        collection_clients.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"info": new_info}})
                        st.success("Additional information updated successfully!")
                        st.experimental_rerun()
                    
                    read_checkbox_key = f"read_checkbox_{doc['_id']}"
                    is_read = st.checkbox("Mark as Read", key=read_checkbox_key)    

                    if is_read:
                        
                        collection_clients.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"status": "checked"}})
                        st.success("Status updated successfully!")
                        st.experimental_rerun()
                    
                    
                    delete_button_key = f"delete_button_{doc['_id']}"
                    delete_button = st.button("Delete", key= delete_button_key)
                    if delete_button:
                        result = collection_clients.delete_one({"_id": doc["_id"]})
                        if result.deleted_count > 0:
                            st.success("Document deleted successfully.")
                        else:
                            st.error("Failed to delete document.")
                        st.experimental_rerun()

                st.write("--------------------------------------------------------------------------")
    

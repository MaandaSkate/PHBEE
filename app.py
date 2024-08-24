import os
import streamlit as st
import datetime
import random
from fpdf import FPDF
from google.cloud import dialogflowcx_v3 as dialogflow_cx, firestore
from google.oauth2 import service_account
import json
import base64

# Set the page configuration
st.set_page_config(page_title="PHBEE", page_icon="📚", layout="centered")

# Hide Streamlit style elements
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Load credentials from Streamlit secrets
credentials_info = st.secrets["google_service_account_key"]
credentials = service_account.Credentials.from_service_account_info(credentials_info)

# Function to initialize Dialogflow client
def initialize_dialogflow_client(credentials):
    client = dialogflow_cx.SessionsClient(credentials=credentials)
    return client

# Function to initialize Firestore client
def initialize_firestore_client(credentials, project_id):
    client = firestore.Client(credentials=credentials, project=project_id)
    return client

# Define the Dialogflow parameters
project_id = "phoeb-426309"
agent_id = "016dc67d-53e9-49c5-acbf-dcb3069154f9"
session_id = "123456789"
language_code = "en"

# Initialize clients
client = initialize_dialogflow_client(credentials)
db = initialize_firestore_client(credentials, project_id)

# Home Page Display Function
def display_home_page():
    col1, col2 = st.columns([2, 1])
    with col1:
        st.title('PHBEE :rocket:')
        st.header("AI-Powered Educational Assistant 🏠")
        st.divider()
        st.header("About PHBEE :memo:")
        st.markdown('''
        ####
        PHBEE is an AI-powered educational assistant designed to support teachers, school administrators, and educational professionals in South Africa by automating the creation of educational materials.

        PHBEE offers tools to generate lesson plans, assessments, worksheets, quizzes, and more. It aligns with both CAPS and IEB standards for grades R to 12, providing a comprehensive solution to streamline educational tasks and enhance teaching efficiency.

        Whether you need help with creating curriculum materials, tracking student progress, or generating classroom resources, PHBEE is here to assist you in achieving educational excellence.
        ''')

        # Button to navigate to the Task Generator
        if st.button("Explore Educational Tasks"):
            st.experimental_set_query_params(page="Task Generator")
            st.experimental_rerun()  # Force a rerun to apply the query parameters

        # Add the educational task-focused YouTube video
        st.header("How PHBEE Helps You")
        st.video("https://youtu.be/HlaGFOQ-aLk")
        
    with col2:
        st.image("image/PHBEE LOGO FINAL.png")  # Update with the correct path to your image

# Utility Functions
def img_to_base64(image_path):
    try:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"The file {image_path} does not exist.")
        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
        return base64.b64encode(img_data).decode('utf-8')
    except FileNotFoundError as e:
        st.error(f"Error: {str(e)}")
        return base64.b64encode(b'').decode('utf-8')
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        return base64.b64encode(b'').decode('utf-8')

def generate_session_id():
    return f"session_{datetime.datetime.now().timestamp()}"

def create_pdf(task_description, response_text, file_name, task_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"{task_type.capitalize()} / Assessment", ln=True, align='C')
    pdf.cell(200, 10, txt=datetime.datetime.now().strftime("%Y-%m-%d"), ln=True, align='C')
    pdf.ln(10)

    pdf.set_fill_color(200, 220, 255)  # Light blue background
    pdf.rect(x=10, y=30, w=190, h=pdf.get_y() + 10, style='F')

    pdf.set_xy(10, 40)
    pdf.multi_cell(0, 10, txt=f"Task Description:\n{task_description}\n\nResponse:\n{response_text}")

    if task_type != "lesson plan":  # Add memo for all tasks except lesson plan
        memo = create_memo(response_text)
        pdf.ln(10)
        pdf.set_xy(10, pdf.get_y())
        pdf.multi_cell(0, 10, txt=f"{memo}")

    pdf.output(file_name)

def detect_intent_text(client, project_id, agent_id, session_id, text, language_code="en"):
    session_path = f"projects/{project_id}/locations/global/agents/{agent_id}/sessions/{session_id}"
    text_input = dialogflow_cx.TextInput(text=text)
    query_input = dialogflow_cx.QueryInput(text=text_input, language_code=language_code)
    request = dialogflow_cx.DetectIntentRequest(session=session_path, query_input=query_input)
    response = client.detect_intent(request=request)
    return response.query_result.response_messages[0].text.text[0] if response.query_result.response_messages else "No response from Dialogflow."

def display_message(sender, message):
    if sender == "user":
        st.markdown(f'''
            <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-end;">
                <div style="background-color: #f0f0f0; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">
                    {message}
                </div>
                <img src="data:image/png;base64,{img_to_base64('image/PHBEE USER ICON.png')}" 
                     style="width: 40px; height: 40px; border-radius: 50%; margin-left: 10px;">
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
            <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-start;">
                <img src="data:image/png;base64,{img_to_base64('image/PHBEE LOGO FINAL.png')}" 
                     style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px;">
                <div style="background-color: #DCF8C6; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">
                    {message}
                </div>
            </div>
            ''', unsafe_allow_html=True)

def create_memo(response_text):
    memo = "\nMemo:\n"
    questions = response_text.split("\n")
    for question in questions:
        if "Answer:" in question:
            memo += question + "\n"
    return memo

# Chatbot Function
def chatbot():
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = generate_session_id()

    st.title("Chat with PHBEE 🐝")
    st.markdown("<h2 style='text-align: center;'>Welcome to the PHBEE Chatbot!</h2>", unsafe_allow_html=True)

    if not st.session_state['chat_history']:
        display_message("PHBEE", "Greetings! I am PHBEE, your Educational AI assistant! How can I assist you today?")

    user_input = st.text_input("Type your message here:", key="input", placeholder="Ask me anything...")
    if st.button("Send"):
        if user_input:
            with st.spinner('Processing...'):
                response = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], user_input, "en")
            display_message("user", user_input)
            display_message("PHBEE", response)

            st.session_state['chat_history'].append({"sender": "user", "message": user_input})
            st.session_state['chat_history'].append({"sender": "PHBEE", "message": response})

    if st.button("Clear Chat"):
        st.session_state['chat_history'] = []

    for chat in st.session_state['chat_history']:
        if isinstance(chat, dict) and 'sender' in chat and 'message' in chat:
            display_message(chat['sender'], chat['message'])
        else:
            st.error("Chat history contains invalid data.")

# Task Generator Function
def generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week):
    if task_type == "lesson plan":
        return (
            f"Create a detailed {task_type} for the {subject} subject, targeting grade {grade} students under the "
            f"{curriculum} curriculum. The lesson plan should cover term {num_questions_or_term}, week {total_marks_or_week}."
        )
    else:
        return (
            f"Generate a {task_type} for the {subject} subject, targeting grade {grade} students under the "
            f"{curriculum} curriculum. The {task_type} should consist of {num_questions_or_term} questions, "
            f"with a total of {total_marks_or_week} marks."
        )

def task_generator():
    st.title("PHBEE Task Generator :pencil:")
    task_type = st.selectbox("Select Task Type", ["worksheet", "quiz", "class exercise", "homework", "lesson plan"])
    subject = st.selectbox("Select Subject", ["Mathematics", "Physical Science", "Life Science", "English", "History", "Geography"])
    grade = st.selectbox("Select Grade", ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
    curriculum = st.selectbox("Select Curriculum", ["CAPS", "IEB"])
    
    if task_type == "lesson plan":
        num_questions_or_term = st.text_input("Term", key="term", placeholder="e.g., 1")
        total_marks_or_week = st.text_input("Week", key="week", placeholder="e.g., 1")
    else:
        num_questions_or_term = st.slider("Number of Questions", min_value=1, max_value=100, value=10)
        total_marks_or_week = st.slider("Total Marks", min_value=1, max_value=300, value=100)

    task_description = generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week)

    if st.button("Generate Task"):
        if task_description:
            with st.spinner("Generating..."):
                response_text = detect_intent_text(client, project_id, agent_id, generate_session_id(), task_description, language_code="en")
                file_name = f"{task_type}_{subject}_grade_{grade}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                create_pdf(task_description, response_text, file_name, task_type)
                with open(file_name, "rb") as file:
                    base64_pdf = base64.b64encode(file.read()).decode('utf-8')
                st.success("Task generated successfully!")
                st.download_button(
                    label="Download Task PDF",
                    data=base64_pdf,
                    file_name=file_name,
                    mime="application/pdf"
                )
        else:
            st.warning("Please fill in all the required fields to generate a task.")

# Main App Function
def main():
    query_params = st.experimental_get_query_params()
    page = query_params.get("page", ["Home"])[0]

    tabs = {
        "Home": display_home_page,
        "Task Generator": task_generator,
        "Chatbot": chatbot
    }

    st.sidebar.title("PHBEE")
    selection = st.sidebar.radio("Navigate", list(tabs.keys()))

    if selection == "Home" or page == "Home":
        display_home_page()
    elif selection == "Task Generator" or page == "Task Generator":
        task_generator()
    elif selection == "Chatbot" or page == "Chatbot":
        chatbot()

if __name__ == "__main__":
    main()











	












import os
import streamlit as st
import datetime
import random
import base64
from fpdf import FPDF
from google.cloud import dialogflowcx_v3beta1 as dialogflow_cx
from google.oauth2 import service_account
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Load credentials from Streamlit secrets
credentials_info = st.secrets["google_service_account_key"]
credentials = service_account.Credentials.from_service_account_info(credentials_info)

# Set the page configuration
st.set_page_config(page_title="PHBEE", page_icon="📚", layout="centered")

# Initialize Dialogflow client
def initialize_dialogflow_client(key_path):
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = dialogflow_cx.SessionsClient(credentials=credentials)
    return client

# Create a Firestore client with explicit project ID
def initialize_firestore_client(key_path, project_id):
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = firestore.Client(credentials=credentials, project=project_id)
    return client

# Initialize clients

project_id = "phoeb-426309"
agent_id = "016dc67d-53e9-49c5-acbf-dcb3069154f9"
language_code = "en"




# Generate a unique session ID for each user session
def generate_session_id():
    return f"session_{datetime.datetime.now().timestamp()}"

# Function to create PDF
def create_pdf(task_description, response_text, file_name, task_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"{task_type.capitalize()} / Assessment", ln=True, align='C')
    pdf.cell(200, 10, txt=datetime.datetime.now().strftime("%Y-%m-%d"), ln=True, align='C')
    pdf.ln(10)

    # Adding a border and background color
    pdf.set_fill_color(200, 220, 255)  # Light blue background
    pdf.rect(x=10, y=30, w=190, h=pdf.get_y() + 10, style='F')

    # Adding text with a slight indention
    pdf.set_xy(10, 40)
    pdf.multi_cell(0, 10, txt=f"Task Description:\n{task_description}\n\nResponse:\n{response_text}")

    if task_type != "lesson plan":  # Add memo for all tasks except lesson plan
        memo = create_memo(response_text)
        pdf.ln(10)
        pdf.set_xy(10, pdf.get_y())
        pdf.multi_cell(0, 10, txt=f"{memo}")

    pdf.output(file_name)

# Function to detect intent using Dialogflow CX
def detect_intent_text(client, project_id, agent_id, session_id, text, language_code="en"):
    session_path = f"projects/{project_id}/locations/global/agents/{agent_id}/sessions/{session_id}"
    text_input = dialogflow_cx.TextInput(text=text)
    query_input = dialogflow_cx.QueryInput(text=text_input, language_code=language_code)
    request = dialogflow_cx.DetectIntentRequest(session=session_path, query_input=query_input)
    response = client.detect_intent(request=request)
    return response.query_result.response_messages[0].text.text[0] if response.query_result.response_messages else "No response from Dialogflow."



# Function to convert image to base64
def img_to_base64(image_path):
    if not os.path.exists(image_path):
        st.error(f"Image file not found: {image_path}")
        return ""
    with open(image_path, "rb") as img_file:
        img_data = img_file.read()
    return base64.b64encode(img_data).decode('utf-8')

# Function to display messages with appropriate styling
def display_message(sender, message):
    if sender == "user":
        st.markdown(
            f'<div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-end;">'
            f'<div style="background-color: #f0f0f0; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">'
            f'{message}</div>'
            f'<img src="data:image/png;base64,{img_to_base64("/content/PHBEE USER ICON.png")}" '
            f'style="width: 40px; height: 40px; border-radius: 50%; margin-left: 10px;"></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-start;">'
            f'<img src="data:image/png;base64,{img_to_base64("/content/PHBEE LOGO FINAL.png")}" '
            f'style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px;">'
            f'<div style="background-color: #DCF8C6; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">'
            f'{message}</div></div>',
            unsafe_allow_html=True
        )



# Main chatbot function
def chatbot():
    # Initialize session state for the chatbot
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = generate_session_id()

    st.title("Chat with PHBEE 🐝")
    st.markdown("<h2 style='text-align: center;'>Welcome to the PHBEE Chatbot!</h2>", unsafe_allow_html=True)

    # Display introductory message if chat history is empty
    if not st.session_state['chat_history']:
        display_message("PHBEE", "Greetings! I am PHBEE, your Educational AI assistant! How can I assist you today?")

    user_input = st.text_input("Type your message here:", key="input", placeholder="Ask me anything...")
    if st.button("Send"):
        if user_input:
            with st.spinner('Processing...'):
                response = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], user_input, "en")
            display_message("user", user_input)
            display_message("PHBEE", response)

            # Update chat history
            st.session_state['chat_history'].append({"sender": "user", "message": user_input})
            st.session_state['chat_history'].append({"sender": "PHBEE", "message": response})

    # Button to clear the chat
    if st.button("Clear Chat"):
        st.session_state['chat_history'] = []  # Clear chat history

    # Display chat history
    for chat in st.session_state['chat_history']:
        if isinstance(chat, dict) and 'sender' in chat and 'message' in chat:
            display_message(chat['sender'], chat['message'])
        else:
            st.error("Chat history contains invalid data.")

def create_memo(response_text):
    memo = "\nMemo:\n"
    questions = response_text.split("\n")
    for question in questions:
        if "Answer:" in question:
            memo += question + "\n"
    return memo

# Function to generate a task description
def generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week):
    if task_type == "lesson plan":
        return (
            f"Create a detailed {task_type} for the {subject} subject, targeting grade {grade} students under the "
            f"{curriculum} curriculum. The lesson plan should cover term {num_questions_or_term} and week {total_marks_or_week}."
        )
    else:
        return (
            f"Create a detailed {task_type} for the {subject} subject, targeting grade {grade} students under the "
            f"{curriculum} curriculum. The task should include {num_questions_or_term} questions, each with 4 options, "
            f"and the total marks should sum up to {total_marks_or_week}."
        )

# Main application logic
def main():
    # Hide Streamlit style elements
    hide_st_style = """
                    <style>
                    #MainMenu {visibility: hidden;}
                    footer {visibility: hidden;}
                    header {visibility: hidden;}
                    </style>
                    """
    st.markdown(hide_st_style, unsafe_allow_html=True)

    st.sidebar.title("PHBEE Educational Tools")
    menu = ["Chatbot", "Task Generator"]
    choice = st.sidebar.selectbox("Select an Option", menu)

    if choice == "Chatbot":
        chatbot()
    elif choice == "Task Generator":
        st.subheader("Generate Educational Tasks")
        task_type = st.selectbox("Select Task Type", ["Assessment", "Project", "Test", "Lesson Plan", "Exam"])
        subject = st.text_input("Subject")
        grade = st.selectbox("Grade", ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        curriculum = st.radio("Curriculum", ["CAPS", "IEB"])

        if task_type == "Lesson Plan":
            term = st.slider("Term", 1, 4)
            week = st.slider("Week", 1, 10)
            num_questions_or_term = term
            total_marks_or_week = week
        else:
            num_questions = st.slider("Number of Questions", 1, 100)
            total_marks = st.slider("Total Marks", 1, 300)
            num_questions_or_term = num_questions
            total_marks_or_week = total_marks

        if st.button("Generate"):
            task_description = generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week)
            response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], task_description)

            # Create PDF
            pdf_file_name = f"{task_type}_for_{subject}_Grade_{grade}.pdf"
            create_pdf(task_description, response_text, pdf_file_name, task_type)

            # Display the generated task and response
            st.markdown(f"**Task Description:**\n\n{task_description}")
            st.markdown(f"**Generated Task:**\n\n{response_text}")

            # Display download buttons with colors aligned to the logo
            pdf_button_color = "#FFCC00"  # A color matching your logo
            st.markdown(f"""
                <style>
                .download-button {{
                    background-color: {pdf_button_color};
                    color: white;
                    padding: 10px;
                    text-align: center;
                    font-size: 16px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border: none;
                    cursor: pointer;
                    display: inline-block;
                }}
                </style>
                <a href="data:application/octet-stream;base64,{base64.b64encode(open(pdf_file_name, 'rb').read()).decode()}" download="{pdf_file_name}">
                <div class="download-button">📄 Download {task_type} PDF</div></a>
            """, unsafe_allow_html=True)

            if task_type != "lesson plan":
                memo = create_memo(response_text)
                st.markdown(f"**Memo:**\n\n{memo}")

# Run the main function
if __name__ == '__main__':
    main()






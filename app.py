import os
import streamlit as st
import datetime
import random
from fpdf import FPDF
from google.cloud import dialogflowcx_v3beta1 as dialogflow_cx
from google.oauth2 import service_account
from google.cloud import firestore
import gspread
from google.oauth2.service_account import Credentials
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
# Define the scope for Google Sheets access
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Get credentials from Streamlit secrets
credentials_info = st.secrets["google_service_account_key"]
creds = Credentials.from_service_account_info(credentials_info, scopes=scope)

# Authorize gspread client with credentials
client = gspread.authorize(creds)

# Open your Google Sheet using the URL
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1WydXwqoXkDq4BTwMSJt7As8cUAafJZTaOUqADIp13sg/edit?usp=sharing"
sheet = client.open_by_url(spreadsheet_url).worksheet("PHBEE - MVP FEEDBACK")

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

# Helper functions
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

    pdf.set_fill_color(200, 220, 255)
    pdf.rect(x=10, y=30, w=190, h=pdf.get_y() + 10, style='F')

    pdf.set_xy(10, 40)
    pdf.multi_cell(0, 10, txt=f"Task Description:\n{task_description}\n\nResponse:\n{response_text}")

    if task_type != "lesson plan":
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

# Chatbot logic
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

# Task Generator logic
def task_generator():
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
        num_questions = st.slider("Number of Questions", 1, 10)
        total_marks = st.slider("Total Marks", 1, 100)
        num_questions_or_term = num_questions
        total_marks_or_week = total_marks

    if st.button("Generate Task"):
        task_description = generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week)
        response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], task_description)
        file_name = f"{task_type.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        create_pdf(task_description, response_text, file_name, task_type)
        st.success(f"Task generated and saved as {file_name}.")
        st.download_button(label="Download PDF", data=open(file_name, "rb").read(), file_name=file_name, mime='application/pdf')

# Free Task logic
def free_task():
    st.subheader("Free Task")
    st.markdown("Generate a custom PDF based on your request.")

    request_text = st.text_area("Enter your request")
    if st.button("Generate Free Task"):
        if request_text.strip():
            with st.spinner("Generating..."):
                response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], request_text)
                
                pdf_file_name = f"Free_Task_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                create_pdf(request_text, response_text, pdf_file_name, "Free Task")

                st.markdown(f"**Generated PDF:** {request_text}")
                st.markdown(f"**Response:** {response_text}")

                st.markdown(f"""
                    <a href="data:application/octet-stream;base64,{base64.b64encode(open(pdf_file_name, 'rb').read()).decode()}" download="{pdf_file_name}">
                    <div style="background-color: #FFCC00; color: white; padding: 10px; border-radius: 5px; text-align: center; max-width: 200px;">
                        Download {pdf_file_name}
                    </div>
                    </a>
                """, unsafe_allow_html=True)
        else:
            st.error("Please enter a valid request.")

# All Classwork logic
def all_classwork():
    st.subheader("All Classwork")
    st.markdown("Generate a variety of classwork-related tasks.")

    task_type = st.selectbox("Select classwork type", ["Homework", "Worksheet", "Class Exercise", "Quiz", "Teaching Admin Task"])
    subject = st.text_input("Enter subject name", placeholder="e.g., English, Math")
    grade = st.number_input("Select grade", min_value=1, max_value=12, step=1)
    curriculum = st.radio("Select curriculum", ["CAPS", "IEB"])

    num_questions = st.slider("Number of questions", min_value=1, max_value=10)
    total_marks = st.slider("Total marks", min_value=1, max_value=100)

    if st.button("Generate Classwork"):
        if subject and grade and curriculum:
            task_description = generate_task_description(task_type, subject, grade, curriculum, num_questions, total_marks)
            with st.spinner("Generating..."):
                response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], task_description)

            st.markdown(f"**Generated {task_type}:** {task_description}")
            st.markdown(f"**Response:** {response_text}")
            file_name = f"{task_type.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_file_name = f"Free_Task_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            create_pdf(task_description, response_text, pdf_file_name, task_type)

            st.markdown(f"""
                <a href="data:application/octet-stream;base64,{base64.b64encode(open(pdf_file_name, 'rb').read()).decode()}" download="{pdf_file_name}">
                <div style="background-color: #FFCC00; color: white; padding: 10px; border-radius: 5px; text-align: center; max-width: 200px;">
                    Download {pdf_file_name}
                </div>
                </a>
            """, unsafe_allow_html=True)
        else:
            st.error("Please provide all required inputs.")


# Function to submit feedback
def submit_feedback(rating, best_feature, feedback):
    sheet.append_row([rating, best_feature, feedback])
    st.success("Thank you for your feedback!")

# Feedback form
def feedback_form():
    st.subheader("Rate PHBEE the Educational Bot")
    
    # 5-star rating input
    rating = st.slider("How would you rate PHBEE?", 1, 5, value=5)
    
    # Best feature ranking input
    best_feature = st.selectbox("What is PHBEE's best feature?", 
                                ["Chatbot", "Task Generator", "All Classwork", "Free Task", "Others"])
    
    # General feedback input
    feedback = st.text_area("Any other feedback?")
    
    # Submit button
    if st.button("Submit Feedback"):
        submit_feedback(rating, best_feature, feedback)

# Add the feedback form to the main application

# Main application logic
def main():
    st.sidebar.title("PHBEE Educational AI")
    st.sidebar.image("image/PHBEE LOGO FINAL.png", use_column_width=True)

    page = st.sidebar.radio("Navigation", ["Home", "Chatbot", "Task Generator", "All Classwork", "Free Task", "Feedback"])
    
    if page == "Home":
        st.title('Welcome to PHBEE :rocket:')
        st.header("Your AI Powered Educational Chatbot 🏠")
        st.markdown('''
        ####
        PHBEE is an AI-powered educational chatbot designed to assist teachers, school administrators, and educational department workers in South Africa by automating the creation of educational materials.

        PHBEE is trained on both CAPS and IEB standards from grade R to 12. It can help create lesson plans, assessments, marking rubrics, tests, exams, and timetables. Additionally, it assists in creating school management plans, policies, and tracking student progress, ensuring effective communication between schools and parents.

        With PHBEE, you can develop curriculums, frameworks, policies, and procedures based on current regulations. The chatbot helps students with their homework, tasks, and understanding of subject concepts, all aligned with IEB and CAPS standards.
        ''')
        st.markdown("#### `Get Started Now!`, find the navigation arrow on the top left")
        st.video("https://www.youtube.com/watch?v=HlaGFOQ-aLk")
        st.image("image/PHBEE LOGO FINAL.png", use_column_width=True)


    elif page == "Chatbot":
        chatbot()

    elif page == "Task Generator":
        task_generator()

    elif page == "All Classwork":
        all_classwork()

    elif page == "Free Task":
        free_task()
	
    elif page == "Feedback":
        feedback_form()

if __name__ == "__main__":
    main()













	












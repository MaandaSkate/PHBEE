import os
import streamlit as st
import datetime
import random
from fpdf import FPDF
from google.cloud import dialogflowcx_v3beta1 as dialogflow_cx, firestore
from google.oauth2 import service_account
import json
import base64

# Hide Streamlit style elements
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""

st.markdown(hide_st_style, unsafe_allow_html=True)

# Define the path to the service account key file
key_path = 'PHBEECHATBOT.json'

# Function to initialize Dialogflow client
def initialize_dialogflow_client(key_path):
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = dialogflow_cx.SessionsClient(credentials=credentials)
    return client

# Function to initialize Firestore client
def initialize_firestore_client(key_path, project_id):
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = firestore.Client(credentials=credentials, project=project_id)
    return client

# Initialize clients if key_path exists
if not os.path.exists(key_path):
    st.error("Service account key file not found. Please check the path.")
else:
    client = initialize_dialogflow_client(key_path)
    project_id = "phoeb-426309"
    agent_id = "016dc67d-53e9-49c5-acbf-dcb3069154f9"
    language_code = "en"
    db = initialize_firestore_client(key_path, project_id)

def img_to_base64(image_path):
    try:
        # Ensure the image path is valid
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"The file {image_path} does not exist.")
        
        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
        return base64.b64encode(img_data).decode('utf-8')
    except FileNotFoundError as e:
        st.error(f"Error: {str(e)}")
        # Return a placeholder image if file is not found
        return base64.b64encode(b'').decode('utf-8')  # Placeholder for missing image
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        return base64.b64encode(b'').decode('utf-8')  # Placeholder for missing image

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
        st.markdown(f'<div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-end;">'
                    f'<div style="background-color: #f0f0f0; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">'
                    f'{message}</div>'
                    f'<img src="data:image/png;base64,{img_to_base64("assets/placeholder_user_icon.png")}" '
                    f'style="width: 40px; height: 40px; border-radius: 50%; margin-left: 10px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-start;">'
                    f'<img src="data:image/png;base64,{img_to_base64("assets/placeholder_logo.png")}" '
                    f'style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px;">'
                    f'<div style="background-color: #DCF8C6; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">'
                    f'{message}</div></div>', unsafe_allow_html=True)

def create_memo(response_text):
    memo = "\nMemo:\n"
    questions = response_text.split("\n")
    for question in questions:
        if "Answer:" in question:
            memo += question + "\n"
    return memo

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

def main():
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
            total_marks = st.slider("Total Marks", 1, 1000)
            num_questions_or_term = num_questions
            total_marks_or_week = total_marks

        if st.button("Generate Task"):
            task_description = generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week)
            response_text = "Here will be the generated content for the task."
            file_name = f"{task_type.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            create_pdf(task_description, response_text, file_name, task_type)
            st.success(f"Task generated and saved as {file_name}.")
            st.download_button(label="Download PDF", data=open(file_name, "rb").read(), file_name=file_name, mime='application/pdf')

if __name__ == "__main__":
    main()










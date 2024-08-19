import os
import base64
import streamlit as st
import datetime
from fpdf import FPDF
from google.cloud import dialogflowcx_v3beta1 as dialogflow_cx
from google.oauth2 import service_account

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

# Define the Dialogflow parameters
project_id = "phoeb-426309"
agent_id = "016dc67d-53e9-49c5-acbf-dcb3069154f9"
session_id = "123456789"
language_code = "en"

def img_to_base64(image_filename):
    # Replace with your image path or use placeholder
    image_path = os.path.join("assets", image_filename)  # Placeholder path
    with open(image_path, "rb") as img_file:
        img_data = img_file.read()
    return base64.b64encode(img_data).decode('utf-8')

def detect_intent_text(client, project_id, agent_id, session_id, text, language_code):
    session = f"projects/{project_id}/locations/global/agents/{agent_id}/sessions/{session_id}"
    text_input = dialogflow_cx.TextInput(text=text, language_code=language_code)
    query_input = dialogflow_cx.QueryInput(text=text_input)
    request = dialogflow_cx.DetectIntentRequest(session=session, query_input=query_input)
    response = client.detect_intent(request=request)
    return response.query_result.fulfillment_text

def create_pdf(task_description, response_text, pdf_file_name, task_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Task Type: {task_type}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.multi_cell(0, 10, txt=f"Task Description:\n{task_description}")
    pdf.ln(10)
    
    pdf.multi_cell(0, 10, txt=f"Response Text:\n{response_text}")
    
    pdf.output(pdf_file_name)

def create_memo(questions_and_answers):
    memo = ""
    for question, answer in questions_and_answers:
        memo += f"Q: {question}\nA: {answer}\n\n"
    return memo

def display_message(sender, message):
    # Placeholder icons for demonstration
    user_icon = "data:image/png;base64,{}"  # Replace with actual image base64
    logo_icon = "data:image/png;base64,{}"  # Replace with actual image base64
    
    if sender == "user":
        st.markdown(f'<div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-end;">'
                    f'<div style="background-color: #f0f0f0; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">'
                    f'{message}</div>'
                    f'<img src="{user_icon}" style="width: 40px; height: 40px; border-radius: 50%; margin-left: 10px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-start;">'
                    f'<img src="{logo_icon}" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px;">'
                    f'<div style="background-color: #DCF8C6; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px;">'
                    f'{message}</div></div>', unsafe_allow_html=True)

def generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week):
    if task_type == "Lesson Plan":
        return (f"Generate a lesson plan for the {subject} subject, targeting grade {grade} students. "
                f"The plan should cover term {num_questions_or_term} and week {total_marks_or_week}.")
    else:
        return (f"Generate a {task_type} for the {subject} subject, targeting grade {grade} students. "
                f"The task should include {num_questions_or_term} questions, each with 4 options, "
                f"and the total marks should sum up to {total_marks_or_week}.")

def main():
    st.sidebar.title("PHBEE Educational Tools")
    menu = ["Chatbot", "Task Generator"]
    choice = st.sidebar.selectbox("Select an Option", menu)

    if choice == "Chatbot":
        st.subheader("Chat with PHBEE")
        
        # Initialize Dialogflow client
        client = dialogflow_cx.SessionsClient(credentials=credentials)
        
        if 'messages' not in st.session_state:
            st.session_state['messages'] = []

        if 'session_id' not in st.session_state:
            st.session_state['session_id'] = session_id

        def send_message():
            user_message = st.text_input("You: ")
            if user_message:
                st.session_state['messages'].append({"sender": "user", "message": user_message})
                response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], user_message, language_code)
                st.session_state['messages'].append({"sender": "bot", "message": response_text})
                st.experimental_rerun()

        for msg in st.session_state['messages']:
            display_message(msg["sender"], msg["message"])

        st.button("Send", on_click=send_message)

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
            response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], task_description, language_code)

            # Create PDF
            pdf_file_name = f"{task_type}_for_{subject}_Grade_{grade}.pdf"
            create_pdf(task_description, response_text, pdf_file_name, task_type)

            # Display download button
            with open(pdf_file_name, "rb") as file:
                st.download_button("Download PDF", file, file_name=pdf_file_name)

if __name__ == "__main__":
    main()









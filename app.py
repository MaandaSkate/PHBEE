import os
import streamlit as st
import datetime
import random
from fpdf import FPDF
from google.cloud import dialogflowcx_v3beta1 as dialogflow_cx
from google.oauth2 import service_account
import json

# Load credentials from Streamlit secrets
credentials_info = st.secrets["google_service_account_key"]
credentials = service_account.Credentials.from_service_account_info(credentials_info)


# Define the Dialogflow parameters
project_id = "phoeb-426309"
agent_id = "016dc67d-53e9-49c5-acbf-dcb3069154f9"
session_id = "123456789"
language_code = "en"



# List of trigger words for different functionalities
trigger_words = ["quiz", "assessment", "project", "test", "oral assessment", "exam"]

def detect_intent_text(project_id, agent_id, session_id, text, language_code):
    client = dialogflow_cx.SessionsClient(credentials=credentials)
    session_path = f"projects/{project_id}/locations/global/agents/{agent_id}/sessions/{session_id}"
    text_input = dialogflow_cx.TextInput(text=text)
    query_input = dialogflow_cx.QueryInput(text=text_input, language_code=language_code)
    request = dialogflow_cx.DetectIntentRequest(session=session_path, query_input=query_input)
    response = client.detect_intent(request=request)
    return response.query_result

def generate_task(task_type, subject, grade, num_questions, num_options, total_marks):
    task_data = []
    for i in range(num_questions):
        question_text = f"Question {i+1} for {task_type}?"
        options = [f"Option {j+1}" for j in range(num_options)]
        correct_answer = random.choice(options)
        explanation = f"Explanation for question {i+1}."
        task_data.append({
            "question": question_text,
            "options": options,
            "answer": correct_answer,
            "explanation": explanation,
            "marks": total_marks // num_questions
        })
    return task_data

def create_pdf(task_data, file_name, task_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Title
    pdf.cell(200, 10, txt=f"{task_type.capitalize()} / Assessment", ln=True, align='C')
    pdf.cell(200, 10, txt=datetime.datetime.now().strftime("%Y-%m-%d"), ln=True, align='C')
    pdf.ln(10)
    # Questions
    for idx, question in enumerate(task_data):
        pdf.multi_cell(0, 10, txt=f"Question {idx + 1}: {question['question']} ({question['marks']} marks)")
        for option in question["options"]:
            pdf.cell(200, 10, txt=f"- {option}", ln=True)
        pdf.cell(200, 10, txt=f"Answer: {question['answer']}", ln=True)
        pdf.cell(200, 10, txt=f"Explanation: {question['explanation']}", ln=True)
        pdf.ln(5)
    pdf.output(file_name)

def main():
    st.title("Educational Task Generator")
    # Tabs for different task types
    tabs = st.tabs(["Quiz", "Assessment", "Project", "Test", "Oral Assessment", "Exam"])
    task_types = ["quiz", "assessment", "project", "test", "oral assessment", "exam"]
    # Initialize session state for chat history
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    # Display chat history
    for chat_entry in st.session_state['chat_history']:
        st.markdown(chat_entry['message'])
    # Input text box for user interaction
    user_input = st.text_input("You: ")
    # Button to send user input to Dialogflow
    if st.button("Enter"):
        if user_input.strip():
            response = detect_intent_text(project_id, agent_id, session_id, user_input, language_code)
            response_text = response.response_messages[0].text.text[0]
            # Add user input to chat history
            st.session_state['chat_history'].append({"message": f"You: {user_input}"})
            st.session_state['chat_history'].append({"message": f"Buddy: {response_text}"})
            st.markdown(f"Buddy: {response_text}")
    # Button to create PDF from the last chatbot response
    if st.button("Create PDF"):
        if st.session_state['chat_history']:
            last_response = st.session_state['chat_history'][-1]['message']
            if "Buddy: " in last_response:
                last_response = last_response.replace("Buddy: ", "")
            task_data = [{"question": last_response, "options": [], "answer": "", "explanation": "", "marks": 0}]
            create_pdf(task_data, "last_response.pdf", "Chatbot Response")
            with open("last_response.pdf", "rb") as f:
                st.download_button(label="Download PDF", data=f.read(), file_name="last_response.pdf", mime="application/pdf")
    # Button to clear chat history
    if st.button("Clear Chat"):
        st.session_state['chat_history'] = []
    # Tabs logic
    for tab, task_type in zip(tabs, task_types):
        with tab:
            st.write(f"This is the {task_type.capitalize()} tab.")

if __name__ == '__main__':
    main()



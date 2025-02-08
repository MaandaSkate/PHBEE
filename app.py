import os
import streamlit as st
from streamlit_option_menu import option_menu
import datetime
import uuid
from fpdf import FPDF
from google.cloud import dialogflowcx_v3beta1 as dialogflow_cx
from google.oauth2 import service_account
from google.cloud import firestore
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
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

# Define the Dialogflow parameters
project_id = "phoeb-426309"
agent_id = "016dc67d-53e9-49c5-acbf-dcb3069154f9"
language_code = "en"

# Initialize clients
def initialize_dialogflow_client(credentials):
    return dialogflow_cx.SessionsClient(credentials=credentials)

def initialize_firestore_client(credentials, project_id):
    return firestore.Client(credentials=credentials, project=project_id)

client = initialize_dialogflow_client(credentials)
db = initialize_firestore_client(credentials, project_id)

# Helper functions
def generate_session_id():
    return str(uuid.uuid4())

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

def extract_answer_key(response_text):
    """Extracts the answer key from the response text and returns it separately."""
    lines = response_text.split("\n")
    main_text = []
    answer_key = []

    is_answer_key = False
    for line in lines:
        if "Answer Key" in line:  # Detect where the answer key starts
            is_answer_key = True
            continue
        if is_answer_key:
            answer_key.append(line.strip())  # Store answer key separately
        else:
            main_text.append(line.strip())  # Store main task response

    return "\n".join(main_text), "\n".join(answer_key)


# 1. Memo Creation Function (must be defined first)
def create_memo(response_text):
    """Generate a memo text with answers from the response."""
    memo = "Memo:\n\n"
    questions = response_text.split("\n")
    
    for question in questions:
        if "Answer:" in question:  # Extract lines containing answers
            memo += question + "\n"

    if memo.strip() == "Memo:":  # If no answers are found, add a note
        memo += "No answers provided in response.\n"

    return memo

import re

def extract_answer_key(response_text):
    """Extract only the answer key from the generated response."""
    lines = response_text.split("\n")
    answer_key = []

    is_answer_key = False
    for line in lines:
        # Detect explicit "Answer Key" section
        if "Answer Key" in line or "Correct Answers" in line or "Answers:" in line:
            is_answer_key = True
            continue

        if is_answer_key:
            answer_key.append(line.strip())  # Store answer key separately
        else:
            # Detect inline answers like "Q1: ... Answer: ..."
            match = re.search(r"Answer:\s*(.*)", line, re.IGNORECASE)
            if match:
                correct_answer = match.group(1).strip()
                answer_key.append(correct_answer)

    return "\n".join(answer_key) if answer_key else "No answers detected."

def create_memo_pdf(answer_key, memo_file_name, task_type):
    """Generate a memo PDF containing only the extracted answers."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"{task_type.capitalize()} Memo", ln=True, align='C')
    pdf.cell(200, 10, txt=datetime.datetime.now().strftime("%Y-%m-%d"), ln=True, align='C')
    pdf.ln(10)

    pdf.set_fill_color(200, 220, 255)
    pdf.rect(x=10, y=30, w=190, h=pdf.get_y() + 10, style='F')

    pdf.set_xy(10, 40)
    pdf.multi_cell(0, 10, txt=f"Answer Key:\n{answer_key}" if answer_key.strip() else "No answers found.")

    pdf.output(memo_file_name)

# 2. PDF Creation Function (uses create_memo)
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

    pdf.output(file_name)








def detect_intent_text(client, project_id, agent_id, session_id, text, language_code="en"):
    try:
        session_path = f"projects/{project_id}/locations/global/agents/{agent_id}/sessions/{session_id}"
        text_input = dialogflow_cx.TextInput(text=text)
        query_input = dialogflow_cx.QueryInput(text=text_input, language_code=language_code)
        request = dialogflow_cx.DetectIntentRequest(session=session_path, query_input=query_input)
        response = client.detect_intent(request=request)
        return response.query_result.response_messages[0].text.text[0] if response.query_result.response_messages else "No response from Dialogflow."
    except Exception as e:
        st.error(f"Error detecting intent: {e}")
        return "An error occurred while processing your request."

def display_message(sender, message):
    if sender == "user":
        st.markdown(f'''
            <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-end;">
                <div style="background-color: #f0f0f0; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px; word-wrap: break-word;">
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
                <div style="background-color: #DCF8C6; border-radius: 10px; padding: 10px; max-width: 70%; font-size: 16px; word-wrap: break-word;">
                    {message}
                </div>
            </div>
            ''', unsafe_allow_html=True)




# Chatbot logic



def generate_session_id():
    """Generate a unique session ID."""
    return str(uuid.uuid4())



def chatbot():
    """Main function to handle the chatbot interaction."""
    # Initialize chat history and session ID
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = generate_session_id()

    st.title("Chat with PHBEE 🐝")
    st.markdown("<h2 style='text-align: center;'>Welcome to the PHBEE Chatbot!</h2>", unsafe_allow_html=True)

    # Initial bot greeting if no history exists
    if not st.session_state['chat_history']:
        display_message("PHBEE", "Greetings! I am PHBEE, your Educational AI assistant! How can I assist you today?")

    # Input field for user input
    user_input = st.text_input(
        "Type your message here:", 
        placeholder="Ask me anything..."
    )

    # Send button to manually trigger sending the message
    if st.button("Send") and user_input:  # User can either press 'Send' or hit 'Enter'
        with st.spinner('Processing...'):
            response = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], user_input, "en")

        # Display user and bot messages
        display_message("user", user_input)
        display_message("PHBEE", response)

        # Append both messages to the chat history
        st.session_state['chat_history'].append({"sender": "user", "message": user_input})
        st.session_state['chat_history'].append({"sender": "PHBEE", "message": response})

        # Clear input field after sending the message
        user_input = ""

    # Clear chat history button
    if st.button("Clear Chat"):
        st.session_state['chat_history'] = []

    # Display chat history
    for chat in st.session_state['chat_history']:
        if isinstance(chat, dict) and 'sender' in chat and 'message' in chat:
            display_message(chat['sender'], chat['message'])
        else:
            st.error("Chat history contains invalid data.")









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


def task_generator():
    st.subheader("Generate Educational Tasks")

    # Ensure session_id is initialized
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = generate_session_id()

    # Task type input
    task_type = st.selectbox("Select Task Type", ["Assessment", "Project", "Test", "Lesson Plan", "Exam"])
    subject = st.text_input("Subject")
    grade = st.selectbox("Grade", ["R", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
    curriculum = st.radio("Curriculum", ["CAPS", "IEB"])

    # Conditional inputs based on task type
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

    # Generate task button
    if st.button("Generate Task"):
    try:
        with st.spinner('Generating task, please wait...'):
            task_description = generate_task_description(task_type, subject, grade, curriculum, num_questions_or_term, total_marks_or_week)
            response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], task_description)

            # Extract only the answers for the memo
            answer_key = extract_answer_key(response_text)

            st.subheader("Generated Task Description and Response")
            st.write(f"**Task Type:** {task_type}")
            st.write(f"**Task Description:** {task_description}")
            st.write(f"**Response from Intent Detection:** {response_text}")

            st.subheader("Answer Key")
            st.write(answer_key)

            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"{task_type.replace(' ', '_')}_{timestamp}.pdf"
            memo_file_name = f"Memo_{task_type.replace(' ', '_')}_{timestamp}.pdf"
            zip_file_name = f"{task_type.replace(' ', '_')}_Task_and_Memo_{timestamp}.zip"

            create_pdf(task_description, response_text, file_name, task_type)
            create_memo_pdf(answer_key, memo_file_name, task_type)  # ✅ Now extracts answers correctly

            st.success("Task and Memo generated successfully!")
            st.balloons()

            with open(file_name, "rb") as task_pdf:
                task_pdf_data = task_pdf.read()

            with open(memo_file_name, "rb") as memo_pdf:
                memo_pdf_data = memo_pdf.read()

            st.download_button("📄 Download Task PDF", data=task_pdf_data, file_name=file_name, mime='application/pdf')
            st.download_button("📄 Download Memo PDF", data=memo_pdf_data, file_name=memo_file_name, mime='application/pdf')

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                zip_file.writestr(file_name, task_pdf_data)
                zip_file.writestr(memo_file_name, memo_pdf_data)

            zip_buffer.seek(0)

            st.download_button("📁 Download Both PDFs (Task + Memo)", data=zip_buffer, file_name=zip_file_name, mime="application/zip")

    except Exception as e:
        st.error(f"An error occurred: {e}")




 




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

                memo_file_name = f"Free_Task_Memo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                create_memo_pdf(response_text, memo_file_name, "Free Task")

                st.markdown(f"**Generated PDF:** {request_text}")
                st.markdown(f"**Response:** {response_text}")

                # Provide download buttons
                st.download_button(
                    label="Download Task PDF",
                    data=open(pdf_file_name, "rb").read(),
                    file_name=pdf_file_name,
                    mime='application/pdf'
                )
                st.download_button(
                    label="Download Memo PDF",
                    data=open(memo_file_name, "rb").read(),
                    file_name=memo_file_name,
                    mime='application/pdf'
                )
        else:
            st.error("Please enter a valid request.")

# All Classwork logic
def all_classwork():
    st.subheader("All Classwork")
    st.markdown("Generate a variety of classwork-related tasks.")

    # Ensure session_id is initialized
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = generate_session_id()

    # Task type options
    task_type = st.selectbox("Select classwork type", ["Homework", "Worksheet", "Class Exercise", "Quiz", "Teaching Admin Task", "Explainer", "Summary"])

    # Common inputs
    subject = st.text_input("Enter subject name", placeholder="e.g., English, Math")
    grade = st.number_input("Select grade", min_value=1, max_value=12, step=1)
    curriculum = st.radio("Select curriculum", ["CAPS", "IEB"])

    # Handle Explainer and Summary differently (no marks, focus on concepts)
    if task_type in ["Explainer", "Summary"]:
        explanation_topic = st.text_area("Enter the topic or concept to be explained", placeholder="e.g., Pythagorean Theorem")
        if st.button(f"Generate {task_type}"):
            if subject and grade and curriculum and explanation_topic:
                task_description = f"Create a detailed {task_type} on {explanation_topic} for {subject} (Grade {grade}, {curriculum}). Focus on explaining the concept in a clear and engaging way."
                with st.spinner("Generating..."):
                    response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], task_description)

                st.markdown(f"**Generated {task_type}:** {task_description}")
                st.markdown(f"**Response:** {response_text}")
                
                # Generate PDF
                pdf_file_name = f"{task_type.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                create_pdf(task_description, response_text, pdf_file_name, task_type)

                # Provide a download link for the PDF
                st.markdown(f"""
                <a href="data:application/octet-stream;base64,{base64.b64encode(open(pdf_file_name, 'rb').read()).decode()}" download="{pdf_file_name}">
                <div style="background-color: #FFCC00; color: white; padding: 10px; border-radius: 5px; text-align: center; max-width: 200px;">
                Download {pdf_file_name}
                </div>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.error("Please provide all required inputs.")
    else:
        # Existing task logic for other task types
        num_questions = st.slider("Number of questions", min_value=1, max_value=10)
        total_marks = st.slider("Total marks", min_value=1, max_value=100)
        if st.button(f"Generate {task_type}"):
            if subject and grade and curriculum:
                task_description = generate_task_description(task_type, subject, grade, curriculum, num_questions, total_marks)
                with st.spinner("Generating..."):
                    response_text = detect_intent_text(client, project_id, agent_id, st.session_state['session_id'], task_description)

                st.markdown(f"**Generated {task_type}:** {task_description}")
                st.markdown(f"**Response:** {response_text}")
                
                # Generate PDF
                pdf_file_name = f"{task_type.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                create_pdf(task_description, response_text, pdf_file_name, task_type)

                # Provide a download link for the PDF
                st.markdown(f"""
                <a href="data:application/octet-stream;base64,{base64.b64encode(open(pdf_file_name, 'rb').read()).decode()}" download="{pdf_file_name}">
                <div style="background-color: #FFCC00; color: white; padding: 10px; border-radius: 5px; text-align: center; max-width: 200px;">
                Download {pdf_file_name}
                </div>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.error("Please provide all required inputs.")

# Send Email Function
def send_email(to_email, subject, body):
    try:
        from_email = st.secrets["email"]["email"]
        email_password = st.secrets["email"]["email_password"]
    except KeyError as e:
        st.error(f"Error: Missing secret key {e}")
        return

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, email_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        st.success("Email sent successfully!")
    except smtplib.SMTPAuthenticationError as e:
        st.error(f"Authentication error: {e}")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Function to submit feedback
def submit_feedback(rating, best_feature, feedback, contact_info):
    email_body = f"Rating: {rating}\nBest Feature: {best_feature}\nFeedback: {feedback}\nContact Info: {contact_info}"
    send_email("maandaskate60@gmail.com", "PHBEE Feedback Submission", email_body)
    st.success("Thank you for your feedback! We've emailed it to our support team.")

# Feedback form
def feedback_form():
    st.subheader("Rate PHBEE the Educational Bot")
    rating = st.slider("How would you rate PHBEE?", 1, 5, value=5)
    
    # Best feature ranking input
    best_feature = st.selectbox("What is PHBEE's best feature?", 
                                ["Chatbot", "Task Generator", "All Classwork", "Free Task", "Others"])
    
    # General feedback input
    feedback = st.text_area("Any other feedback?")
    
    # Contact info (optional)
    contact_info = st.text_input("Your email or phone number (optional)")

    # Submit button
    if st.button("Submit Feedback"):
        submit_feedback(rating, best_feature, feedback, contact_info)

# Main function to handle page navigation
def main():
    # Sidebar menu with icons
    with st.sidebar:
        selected = option_menu(
            menu_title="PHBEE Educational AI",
            options=["Home", "Chatbot", "Task Generator", "All Classwork", "Free Task", "Feedback"],
            icons=["house", "robot", "file-text", "clipboard-data", "pencil-square", "chat-right-dots"],
            menu_icon="cast",
            default_index=0,
        )

    # Page content logic based on selection
    if selected == "Home":
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
        st.image("image/PHBEE LOGO FINAL.png", use_container_width=True)

    elif selected == "Chatbot":
        chatbot()

    elif selected == "Task Generator":
        task_generator()

    elif selected == "All Classwork":
        all_classwork()

    elif selected == "Free Task":
        free_task()

    elif selected == "Feedback":
        feedback_form()

# Run the app
if __name__ == "__main__":
    main()










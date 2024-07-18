# PHBEETEST
first deployment of PHBEE generator
# Educational Task Generator

This is a Streamlit application that generates educational tasks such as quizzes, assessments, projects, tests, oral assessments, and exams. The app interacts with a Dialogflow CX agent to generate responses based on user input.

## Setup

### Prerequisites
- Python 3.7 or higher
- A Google Cloud project with Dialogflow CX enabled
- A service account key file from your Google Cloud project

### Installation

1. Clone this repository:
    ```sh
    git clone https://github.com/yourusername/educational-task-generator.git
    cd educational-task-generator
    ```

2. Install the dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Place your service account key file in the project directory and update the path in `app.py`:
    ```python
    service_account_key_path = "path_to_your_service_account_key.json"
    ```

### Running the App

Run the Streamlit app:
```sh
streamlit run app.py

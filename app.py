import os
import re
import pandas as pd
import requests
import matplotlib.pyplot as plt
from flask import Flask, request, render_template, send_file, jsonify

app = Flask(__name__)
uploaded_data = None  # Global variable to store the uploaded data

def load_data(file_path):
    if file_path.endswith('.csv'):
        data = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        data = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")
    return data

def extract_code_from_response(response_text):
    # Use regex to extract code between ``` blocks
    code_blocks = re.findall(r'```python(.*?)```', response_text, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()
    else:
        return None

def py_code_of_dashboard(data, file_path):
    url = 'https://financeops-azure-openai-backup.openai.azure.com/openai/deployments/financeops-azure-openai-backup/chat/completions?api-version=2024-04-01-preview'
    headers = {
        'api-key': '5b4d8a7651294134b88ada1181a43795',
        'Content-Type': 'application/json'
    }
    
    # Convert the dataframe to a CSV string
    data_csv = data.to_csv(index=False)
    
    prompt = f"Here is a dataset in CSV format from file '{file_path}':\n\n{data_csv}\n\nPlease provide a Python code snippet starting from imports that creates a dashboard with 6 visualizations compiled in a single image. Ensure the code snippet saves the image to 'static/dashboard.png' and is provided without any additional text or explanations."
    
    data = {
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()
    
    if 'choices' in response_json:
        response_text = response_json['choices'][0]['message']['content']
        # Extract the Python code snippet
        python_code = extract_code_from_response(response_text)
        if python_code:
            return python_code
        else:
            return f"Error: No Python code snippet found in response."
    else:
        return f"Error: {response_json}"

def run_dashboard_code(dashboard_code):
    # Ensure the generated image is saved in the static folder
    exec(dashboard_code, {'plt': plt, 'save_path': 'static/dashboard.png'})
    plt.savefig('static/dashboard.png')
    plt.close()

def ask_data(data, question):
    url = 'https://financeops-azure-openai-backup.openai.azure.com/openai/deployments/financeops-azure-openai-backup/chat/completions?api-version=2024-04-01-preview'
    headers = {
        'api-key': '5b4d8a7651294134b88ada1181a43795',
        'Content-Type': 'application/json'
    }
    
    # Convert the dataframe to a CSV string
    data_csv = data.to_csv(index=False)
    
    # Adjusted prompt to request only descriptive answers without code
    prompt = f"Here is a dataset in CSV format:\n\n{data_csv}\n\nFrom the data please give an answer for '{question}'?. Please provide a descriptive answer without including any code or step-by-step instructions for performing calculations"

    data = {
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response_json = response.json()
    
    if 'choices' in response_json:
        return response_json['choices'][0]['message']['content']
    else:
        return f"Error: {response_json}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global uploaded_data
    file = request.files['file']
    if file:
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        uploaded_data = load_data(file_path)
        dashboard_code = py_code_of_dashboard(uploaded_data, file_path)
        if dashboard_code:
            run_dashboard_code(dashboard_code)
            data_head = uploaded_data.head(3).to_html()
            return jsonify({"status": "success", "data_head": data_head})
    return jsonify({"status": "failed"})

@app.route('/ask', methods=['POST'])
def ask_question():
    global uploaded_data
    question = request.form['question']
    if uploaded_data is not None and question:
        answer = ask_data(uploaded_data, question)
        return jsonify({"question": question, "answer": answer})
    return jsonify({"error": "No data uploaded or question provided."})

@app.route('/generate_dashboard', methods=['GET'])
def generate_dashboard():
    global uploaded_data
    if uploaded_data is not None:
        file_path = os.path.join('uploads', 'temp.csv')  # Temporarily save data to a file for OpenAI request
        uploaded_data.to_csv(file_path, index=False)
        dashboard_code = py_code_of_dashboard(uploaded_data, file_path)
        if dashboard_code:
            run_dashboard_code(dashboard_code)
            return jsonify({"status": "success"})
    return jsonify({"status": "failed"})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    app.run(debug=True)

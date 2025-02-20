from flask import Flask, request, jsonify, render_template
import os
from LlmModule import LlmModule

# Create the Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")

# Set a directory to save uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

llm_instance = None

# Route to serve the main HTML page
@app.route("/")
def index():
    return render_template("index.html")

# API route for chatbot interaction
@app.route('/chat', methods=['POST'])
def chat():
    print(request)
    print(request.json)
    user_message = request.json.get("message")
    bot_reply = llm_instance.receive_request(user_message)
    return jsonify({"reply": bot_reply})

if __name__ == '__main__':
    llm_instance = LlmModule()
    app.run(host='0.0.0.0', port=8000)

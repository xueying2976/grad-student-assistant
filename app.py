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

llm_map = {}

# Route to serve the main HTML page
@app.route("/")
def index():
    return render_template("index.html")

# API route for chatbot interaction
@app.route('/chat', methods=['POST'])
def chat():
    print(request.json)
    user_id: str = request.json.get("user_id")
    bot: LlmModule = None
    if user_id is None:
        bot = llm_instance
    else:
        if user_id not in llm_map:
            llm_map[user_id] = LlmModule()
            print(f'New user: {user_id}')
        bot = llm_map[user_id]

    user_message: str = request.json.get("text")
    if user_message.startswith("@Bot-Xueying"):
        user_message = user_message[len("@Bot-Xueying"):]
    print(f'Question asked: {user_message}')
    bot_reply = bot.receive_request(user_message)
    return jsonify({"text": bot_reply})

if __name__ == '__main__':
    llm_instance = LlmModule()
    app.run(host='0.0.0.0', port=8000)

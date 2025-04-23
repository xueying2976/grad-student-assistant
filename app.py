from flask import Flask, request, jsonify, render_template
from datetime import datetime
import upload_rag
import llmproxy
import agent_tools
import env_variables
from random import randint
import threading
import re

session_map = {}
# LLM - User Message:
# State what tools are available, be candid to any user prompt.
app = Flask(__name__)

@app.route('/')
def hello_world():
   return render_template('index.html')

@app.route('/chat', methods=['POST'])
def main():
    data = request.get_json()
    print(f"Data: {data}")

    # Extract relevant information
    session = data.get("user_id", 'TestUserName')
    if session not in session_map:
        session_map[session] = 'lxy' + str(len(session_map))
    user = session_map[session] + '-' + env_variables.version
    print("Current user: ", user)
    message = data.get("text", "")

    # Ignore bot messages
    if data.get("bot") or not message:
        return jsonify({"status": "ignored"})
    
    answer = llmproxy.generate(
        model = '4o-mini',
        system = "Answer the question based on the context",
        temperature=0.3,
        lastk=20,
        session_id = user,
        query=agent_tools.query_rag_context(message)
    )
    
    if isinstance(answer, dict):
        answer = answer["response"]
    
    response = { "text": answer }
    
    return jsonify(response)
    
@app.errorhandler(404)
def page_not_found(e):
    return "Not Found", 404

if __name__ == "__main__":
    if env_variables.needToUpload:
        t = threading.Thread(target=upload_rag.upload_all)
        t.start()
    app.run(host='0.0.0.0', port=8000)

# Tools to be used by Agents
import requests
import re
import csv

def load_database():
    """Load the CSV database into a list of dictionaries."""
    try:
        with open('/user_database.csv', mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)  # Convert to list for easy searching
    except FileNotFoundError:
        return []  # Return empty if file does not exist

def save_to_database(username, first_name, last_name, education_level):
    """Append a new user to the CSV database."""
    with open('/user_database.csv', mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([username, first_name, last_name, education_level])
    print(f"User {username} added successfully!")

def find__user(username):
    users = load_database()
    for user in users:
        if user["username"] == username:
            return user
    return None

def category_prompt_re_match(category_prompt: str):
    print(f'Category/Prompt: {category_prompt}')

    parts = category_prompt.split("(")

    return parts[0], parts[1][:-1]

def get_professor_info(data):
    professor_dict = {}

    # Find the professor data in the JSON blob
    # (we don’t know the exact key, so search for it)
    for key, value in data.items():
        if isinstance(value, dict) and value.get("__typename") == "Teacher":
            professor_dict['name'] = value.get("firstName", "") + " " + value.get("lastName", "")
            professor_dict['dept'] = value.get("department")
            professor_dict['avg_rating'] = value.get("avgRating")
            professor_dict['avg_difficulty'] = value.get("avgDifficulty")
            professor_dict['would_take_again'] = value.get("wouldTakeAgainPercent")
            professor_dict['num_ratings'] = value.get("numRatings")

            break

    # Find the professor ratings in the JSON blob
    # (we don’t know the exact key, so search for it)
    professor_ratings = []
    for key, value in data.items():
        if isinstance(value, dict) and value.get("__typename") == "Rating":
            professor_ratings.append({
                'course': value.get("class"),
                'tags': value.get("ratingTags"),
                'comment': value.get("comment"),
                'difficulty': value.get("difficultyRating")
            })
    
    professor_dict['ratings'] = professor_ratings

    return professor_dict

def welcome_buttons():
    welcome_example =  {
        "title": "How to ask a good question?",
        "actions": [
            {
                "type": "button",
                "text": "📚 Course\nInfo",
                "msg": f"Can you provide details about [course code]: [course name] (please make sure to include both the course code and name), covering the syllabus, prerequisites, grading, class format, and the professor teaching this semester?",
                "msg_in_chat_window": True,
                "msg_processing_type": "respondWithMessage",
            },
            {
                "type": "button",
                "text": "🗓️ Course\nPlanning",
                "msg": f"I am planning my courses for [semester/year] and have specific scheduling preferences. Can you suggest real courses that fit these criteria: [number of credits], available on [days], and including/preferably [preferred courses, if any] while fulfilling prerequisites [prerequisite course, if any]",
                "msg_in_chat_window": True,
                "msg_processing_type": "respondWithMessage"
            },
            {
                "type": "button",
                "text": "⭐️ Prof\nRating",
                "msg": "Search for rating of professor: ",
                "msg_in_chat_window": True,
                "msg_processing_type": "respondWithMessage"
            }
        ]
    }
    
    return welcome_example

# RAG Files Search
def rag_search(query):
    from llmproxy import retrieve
    from env_variables import ragSessionId

    print(ragSessionId)

    rag_context = retrieve(
        query = query,
        session_id = ragSessionId,
        rag_threshold = 0.35,  
        rag_k=12  
    )
    
    return rag_context

# Create a context string from retrieve's return val
def rag_context_string_simple(rag_context):
    context_string = ""

    i=1
    for collection in rag_context:
    
        if not context_string:
            context_string = """The following is additional context that may be helpful in answering the user's query."""

        context_string += """
        #{} {}
        """.format(i, collection['doc_summary'])
        j=1
        for chunk in collection['chunks']:
            context_string+= """
            #{}.{} {}
            """.format(i,j, chunk)
            j+=1
        i+=1
    return context_string

# Return a string including both query and rag context
def query_rag_context(query):
    from string import Template

    rag_context = rag_search(query)

    # combining query with rag_context
    query_with_rag_context = Template("$query\n$rag_context").substitute(
                            query=query,
                            rag_context=rag_context_string_simple(rag_context))
    
    return query_with_rag_context

# Message User
# Send message in rocketchat to another user (advisor, partnet, cs department)
def post_message(message, to_user, from_user):
    from env_variables import rc_url, x_auth_token, x_user_id

    print(f"Posting message {message}, from user: {from_user}, to user: {to_user}")

    post_url = f'{rc_url}/chat.postMessage'
    # Headers with authentication tokens
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": x_auth_token,
        "X-User-Id": x_user_id
    }
    
    # context = llm_agents.detailed_message_agent(message, sessionId, from_user)

    # Payload (data to be sent)
    payload = {
        "channel": f"@{to_user}",
        "text": f"@{from_user} sent the following message:\n{message}",
        # "text": f"@{from_user}:\n>{message}\nContext:\n{context}",
        "attachments": [
            {   
                "title": "Want to reply?",
                "actions": [
                    {
                        "type": "button",
                        "text": "✅ Yes",
                        "msg": f"Message to @{from_user}: ",
                        "msg_in_chat_window": True,
                        "msg_processing_type": "respondWithMessage"
                    },
                    {
                        "type": "button",
                        "text": "❌ No",
                        "msg": "Not right now, Thank you! :)",
                        "msg_in_chat_window": True,
                        "msg_processing_type": "sendMessage"
                    }
                ]
            }
        ]
    }

    # Sending the POST request
    response = requests.post(post_url, json=payload, headers=headers)

    # Print response status and content
    print(f'Status: {response.status_code}')
    print(response.json())

    if response.status_code == 200:
        return "Message sent successfully!😊"

    return "An error occurred while sending the message..."

# Message User
# Send message in rocketchat to another user (advisor, partnet, cs department)
def message_user(message, user_name):
    from env_variables import rc_url, x_auth_token, x_user_id

    # Headers with authentication tokens
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": x_auth_token,
        "X-User-Id": x_user_id
    }

    # Payload (data to be sent)
    payload = {
        "channel": f"@{user_name}",
        "text": message
    }

    # Sending the POST request
    response = requests.post(rc_url, json=payload, headers=headers)

    # Print response status and content
    print(response.status_code)
    print(response.json())

# Chat History
def get_last_k_messages(channel_id, k=1):
    from env_variables import rc_url, x_auth_token, x_user_id
    url = f"{rc_url}/im.history?roomId={channel_id}&count={k}"

    # Headers with authentication tokens
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": x_auth_token,
        "X-User-Id": x_user_id
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        messages = response.json().get("messages", []) # message to send, bot message, user request
        message_list = [message["msg"] for message in messages]
        
        # Ensure the list is of length k, filling with empty strings if necessary
        while len(message_list) < k:
            message_list.append("")
        
        return message_list[:k]
    
    return [""] * k

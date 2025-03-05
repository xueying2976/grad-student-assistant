# Tools to be used by Agents
import requests
import re

def category_prompt_re_match(category_prompt):
    print(f'Category/Prompt: {category_prompt}')

    pattern = r'^([^()]*)\((.*?)\)$'
    params = re.match(pattern, category_prompt['response'], re.DOTALL)

    return params.group(1), params.group(2)

# Return a list of capabilities buttons in JSON
def capabilites_buttons():
    capabilities =  {
        "title": "Quick Actions",
        "actions": [
            {
                "type": "button",
                "text": "📚 Course\nInfo",
                "msg": "I would like help with course information",
                "msg_in_chat_window": True,
                "msg_processing_type": "sendMessage",
            },
            {
                "type": "button",
                "text": "🎓 Program\nInfo",
                "msg": "I would like help with my program",
                "msg_in_chat_window": True,
                "msg_processing_type": "sendMessage"
            },
            {
                "type": "button",
                "text": "🗓️ Course\nPlanning",
                "msg": "I would like help with my courses planning",
                "msg_in_chat_window": True,
                "msg_processing_type": "sendMessage"
            },
            {
                "type": "button",
                "text": "📞 Contact\nDepartment",
                "msg": "I would like help with cs department contact information",
                "msg_in_chat_window": True,
                "msg_processing_type": "sendMessage"
            },
            {
                "type": "button",
                "text": "👩🏻‍💻 Job\Recommendation",
                "msg": "I would like help with job recommendations",
                "msg_in_chat_window": True,
                "msg_processing_type": "sendMessage"
            }
        ]
    }
    
    return capabilities

# Return a list of contact buttons in JSON
def contact_buttons(query):
    contact_info = {
        "title": "Need More Help?",
        "actions": [
            {
                "type": "button",
                "text": "📞 Phone",
                "msg": "What is the CS Department phone number?",
                "msg_in_chat_window": ('phone' not in query.lower()),
                "msg_processing_type": "sendMessage",
            },
            {
                "type": "button",
                "text": "📧 Email",
                "msg": "What is the CS Department email address?",
                "msg_in_chat_window": ('email' not in query.lower()),
                "msg_processing_type": "sendMessage"
            },
            {
                "type": "button",
                "text": "📍 Address",
                "msg": "What is the CS Department address?",
                "msg_in_chat_window": ('address' not in query.lower()),
                "msg_processing_type": "sendMessage"
            },
            {
                "type": "button",
                "text": "👤 Message\nDepartment",
                "msg": "Send a message to the CS department",
                "msg_in_chat_window": ('message' not in query.lowe()),
                "msg_processing_type": "sendMessage"
            }
        ]
    }

    return contact_info

# Google Web Search
def web_search(query):
    from env_variables import googleApiKey, googleSearchApiUrl, googleSearchId

    params = {
        "key": googleApiKey,
        "cx": googleSearchId,
        "q": query,
        "num": 5
    }
    
    google_search = requests.get(googleSearchApiUrl, params=params)
    search_results = []
    if google_search.status_code == 200:
        search_results = [(item["title"], item["link"], item["snippet"]) for item in google_search.json().get("items", [])]
    else:
        print("Error:", google_search.status_code, query)

    return search_results

# RAG Files Search
def rag_search(query):
    from llmproxy import retrieve
    from env_variables import ragSessionId

    print(ragSessionId)

    rag_context = retrieve(
        query = query,
        session_id = ragSessionId,
        rag_threshold = 0.4,
        rag_k = 10)
    
    print(f"RAG: {rag_context}")
    
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

# Send Email
# Email someone in the cs department, faculty or department
def send_email(query, email_address):
    return None

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









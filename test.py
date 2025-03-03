import requests

response_main = requests.get("https://literary-milka-javiervillegas-932439c1.koyeb.app/")
print('Web Application Response:\n', response_main.text, '\n\n')


# data = {"text":"tell me about tufts"}
# data = {"text":input("Enter Message: ")}
# response_llmproxy = requests.post("https://literary-milka-javiervillegas-932439c1.koyeb.app/query", json=data)
# print('LLMProxy Response:\n', response_llmproxy.text)

while(True):
    data = {"text":input("Enter Message: ")}
    response_llmproxy = requests.post("https://literary-milka-javiervillegas-932439c1.koyeb.app/query", json=data)
    print('LLMProxy Response:\n', response_llmproxy.text)

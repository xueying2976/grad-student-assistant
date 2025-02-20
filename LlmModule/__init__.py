from .llmproxy import generate, pdf_upload, text_upload
from random import randint

class LlmModule:
    def __init__(self):
        self.session_id = f'liuxueying-{randint(100000000, 999999999)}'
        self.create_context()

        print(f'New session created with ID: {self.session_id}')

    def create_context(self):
        response = pdf_upload(
            path = './context.pdf',
            session_id = self.session_id,
            strategy = 'smart'
        )

        print(f'Context created: {response}')

    def ask_question(self, question: str) -> str:
        response = generate(
            model="4o-mini",
            system= "You are an AI assistant helping Tufts graduate students strictly based on the already provided content.",
               # "Do not generate answers outside the provided context. If the question is unrelated, respond with 'I can only provide information based on the handbook.'",
            query=question,
            temperature=0.3,
            lastk=1024,
            session_id=self.session_id,
            rag_usage=True,
            rag_threshold=0.4,
            rag_k=5
        )
        
        print(response)
        
        if isinstance(response, str):
            return response

        return response["response"]
    
    def receive_request(self, message: str) -> str:
        return self.ask_question(message)


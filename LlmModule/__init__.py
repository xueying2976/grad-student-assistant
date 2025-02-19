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
            description="This provided PDF file is the Tufts University Graduate Students Handbook.",
            session_id = self.session_id,
            strategy = 'smart'
        )

        print(f'Context created: {response}')

    def ask_question(self, question: str) -> str:
        response = generate(
            model="4o-mini",
            system='Answer my questions strictly and solely based on the already provided context, which is the content of the Tufts University Graduate Students Handbook. You will be getting questions from a Tufts graduate student.',
            query=question,
            temperature=0.5,
            lastk=2048,
            session_id=self.session_id,
            rag_usage=True,
            rag_threshold=0.4,
            rag_k=9
        )
        
        print(response)

        return response["response"]
    
    def receive_request(self, message: str) -> str:
        return self.ask_question(message)


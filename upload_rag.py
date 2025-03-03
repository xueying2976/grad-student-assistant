from llmproxy import pdf_upload
from env_variables import ragSessionId
import time

def upload_files(file_path):
    response = pdf_upload(
        path = file_path,
        session_id = ragSessionId,
        strategy = 'smart')

    print(response)

def upload_all():
    for i in range(5):
        upload_files(f'RAG Files 2/context2-{i+1}.pdf')
        time.sleep(9)
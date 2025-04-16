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
    for i in range(4):
        file = f'RAGFiles/fall-{i+1}.pdf'
        upload_files(file)
        print("Uploaded file: " + file)
        time.sleep(9)
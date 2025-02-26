from .llmproxy import generate, pdf_upload
from random import randint
import requests, os
from bs4 import BeautifulSoup
from urllib.parse import quote

API_KEY = os.environ.get("GOOGLE_API_KEY")
CX = os.environ.get("GOOGLE_CX")

class LlmModule:
    def __init__(self):
        self.session_id = f'liuxueying-{randint(1000000000, 9999999999)}'
        self.create_context()
        print(f'New session created with ID: {self.session_id}')

    def create_context(self):
        response = pdf_upload(
            path='./context.pdf',
            session_id=self.session_id,
            strategy='smart'
        )
        print(f'Context created: {response}')

    def ask_question(self, question: str) -> str:
        """First, check if the query needs syllabus info. If not, use RAG directly."""
        
        # 1️⃣ 让 ChatGPT 判断是否需要 syllabus
        syllabus_check = generate(
            model="4o-mini",
            system="Determine whether the following query is directly asking for details about a specific course at Tufts University, "
                   "such as prerequisites, topics covered, grading policies, or required textbooks. "
                   "If the query is general (e.g., about AI, programming, or university policies) or not course-related, respond with 'no'. "
                   "Respond only with 'yes' or 'no'.",
            query=question,
            temperature=0,
            session_id=self.session_id,
            lastk=1024
        )
        
        if isinstance(syllabus_check, dict):
            syllabus_check = syllabus_check['response']

        print(f"DEBUG: Syllabus requirement check: {syllabus_check}")

        if syllabus_check.strip().lower() == "no":
            # 2️⃣ 如果不需要 syllabus，直接用 RAG
            response = generate(
                model="4o-mini",
                system="You are an AI assistant helping Tufts graduate students with course information. "
                       "All information must come from the provided knowledge base, and you should never make up courses.",
                query=f"Question: {question}",
                temperature=0.3,
                lastk=1024,
                session_id=self.session_id,
                rag_usage=True,
                rag_threshold=0.4,
                rag_k=5
            )
            
            print(f"Final response (No syllabus needed): {response['response']}")
            return response["response"]

        # 3️⃣ 让 ChatGPT 通过 RAG 提取所有相关课程
        course_list_check = generate(
            model="4o-mini",
            system="Extract only the official Tufts University course names and their corresponding course codes "
                   "strictly from the provided knowledge base. Do NOT create or assume course names. "
                   "Return them in a comma-separated format like: CS160:Machine Learning, CS105:Data Structures."
                   "Return at most 2 classes; you may return only one class if you think only one is relevant.",
            query=question,
            temperature=0,
            lastk=1024,
            session_id=self.session_id,
            rag_usage=True,  
            rag_threshold=0.4,
            rag_k=5
        )

        print(f'Course list: {course_list_check["response"]}')
        print(f"DEBUG: Full response from generate(): {course_list_check}")

        courses = [course.strip() for course in course_list_check["response"].split(",")]
        
        syllabus_content = ""

        # 4️⃣ 遍历课程，Google 搜索 syllabus
        for course in courses:
            if ":" not in course:
                continue

            course_code, _, course_name = course.partition(":")  # ✅ 保障课程名称完整
            course_code = course_code.strip()
            course_name = course_name.strip()

            syllabus_url = self.search_syllabus(course_code, course_name)
            if syllabus_url:
                syllabus_content += f"{course_code} - {course_name} Syllabus:\n"
                syllabus_content += self.scrape_syllabus(syllabus_url, 30000 // len(courses)) + "\n\n"

        print(f'Syllabus content: {syllabus_content}')
                
        # 5️⃣ LLM 结合 RAG + syllabus 生成最终回答
        response = generate(
            model="4o-mini",
            system="You are an AI assistant helping Tufts graduate students with course information. "
                   "Use the provided syllabus content if relevant. Never create courses that are not in the provided information. "
                   "If the question is too broad, ask for clarification.",
            query=f"Question: {question}\n\nSyllabus Content:\n{syllabus_content}",
            temperature=0.3,
            lastk=1024,
            session_id=self.session_id,
            rag_usage=True,  
            rag_threshold=0.4,
            rag_k=5
        )
        
        print(f'Final response: {response["response"]}')
        return response["response"]
    
    def receive_request(self, message: str) -> str:
        return self.ask_question(message)

    def search_syllabus(self, course_code, course_name):
        """Google Search for the first syllabus result"""
        query = f"Tufts {course_code} {course_name} syllabus"
        query = quote(query)
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={API_KEY}&cx={CX}"

        response = requests.get(url)
        results = response.json()

        if "items" in results:
            return results["items"][0]["link"]
        return None
    
    def scrape_syllabus(self, url, length):
        """Scrape and extract relevant syllabus content from a webpage."""
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return "Unable to access syllabus page"

        soup = BeautifulSoup(response.text, "html.parser")

        # **1️⃣ Remove unnecessary elements like script, style, and footer**
        for tag in soup(["script", "style", "footer", "nav", "header", "aside"]):
            tag.decompose()  # Remove the tag completely

        # **2️⃣ Try to extract syllabus from common structures (table, sections, etc.)**
        syllabus_text = ""

        # Try extracting content from syllabus-specific sections
        syllabus_section = soup.find("section", class_="syllabus") or soup.find("div", class_="syllabus")
        if syllabus_section:
            syllabus_text = syllabus_section.get_text(separator="\n")

        # **3️⃣ If no structured syllabus section, extract from multiple text tags**
        if not syllabus_text.strip():
            paragraphs = soup.find_all(["p", "li", "div"])  # Grab multiple tag types
            syllabus_text = "\n".join(p.get_text() for p in paragraphs)

        # **4️⃣ Ensure the text is clean and readable**
        syllabus_text = syllabus_text.strip()
        
        return syllabus_text[:length]  # ✅ Increase text limit for better results
    
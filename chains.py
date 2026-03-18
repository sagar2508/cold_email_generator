# # import os
# # from dotenv import load_dotenv
# # import streamlit as st
# # from langchain_community.document_loaders import WebBaseLoader
# # from chains import Chain
# # from my_portfolio import Portfolio
# # from utils import clean_text

# # # Load env variables
# # load_dotenv()

# # def create_streamlit_app(llm, portfolio, clean_text):
# #     st.set_page_config(layout="wide", page_title="Cold Email Generator", page_icon="📧")

# #     st.title("📧 Cold Email Generator")
# #     url_input = st.text_input("Enter a Job URL:")
# #     submit_button = st.button("Generate Cold Email")

# #     if submit_button:
# #         if not url_input.strip():
# #             st.warning("⚠️ Please enter a valid URL before submitting.")
# #             return

# #         try:
# #             with st.spinner("⏳ Loading job details, please wait..."):
# #                 # Load website data
# #                 user_agent = os.getenv("USER_AGENT", "Mozilla/5.0")
# #                 loader = WebBaseLoader([url_input], header_template={"User-Agent": user_agent})
# #                 page_content = loader.load().pop().page_content

# #             with st.spinner("🧹 Cleaning and processing job description..."):
# #                 data = clean_text(page_content)

# #             with st.spinner("💼 Loading portfolio..."):
# #                 portfolio.load_portfolio()

# #             with st.spinner("🧠 Extracting job details..."):
# #                 jobs = llm.extract_jobs(data)

# #             if not jobs:
# #                 st.warning("No job details were found on this page.")
# #                 return

# #             for job in jobs:
# #                 st.subheader(f"📄 Job: {job.get('role', 'Unknown Role')}")
# #                 skills = job.get('skills', [])
# #                 links = portfolio.query_links(skills)

# #                 with st.spinner("✉️ Generating cold email..."):
# #                     email = llm.write_mail(job, links)

# #                 st.markdown("### 📬 Cold Email:")
# #                 st.code(email, language='markdown')

# #         except Exception as e:
# #             st.error(f"🚨 An Error Occurred: {e}")

# # if __name__ == "__main__":
# #     chain = Chain()
# #     portfolio = Portfolio()
# #     create_streamlit_app(chain, portfolio, clean_text)
# # chains.py
# import os
# import json
# from langchain_groq import ChatGroq
# from langchain_core.prompts import PromptTemplate
# from langchain_core.output_parsers import JsonOutputParser
# from langchain_core.exceptions import OutputParserException
# from dotenv import load_dotenv

# load_dotenv()


# class Chain:
#     def __init__(self):
#         self.llm = ChatGroq(
#             temperature=0,
#             api_key=os.getenv("GROQ_API_KEY"),
#             model_name="llama-3.3-70b-versatile"
#         )

#     def _chunk_text(self, text, chunk_size=3000):
#         """Splits text into manageable chunks based on word count."""
#         words = text.split()
#         for i in range(0, len(words), chunk_size):
#             yield " ".join(words[i:i + chunk_size])

#     def extract_jobs(self, cleaned_text):
#         """Extract job info safely from large scraped text with robust parsing."""
#         prompt_extract = PromptTemplate.from_template(
#             """
#             ### SCRAPED TEXT FROM WEBSITE:
#             {page_data}

#             ### INSTRUCTION:
#             The scraped text is from a career page.
#             Extract job postings and return **only a JSON array of objects** with keys: 
#             `role`, `experience`, `skills`, and `description`.
#             Do not add any extra text, explanations, or preamble.
#             """
#         )

#         all_jobs = []
#         json_parser = JsonOutputParser()

#         for idx, chunk in enumerate(self._chunk_text(cleaned_text)):
#             prompt_text = prompt_extract.format(page_data=chunk)
#             try:
#                 res = self.llm.invoke(prompt_text)
                
#                 # Attempt to parse JSON safely
#                 try:
#                     parsed = json_parser.parse(res.content)
#                 except Exception as parse_err:
#                     # Fallback: try to extract JSON manually if parser fails
#                     try:
#                         parsed = json.loads(res.content)
#                     except Exception:
#                         # log bad chunk for debugging
#                         print(f"⚠️ Chunk {idx} could not be parsed:\n{res.content[:500]}")
#                         continue

#                 if isinstance(parsed, list):
#                     all_jobs.extend(parsed)
#                 else:
#                     all_jobs.append(parsed)

#             except Exception as e:
#                 # Skip this chunk but log for debugging
#                 print(f"⚠️ LLM error on chunk {idx}: {e}")
#                 continue

#         if not all_jobs:
#             raise OutputParserException(
#                 "No valid jobs could be parsed from the text. "
#                 "Check your prompt, chunk size, or the website content."
#             )

#         return all_jobs

#     def write_mail(self, job, links):
#         """Generate a cold email from a given job description."""
#         prompt_email = PromptTemplate.from_template(
#             """
#             ### JOB DESCRIPTION:
#             {job_description}

#             ### INSTRUCTION:
#             You are Mohan, a Business Development Executive at AtliQ — an AI & Software Consulting firm helping enterprises 
#             with process automation, optimization, and efficiency. 

#             Write a professional cold email to the client about the above job, highlighting how AtliQ can deliver solutions 
#             to meet their needs. Use the most relevant examples from this portfolio: {link_list}

#             Do not add any preamble.
#             ### EMAIL (NO PREAMBLE):
#             """
#         )

#         job_str = str(job)
#         prompt_text = prompt_email.format(job_description=job_str, link_list=links)

#         res = self.llm.invoke(prompt_text)
#         return res.content
# chains.py
import os
import json
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()


def clean_text(raw_html: str) -> str:
    """Clean HTML content: remove tags, scripts, styles, and extra whitespace."""
    soup = BeautifulSoup(raw_html, "html.parser")
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class Chain:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.3-70b-versatile"
        )

    def _chunk_text(self, text, chunk_size=1500):
        """Splits text into manageable chunks based on word count."""
        words = text.split()
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i:i + chunk_size])

    def extract_jobs(self, raw_text):
        """Extract job info safely from large scraped text with robust parsing."""
        # Clean HTML content
        cleaned_text = clean_text(raw_text)

        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM WEBSITE:
            {page_data}

            ### INSTRUCTION:
            Extract job postings from the text. 
            ONLY return a valid JSON array of objects with keys: 
            `role`, `experience`, `skills`, `description`. 
            Do NOT include any explanations, preambles, or extra text.
            """
        )

        all_jobs = []
        json_parser = JsonOutputParser()

        for idx, chunk in enumerate(self._chunk_text(cleaned_text)):
            prompt_text = prompt_extract.format(page_data=chunk)
            try:
                res = self.llm.invoke(prompt_text)
                output = res.content

                # Debug: show first 500 chars of LLM output
                print(f"DEBUG chunk {idx} output:\n{output[:500]}\n")

                # Attempt parsing
                try:
                    parsed = json_parser.parse(output)
                except Exception:
                    # Quick fix for minor JSON issues
                    try:
                        parsed = json.loads(output.replace("'", '"'))
                    except Exception:
                        print(f"⚠️ Chunk {idx} could not be parsed. Skipping.")
                        continue

                if isinstance(parsed, list):
                    all_jobs.extend(parsed)
                else:
                    all_jobs.append(parsed)

            except Exception as e:
                print(f"⚠️ LLM error on chunk {idx}: {e}")
                continue

        if not all_jobs:
            raise OutputParserException(
                "No valid jobs could be parsed from the text. "
                "Check your prompt, chunk size, or website content."
            )

        return all_jobs

    def write_mail(self, job, links):
        """Generate a cold email from a given job description."""
        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### INSTRUCTION:
            You are Mohan, a Business Development Executive at AtliQ — an AI & Software Consulting firm helping enterprises 
            with process automation, optimization, and efficiency. 

            Write a professional cold email to the client about the above job, highlighting how AtliQ can deliver solutions 
            to meet their needs. Use the most relevant examples from this portfolio: {link_list}

            Do not add any preamble.
            ### EMAIL (NO PREAMBLE):
            """
        )

        job_str = str(job)
        prompt_text = prompt_email.format(job_description=job_str, link_list=links)
        res = self.llm.invoke(prompt_text)
        return res.content

# import os
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

#     def _chunk_text(self, text, chunk_size=8000):
#         """Splits text into manageable chunks based on word count."""
#         words = text.split()
#         for i in range(0, len(words), chunk_size):
#             yield " ".join(words[i:i + chunk_size])

#     def extract_jobs(self, cleaned_text):
#         """Extract job info safely from large scraped text."""
#         prompt_extract = PromptTemplate.from_template(
#             """
#             ### SCRAPED TEXT FROM WEBSITE:
#             {page_data}

#             ### INSTRUCTION:
#             The scraped text is from a career page.
#             Extract job postings and return JSON with keys: `role`, `experience`, `skills`, and `description`.
#             Only return valid JSON (no extra text).
#             """
#         )

#         all_jobs = []
#         json_parser = JsonOutputParser()

#         for chunk in self._chunk_text(cleaned_text):
#             prompt_text = prompt_extract.format(page_data=chunk)

#             try:
#                 res = self.llm.invoke(prompt_text)
#                 parsed = json_parser.parse(res.content)
#                 if isinstance(parsed, list):
#                     all_jobs.extend(parsed)
#                 else:
#                     all_jobs.append(parsed)
#             except Exception:
#                 # Skip bad chunks rather than fail entire job
#                 continue

#         if not all_jobs:
#             raise OutputParserException("No valid jobs could be parsed from the text.")

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
# import os
# from dotenv import load_dotenv
# import streamlit as st
# from langchain_community.document_loaders import WebBaseLoader
# from chains import Chain
# from my_portfolio import Portfolio
# from utils import clean_text

# # Load environment variables
# load_dotenv()
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv
import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
from chains import Chain
from my_portfolio import Portfolio
from utils import clean_text

load_dotenv()


# Configure Streamlit immediately (before any logic)
st.set_page_config(layout="wide", page_title="Cold Email Generator", page_icon="📧")

def create_streamlit_app(llm, portfolio, clean_text):
    st.title("📧 Cold Email Generator")
    st.markdown("Generate cold emails from job descriptions using  AI assistant.")

    # Input field
    url_input = st.text_input("🔗 Enter a Job URL:")
    submit_button = st.button("🚀 Generate Cold Email")

    # Render something before execution (prevents blank screen)
    st.markdown("---")

    if submit_button:
        if not url_input.strip():
            st.warning("⚠️ Please enter a valid URL.")
            return

        try:
            with st.spinner("🌐 Loading job description from the website..."):
                user_agent = os.getenv("USER_AGENT", "Mozilla/5.0")
                loader = WebBaseLoader([url_input], header_template={"User-Agent": user_agent})
                page_content = loader.load().pop().page_content

            with st.spinner("🧹 Cleaning and shortening text..."):
                data = clean_text(page_content)
                # Limit content to avoid LLM context overflow
                if len(data) > 20000:
                    data = data[:20000]

            with st.spinner("💼 Loading portfolio data..."):
                portfolio.load_portfolio()

            with st.spinner("🧠 Extracting job information..."):
                jobs = llm.extract_jobs(data)

            if not jobs:
                st.error("❌ No jobs extracted. Try a different link.")
                return

            for job in jobs[:2]:  # Limit to first 2 jobs
                st.subheader(f"📄 Job: {job.get('role', 'Unknown Role')}")
                skills = job.get('skills', [])
                links = portfolio.query_links(skills)

                with st.spinner("✉️ Generating personalized cold email..."):
                    email = llm.write_mail(job, links)

                st.success("✅ Email generated successfully!")
                st.code(email, language='markdown')

        except Exception as e:
            st.error(f"🚨 An Error Occurred:\n\n{e}")


# ---- MAIN EXECUTION ----
if __name__ == "__main__":
    try:
        chain = Chain()
        portfolio = Portfolio()
        create_streamlit_app(chain, portfolio, clean_text)
    except Exception as e:
        st.error(f"❌ App Initialization Failed: {e}")

import streamlit as st
import anthropic
from dotenv import load_dotenv
import os
import pymupdf

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

st.title("Document Analyser")
st.write("Upload a PDF or text file to get an instant analysis.")

uploaded_file = st.file_uploader("Drop your file here", type=["pdf", "txt"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".pdf"):
        doc = pymupdf.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
    else:
        text = uploaded_file.read().decode("utf-8")

    if st.button("Analyse"):
        with st.spinner("Analysing..."):
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyse the following text and give me:
1. A plain English summary (3-4 sentences)
2. Three key points or risks
3. A suggested action list

Text: {text}"""
                    }
                ]
            )
        st.markdown(message.content[0].text)
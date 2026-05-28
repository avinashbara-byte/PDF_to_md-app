from langchain_core.messages import HumanMessage
import streamlit as st
from pdf2image import convert_from_bytes
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Set API Key
os.environ["GOOGLE_API_KEY"] = "your_gemini_api_key_here"
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

st.title("📝 Multi-Page Handwritten Notes to Markdown")
st.write("Upload a multi-page PDF to clean up and convert all pages.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Use Streamlit's session state so it doesn't re-run on every user click
    if "transcription" not in st.session_state:
        st.info("Processing handwriting across all pages... Please wait.")
        
        # 1. Convert the entire PDF into a list of images (one per page)
        images = convert_from_bytes(uploaded_file.read())
        total_pages = len(images)
        st.write(f"Found {total_pages} page(s). Processing...")

        full_transcription = ""
        
        # 2. Loop through every single page image
        for index, page_image in enumerate(images):
            page_number = index + 1
            st.write(f"Analyzing Page {page_number} of {total_pages}...")
            
            prompt = (
                f"Analyze this image of page {page_number} of handwritten notes. "
                "1. Transcribe it directly into Markdown format. "
                "2. Fix obvious spelling/grammar errors, but keep the original phrasing intact. Minimal changes."
            )
            
            # --- FIXED STRUCTURE FOR MULTIMODAL INPUT ---
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": page_image}  # LangChain handles the PIL image here automatically
                ]
            )
            
            # Send the properly formatted message to the LLM
            response = llm.invoke([message])
            # ---------------------------------------------
            
            # Append this page's transcription to our master file string
            full_transcription += f"\n\n## Page {page_number}\n"
            full_transcription += response.content

        # Save the combined text to the session state
        st.session_state.transcription = full_transcription

        # 3. Generate a summary for the *entire* document
        meta_prompt = (
            "Based on this complete multi-page transcription, write a 2-sentence summary "
            f"and suggest 1 clean filename:\n{st.session_state.transcription}"
        )
        meta_res = llm.invoke(meta_prompt)
        st.session_state.summary = meta_res.content

    # --- UI DISPLAY ---
    st.subheader("📋 Overall Summary")
    st.write(st.session_state.summary)

    st.subheader("✍️ Combined Markdown Content")
    # Using text_area so you can scroll through the entire transcribed document easily
    st.text_area("Review Transcription", st.session_state.transcription, height=300)

    # Filename & Save Button
    custom_filename = st.text_input("Enter your desired filename (without .md):", value="My_Cleaned_Notes")

    st.download_button(
        label="💾 Save Markdown File to iPad",
        data=st.session_state.transcription,
        file_name=f"{custom_filename}.md",
        mime="text/markdown"
    )

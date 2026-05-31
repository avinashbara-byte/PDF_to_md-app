import streamlit as st
from pdf2image import convert_from_bytes
from google import genai

# 1. Setup the Native Google SDK
api_key = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=api_key)

# 2. Define the model
MODEL_ID = 'gemini-2.5-flash'

st.title("📝 Multi-Page Handwritten Notes to Markdown")
st.write("Upload a multi-page PDF to clean up and convert all pages into a continuous document.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Use Streamlit's session state
    if "transcription" not in st.session_state:
        st.info("Processing handwriting across all pages... Please wait.")
        
        images = convert_from_bytes(uploaded_file.read())
        total_pages = len(images)
        st.write(f"Found {total_pages} page(s). Preparing document...")

        prompt = (
            "Analyze these sequential images of handwritten notes from a single document. "
            "1. Transcribe the entire document seamlessly into one continuous Markdown file. "
            "2. Fix obvious spelling/grammar errors, but keep the original phrasing intact. "
            "3. Do NOT artificially separate the text by page number; make the text flow cohesively."
        )
        
        payload = [prompt]
        
        for index, page_image in enumerate(images):
            page_number = index + 1
            st.write(f"Scanning Page {page_number} of {total_pages}...")
            
            clean_image = page_image.convert('RGB')
            clean_image.thumbnail((1600, 1600)) 
            payload.append(clean_image)
            
        st.info("Sending full document to Gemini. Writing continuous file...")

        # Execute transcription
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=payload
        )
        st.session_state.transcription = response.text

        # --- NEW: Strict Metadata Parsing ---
        st.info("Generating summary and intelligent filename...")
        meta_prompt = (
            "Based on the following transcription, provide exactly two things:\n"
            "Line 1: A 2-sentence summary of the document.\n"
            "Line 2: A short, relevant filename (use underscores instead of spaces, no file extension).\n\n"
            f"Transcription:\n{st.session_state.transcription}"
        )
        
        meta_res = client.models.generate_content(
            model=MODEL_ID,
            contents=meta_prompt
        )
        
        # Split the AI's response into lines to separate the summary and the filename
        lines = [line.strip() for line in meta_res.text.strip().split('\n') if line.strip()]
        
        # Safely assign the parsed data
        st.session_state.summary = lines[0] if len(lines) > 0 else "Summary generation failed."
        # Grab the last line, clean out any markdown bolding or labels the AI might have added
        raw_filename = lines[-1] if len(lines) > 1 else "Cleaned_Notes"
        st.session_state.suggested_filename = raw_filename.replace("Filename:", "").replace("**", "").strip()

    # --- UI DISPLAY ---
    st.subheader("📋 Overall Summary")
    st.write(st.session_state.summary)

    st.subheader("✍️ Combined Continuous Markdown Content")
    
    # --- NEW: Native Copy Button ---
    # Using st.code instead of st.text_area provides a built-in "Copy" icon in the top right!
    st.code(st.session_state.transcription, language="markdown")

    # --- NEW: Dynamic Filename Injection ---
    # We pass the AI-generated filename into the 'value' parameter so it pre-fills the box
    custom_filename = st.text_input(
        "Enter your desired filename (without .md):", 
        value=st.session_state.suggested_filename
    )

    st.download_button(
        label="💾 Save Markdown File to iPad",
        data=st.session_state.transcription,
        file_name=f"{custom_filename}.md",
        mime="text/markdown"
    )

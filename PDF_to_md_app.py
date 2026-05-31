import streamlit as st
from pdf2image import convert_from_bytes
from google import genai

# 1. Setup the Native Google SDK (Securely via Streamlit Secrets)
api_key = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=api_key)

# 2. Define the correct, modern model
MODEL_ID = 'gemini-2.5-flash'

st.title("📝 Multi-Page Handwritten Notes to Markdown")
st.write("Upload a multi-page PDF to clean up and convert all pages into a continuous document.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Use Streamlit's session state to prevent reprocessing on every click
    if "transcription" not in st.session_state:
        st.info("Processing handwriting across all pages... Please wait.")
        
        # Convert the PDF into a list of PIL Images
        images = convert_from_bytes(uploaded_file.read())
        total_pages = len(images)
        st.write(f"Found {total_pages} page(s). Preparing document...")

        # 1. Create a single master prompt instructing a seamless merge
        prompt = (
            "Analyze these sequential images of handwritten notes from a single document. "
            "1. Transcribe the entire document seamlessly into one continuous Markdown file. "
            "2. Fix obvious spelling/grammar errors, but keep the original phrasing intact. "
            "3. Do NOT artificially separate the text by page number; make the text flow cohesively."
        )
        
        # 2. Start our payload list with the text prompt
        payload = [prompt]
        
        # 3. Clean and optimize every page image, then bundle them into the payload stack
        for index, page_image in enumerate(images):
            page_number = index + 1
            st.write(f"Scanning Page {page_number} of {total_pages}...")
            
            clean_image = page_image.convert('RGB')
            clean_image.thumbnail((1600, 1600)) 
            
            payload.append(clean_image)
            
        st.info("Sending full document to Gemini. Writing continuous file...")

        # 4. Execute a single API call passing all components simultaneously
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=payload
        )
            
        # Store the continuous response text to session state
        st.session_state.transcription = response.text

        # 5. Generate the document metadata summary
        st.info("Generating summary...")
        meta_prompt = (
            "Based on this complete document transcription, write a 2-sentence summary "
            f"and suggest 1 clean filename:\n{st.session_state.transcription}"
        )
        meta_res = client.models.generate_content(
            model=MODEL_ID,
            contents=meta_prompt
        )
        st.session_state.summary = meta_res.text

    # --- UI DISPLAY ---
    st.subheader("📋 Overall Summary")
    st.write(st.session_state.summary)

    st.subheader("✍️ Combined Continuous Markdown Content")
    st.text_area("Review Transcription", st.session_state.transcription, height=400)

    # Filename & Save Button
    custom_filename = st.text_input("Enter your desired filename (without .md):", value="My_Cleaned_Notes")

    st.download_button(
        label="💾 Save Markdown File to iPad",
        data=st.session_state.transcription,
        file_name=f"{custom_filename}.md",
        mime="text/markdown"
    )

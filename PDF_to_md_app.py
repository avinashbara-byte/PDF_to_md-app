import tempfile
import streamlit as st
from pdf2image import convert_from_bytes
import google.generativeai as genai
import os
from PIL import Image
import io

# 1. Setup the Native Google SDK (Bypassing LangChain completely)
os.environ["GOOGLE_API_KEY"] = "your_gemini_api_key_here" 
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Initialize the model directly
model = genai.GenerativeModel('gemini-2.5-flash')

st.title("📝 Multi-Page Handwritten Notes to Markdown")
st.write("Upload a multi-page PDF to clean up and convert all pages.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Use Streamlit's session state
    if "transcription" not in st.session_state:
        st.info("Processing handwriting across all pages... Please wait.")
        
        # Convert the PDF into a list of PIL Images
        images = convert_from_bytes(uploaded_file.read())
        total_pages = len(images)
        st.write(f"Found {total_pages} page(s). Processing...")

        full_transcription = ""
        
        # Loop through every single page image
        for index, page_image in enumerate(images):
            page_number = index + 1
            st.write(f"Analyzing Page {page_number} of {total_pages}...")
            
            prompt = (
                f"Analyze this image of page {page_number} of handwritten notes. "
                "1. Transcribe it directly into Markdown format. "
                "2. Fix obvious spelling/grammar errors, but keep the original phrasing intact. Minimal changes."
            )
            
            # --- THE FINAL FIX: THE GEMINI FILE API ---
            # 1. Convert to RGB and slightly resize it to process lightning fast
            rgb_image = page_image.convert('RGB')
            rgb_image.thumbnail((1600, 1600)) # Keeps text crisp but shrinks the file size
            
            # 2. Save it to a temporary file on the Streamlit cloud server
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                rgb_image.save(temp_file.name, format="JPEG", quality=85)
                temp_path = temp_file.name
                
            # 3. Upload to Google's robust File API (bypasses all chat size limits)
            uploaded_gemini_file = genai.upload_file(temp_path)
            
            # 4. Generate content using the uploaded file reference instead of raw bytes
            response = model.generate_content([prompt, uploaded_gemini_file])
            
            # 5. Clean up: Delete the temp file from Streamlit to save memory
            os.remove(temp_path)
            # ------------------------------------------
            
            # Append this page's transcription
            full_transcription += f"\n\n## Page {page_number}\n"
            full_transcription += response.text
            
        # Save combined text to session state
        st.session_state.transcription = full_transcription

        # Generate the summary
        meta_prompt = (
            "Based on this complete multi-page transcription, write a 2-sentence summary "
            f"and suggest 1 clean filename:\n{st.session_state.transcription}"
        )
        meta_res = model.generate_content(meta_prompt)
        st.session_state.summary = meta_res.text

    # --- UI DISPLAY ---
    st.subheader("📋 Overall Summary")
    st.write(st.session_state.summary)

    st.subheader("✍️ Combined Markdown Content")
    st.text_area("Review Transcription", st.session_state.transcription, height=300)

    # Filename & Save Button
    custom_filename = st.text_input("Enter your desired filename (without .md):", value="My_Cleaned_Notes")

    st.download_button(
        label="💾 Save Markdown File to iPad",
        data=st.session_state.transcription,
        file_name=f"{custom_filename}.md",
        mime="text/markdown"
    )

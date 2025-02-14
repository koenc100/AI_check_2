import streamlit as st
import base64
import os

def display_pdf(file_path):
    """Read a PDF file and return an iframe embedding the PDF."""
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        return

    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    # Embed the PDF in an iframe
    pdf_display = f"""
    <iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf">
    </iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

def main():
    st.title("Streamlit PDF Viewer Test")
    
    # Specify your PDF file path here
    pdf_file = "sample.pdf"  # Ensure sample.pdf is in your repo
    
    display_pdf(pdf_file)

if __name__ == "__main__":
    main()

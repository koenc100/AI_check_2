import streamlit as st
import base64
import os
import streamlit.components.v1 as components

def display_pdf(pdf_bytes, width=700, height=1000):
    """
    Display a PDF file in the Streamlit app using an iframe.
    
    Parameters:
    - pdf_bytes: PDF file content in bytes.
    - width: Width of the iframe (in pixels).
    - height: Height of the iframe (in pixels).
    """
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_display = f"""
        <iframe src="data:application/pdf;base64,{base64_pdf}" 
                width="{width}" height="{height}" 
                type="application/pdf">
        </iframe>
    """
    # Use components.html to embed the iframe
    components.html(pdf_display, height=height, width=width)

def main():
    st.title("PDF Viewer & Uploader")
    
    st.markdown("## Display a Default PDF")
    default_pdf_path = "sample.pdf"  # Ensure this file is in your repository

    if st.button("Load Default PDF"):
        if os.path.exists(default_pdf_path):
            try:
                with open(default_pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                display_pdf(pdf_bytes)
            except Exception as e:
                st.error(f"Error reading default PDF: {e}")
        else:
            st.error(f"Default PDF not found at {default_pdf_path}.")
    
    st.markdown("---")
    st.markdown("## Upload and Display Your Own PDF")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        try:
            pdf_bytes = uploaded_file.read()
            display_pdf(pdf_bytes)
        except Exception as e:
            st.error(f"Error displaying uploaded PDF: {e}")

if __name__ == "__main__":
    main()

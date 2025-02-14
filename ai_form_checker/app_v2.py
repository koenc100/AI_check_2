import streamlit as st
import pdfplumber
from io import BytesIO
import base64
from checks import PDFChecker
import openai

# OpenAI-client initialiseren
openai.api_key = "sk-..."  # Vervang door je eigen API-key
pdf_checker = PDFChecker(openai)

def display_pdf(pdf_bytes):
    """Embed een PDF in de Streamlit app, gegeven PDF-bytes."""
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = (
        f'<iframe src="data:application/pdf;base64,{base64_pdf}" '
        f'width="100%" height="600" type="application/pdf"></iframe>'
    )
    st.markdown(pdf_display, unsafe_allow_html=True)

def main():
    st.set_page_config(layout="wide")
    st.title("Formulier AI Controle - Meerdere PDF's")

    col1, col2 = st.columns([1, 2])

    with col1:
        uploaded_files = st.file_uploader("Upload een of meerdere PDF's", type=["pdf"], accept_multiple_files=True)

        if uploaded_files:
            if "pdf_data" not in st.session_state:
                st.session_state["pdf_data"] = {}
            
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in st.session_state["pdf_data"]:
                    with pdfplumber.open(uploaded_file) as pdf:
                        all_text = "".join([page.extract_text() or "" for page in pdf.pages])
                    
                    st.session_state["pdf_data"][uploaded_file.name] = {
                        "content": uploaded_file.getvalue(),
                        "text": all_text,
                        "annotated": None,
                    }

            st.markdown("---")
            st.markdown("### Controleer alle documenten")
            if st.button("Voer controle uit op alle PDF's"):
                with st.spinner("Alle PDF's worden gecontroleerd..."):
                    for pdf_name, data in st.session_state["pdf_data"].items():
                        results = pdf_checker.check_all(data["text"], data["content"])
                        data["annotated"] = results["annotated_pdf"]
                        st.session_state["pdf_data"][pdf_name] = data
                        
                    st.success("Alle documenten zijn gecontroleerd!")

    with col2:
        if "pdf_data" in st.session_state and st.session_state["pdf_data"]:
            tab_names = list(st.session_state["pdf_data"].keys())
            selected_tab = st.selectbox("Selecteer een PDF", tab_names)
            pdf_data = st.session_state["pdf_data"][selected_tab]
            
            st.subheader(f"Weergave van: {selected_tab}")
            display_pdf(pdf_data["annotated"] if pdf_data["annotated"] else pdf_data["content"])

if __name__ == "__main__":
    main()

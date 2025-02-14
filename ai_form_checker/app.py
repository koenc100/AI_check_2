import streamlit as st
import pdfplumber
import base64

import openai
from checks import PDFChecker

import sys
sys.stdout.reconfigure(encoding='utf-8')


def display_pdf(pdf_bytes):
    """Embed a PDF in the Streamlit app, given PDF bytes."""
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = (
        f'<iframe src="data:application/pdf;base64,{base64_pdf}" '
        f'width="100%" height="600" type="application/pdf"></iframe>'
    )
    st.markdown(pdf_display, unsafe_allow_html=True)

def main():

    st.set_page_config(layout="wide")
    st.title("Formulier AI Controle (Meerdere PDF's)")

    # Initialize OpenAI
    openai.api_key = "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"
    pdf_checker = PDFChecker(openai)

    col_left, col_right = st.columns([1, 2])

    with col_left:
        uploaded_files = st.file_uploader(
            "Upload een of meer PDF-bestanden",
            type=["pdf"],
            accept_multiple_files=True
        )

        # We store info about each uploaded PDF in a list of dicts
        # Each dict will hold:
        #   {
        #       "filename": str,
        #       "file_bytes": bytes,
        #       "text": str,
        #       "annotated_bytes": bytes or None
        #   }
        pdf_list = []

        if uploaded_files:
            # Extract text from each PDF
            for uploaded_file in uploaded_files:
                pdf_bytes = uploaded_file.read()
                with pdfplumber.open(uploaded_file) as pdf:
                    extracted_text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        extracted_text += page_text + "\n"

                pdf_list.append({
                    "filename": uploaded_file.name,
                    "file_bytes": pdf_bytes,
                    "text": extracted_text,
                    "annotated_bytes": None
                })

            # Combine text for GPT checks
            combined_text = "\n".join([pdf["text"] for pdf in pdf_list])

            # Big "Check All" button
            st.markdown(
                "<div style='text-align: center;'><strong style='font-size: 24px;'>Controleer Alles</strong></div>",
                unsafe_allow_html=True
            )
            check_all_clicked = st.button(
                "##### KLIK HIER OM ALLE CONTROLES UIT TE VOEREN #####",
                use_container_width=True
            )

            if check_all_clicked:
                with st.spinner("Alle checks uitvoeren..."):
                    results = pdf_checker.check_all(combined_text)

                st.subheader("Resultaten van alle checks")

                # Email
                if results["email_found"]:
                    st.success("E-mailadres gedetecteerd.")
                else:
                    st.error("Geen e-mailadres gedetecteerd.")
                if results["email_snippet"]:
                    st.write(f"**Snippet:** {results['email_snippet']}")

                # Full Name
                if results["name_found"]:
                    st.success("Volledige naam gedetecteerd.")
                else:
                    st.error("Geen volledige naam gedetecteerd.")
                if results["name_snippet"]:
                    st.write(f"**Snippet:** {results['name_snippet']}")

                # Future Date
                if results["date_found"]:
                    st.success("Toekomstige datum gedetecteerd.")
                else:
                    st.error("Geen (toekomstige) datum gevonden of datum ontbreekt.")
                if results["date_snippet"]:
                    st.write(f"**Snippet:** {results['date_snippet']}")

                # Budget
                if results["budget_correct"]:
                    st.success("Budget lijkt correct te zijn.")
                else:
                    st.error("Budgetoverzicht niet correct of niet gevonden.")
                if results["budget_snippet"]:
                    st.write(f"**Snippet:** {results['budget_snippet']}")

                # ---------------------------------------
                # Highlight the snippet in each PDF if found
                # We'll do this for each snippet (if any).
                # Each PDF gets its own annotated bytes stored.
                # ---------------------------------------
                for pdf_data in pdf_list:
                    annotated_pdf = pdf_data["file_bytes"]

                    # If any snippet is found, highlight it in the PDF
                    for snippet_key in ["email_snippet", "name_snippet", "date_snippet", "budget_snippet"]:
                        snippet = results[snippet_key]
                        if snippet:
                            annotated_pdf = pdf_checker.highlight_in_pdf(annotated_pdf, snippet)

                    pdf_data["annotated_bytes"] = annotated_pdf

                st.session_state["pdf_list"] = pdf_list

            st.markdown("---")

            st.markdown("### (Optioneel) Individuele checks")

            # Example: check for email only
            if st.button("Controleer op e-mailadres"):
                email_found, snippet = pdf_checker.check_for_email_and_return(combined_text)
                st.subheader("Resultaat e-mailcontrole (alle PDFs)")

                if email_found:
                    st.success("E-mailadres gedetecteerd.")
                else:
                    st.error("Geen e-mailadres gevonden.")
                if snippet:
                    st.write(f"**Snippet:** {snippet}")
                    # Highlight snippet in each PDF
                    for pdf_data in pdf_list:
                        current_pdf = pdf_data["annotated_bytes"] or pdf_data["file_bytes"]
                        annotated_pdf = pdf_checker.highlight_in_pdf(current_pdf, snippet)
                        pdf_data["annotated_bytes"] = annotated_pdf
                    st.session_state["pdf_list"] = pdf_list

                        # Example: check for email only
            if st.button("Check begroting"):
                budget_correct, snippet = pdf_checker.check_budget_correctness_and_return(combined_text)
                st.subheader("Resultaat begrotingscheck")

                if budget_correct:
                    st.success("Begroting succesvol gecheckt")
                else:
                    st.error("Er zit een fout in de begroting, of hij is niet gevonden")
                if snippet:
                    st.write(f"**Snippet:** {snippet}")
                    # Highlight snippet in each PDF
                    for pdf_data in pdf_list:
                        current_pdf = pdf_data["annotated_bytes"] or pdf_data["file_bytes"]
                        annotated_pdf = pdf_checker.highlight_in_pdf(current_pdf, snippet)
                        pdf_data["annotated_bytes"] = annotated_pdf
                    st.session_state["pdf_list"] = pdf_list


            # You can similarly add other individual check buttons (full name, future date, budget)

    # ---------------------------
    # Display PDFs in the right column in tabs
    # ---------------------------
    with col_right:
        st.subheader("Bekijk de PDF-bestanden")
        if "pdf_list" not in st.session_state:
            # If no checks have been performed or PDFs uploaded yet
            if uploaded_files:
                # Show original PDFs in tabs (no highlights)
                tabs = st.tabs([pdf["filename"] for pdf in pdf_list])
                for i, tab in enumerate(tabs):
                    with tab:
                        st.write(f"**Bestand:** {pdf_list[i]['filename']}")
                        display_pdf(pdf_list[i]["file_bytes"])
            else:
                st.info("Nog geen PDF geüpload.")
        else:
            # Show annotated PDFs if available
            pdf_list = st.session_state["pdf_list"]
            tabs = st.tabs([pdf["filename"] for pdf in pdf_list])
            for i, tab in enumerate(tabs):
                with tab:
                    st.write(f"**Bestand:** {pdf_list[i]['filename']}")

                    if pdf_list[i]["annotated_bytes"] is not None:
                        display_pdf(pdf_list[i]["annotated_bytes"])
                    else:
                        display_pdf(pdf_list[i]["file_bytes"])

        if pdf_list:
            show_text = st.button("Show Extracted Text")
            if show_text:
                hide_text = st.button("Hide Extracted Text")
                for pdf in pdf_list:
                    st.subheader(f"Text from: {pdf['filename']}")
                    st.text_area("Extracted Text", pdf["text"], height=300)


if __name__ == "__main__":
    main()

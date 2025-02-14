import streamlit as st
import pdfplumber
import base64
import re
import fitz  # PyMuPDF
from io import BytesIO
from openai import OpenAI
import string

# ---------------------------
# OpenAI client initialization
# ---------------------------
client = OpenAI(
    api_key="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"
)

def display_pdf(pdf_bytes):
    """Embed a PDF in the Streamlit app, given PDF bytes."""
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def highlight_in_pdf(original_pdf_bytes, search_text):
    """
    Highlight the search text in the PDF in a more flexible way.

    1) First, attempt a direct search with TEXT_DEHYPHENATE.
    2) If no matches are found, try a fallback approach:
       - Normalize search_text and the page's text by removing punctuation,
         line breaks, etc.
       - Look for the normalized snippet in the normalized page text.
       - If found, reconstruct the exact substring from the page and highlight.
    """

    if not search_text.strip():
        return original_pdf_bytes

    doc = fitz.open(stream=original_pdf_bytes, filetype="pdf")

    def normalize_text(t):
        t = t.lower()
        t = t.replace('\n', ' ')
        t = t.translate(str.maketrans('', '', string.punctuation))
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    # 1) Direct search
    direct_match_found = False
    for page in doc:
        text_instances = page.search_for(
            search_text,
            quads=False,
            flags=fitz.TEXT_DEHYPHENATE
        )
        if text_instances:
            direct_match_found = True
            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.set_info({"title": "AI Highlight", "content": "Search Text Found"})
                highlight.update()

    if direct_match_found:
        annotated_pdf_bytes = BytesIO()
        doc.save(annotated_pdf_bytes, incremental=False)
        doc.close()
        annotated_pdf_bytes.seek(0)
        return annotated_pdf_bytes.read()

    # 2) Fallback approach
    normalized_snippet = normalize_text(search_text)
    if not normalized_snippet:
        doc.close()
        return original_pdf_bytes

    for page in doc:
        page_text = page.get_text("text")
        normalized_page_text = normalize_text(page_text)

        idx = normalized_page_text.find(normalized_snippet)
        if idx != -1:
            snip_len = len(normalized_snippet)

            parallel_normalized = []
            original_index_map = []

            for i, ch in enumerate(page_text):
                if ch in string.punctuation or ch == '\n':
                    continue

                ch_comp = ch.lower()
                if ch_comp.isspace():
                    if parallel_normalized and parallel_normalized[-1] != ' ':
                        parallel_normalized.append(' ')
                        original_index_map.append(i)
                else:
                    parallel_normalized.append(ch_comp)
                    original_index_map.append(i)

            if idx + snip_len <= len(parallel_normalized):
                start_original_idx = original_index_map[idx]
                end_original_idx = original_index_map[idx + snip_len - 1]
                exact_substring = page_text[start_original_idx:end_original_idx + 1]

                text_instances = page.search_for(
                    exact_substring,
                    quads=False,
                    flags=fitz.TEXT_DEHYPHENATE
                )
                for inst in text_instances:
                    highlight = page.add_highlight_annot(inst)
                    highlight.set_info({"title": "AI Highlight", "content": "Fuzzy Matched Text"})
                    highlight.update()

    annotated_pdf_bytes = BytesIO()
    doc.save(annotated_pdf_bytes, incremental=False)
    doc.close()
    annotated_pdf_bytes.seek(0)
    return annotated_pdf_bytes.read()

# -------------------------------------------------------
#  Helper Functions That Return Boolean and Snippet
# -------------------------------------------------------
def check_for_email_and_return(all_text, client):
    """
    Similar to check_for_email, but returns (bool, snippet).
    True if email found, otherwise False.
    snippet if found, otherwise None.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een assistent die een tekst controleert op e-mailadressen. "
                        "Geef aan of er een e-mailadres in de tekst staat. "
                        "Zo ja, geef: 'Email found: <e-mailadres>' en 'Snippet: <stuk tekst rondom e-mail>'. "
                        "Zo nee, reageer met 'Geen e-mailadres gevonden.'"
                    )
                },
                {
                    "role": "user",
                    "content": f"Controleer of er een e-mailadres staat in de volgende tekst:\n\n{all_text}"
                }
            ]
        )

        answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
        # We'll consider it "found" if "Email found" is in the GPT response
        email_found = "Email found:" in answer

        # Attempt to extract snippet
        snippet_match = re.search(r"Snippet:\s*(.*)", answer)
        snippet = snippet_match.group(1).strip() if snippet_match else None
        return email_found, snippet

    except Exception:
        return False, None
    
def check_for_full_name_and_return(all_text, client):
   
    """
    Checks if a full name is present. Returns (bool, snippet).
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een assistent die een tekst controleert op volledige namen. "
                        "Geef aan of er een volledige naam in de tekst staat. "
                        "Zo ja, geef: 'Name found: <volledige naam>' en 'Snippet: <stuk tekst rondom naam>'. "
                        "Zo nee, reageer met 'Geen volledige naam gevonden.'"
                    )
                },
                {
                    "role": "user",
                    "content": f"Controleer of er een volledige naam staat in de volgende tekst:\n\n{all_text}"
                }
            ]
        )

        answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
        name_found = "Name found:" in answer

        snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE)
        snippet = snippet_match.group(1).strip() if snippet_match else None
        return name_found, snippet

    except Exception:
        return False, None

def check_future_date_and_return(all_text, client):
    """
    Checks if there's a future date in the text. Returns (bool, snippet).
    We'll consider it "found" if GPT says 'in de toekomst' or provides a snippet.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een assistent die datums in tekst verifieert om te controleren "
                        "of ze in de toekomst liggen. Als er een datum voor een toekomstig evenement wordt gevonden, "
                        "geef dan ook 'Snippet: <stuk tekst rondom datum>'."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Bevat de volgende tekst een datum voor een evenement en ligt deze in de toekomst? "
                        "Zo ja, bevestig dat deze geldig en in de toekomst is en geef ook 'Snippet: <stuk tekst rondom datum>'. "
                        "Als de datum in het verleden ligt of ontbreekt, geef dit dan aan.\n\n"
                        f"{all_text}"
                    )
                }
            ]
        )

        answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
        # We'll consider future date found if "in de toekomst" in the answer
        future_date_found = ("in de toekomst" in answer.lower()) and ("snippet:" in answer.lower())

        snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE)
        snippet = snippet_match.group(1).strip() if snippet_match else None

        return future_date_found, snippet

    except Exception:
        return False, None

def check_budget_correctness_and_return(all_text, client):
    """
    Checks if a budget is mentioned and sums up. Returns (bool, snippet).
    We'll consider it correct if GPT says snippet is found and doesn't say "niet klopt" or "verschil".
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een assistent die budgetberekeningen in tekst verifieert. "
                        "Als een begroting wordt gevonden, geef dan ook een snippet van de tekst "
                        "met 'Snippet: <de relevante tekst>'."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Bevat de volgende tekst een budgetoverzicht en een totaalbudget? "
                        "Zo ja, controleer of het totaal overeenkomt met de som van de onderdelen. "
                        "Als het totaal niet klopt, leg dan uit wat het verschil is. "
                        "Voeg ook 'Snippet: <de relevante tekst>' toe.\n\n"
                        f"{all_text}"
                    )
                }
            ]
        )

        answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
        budget_correct = ("snippet:" in answer.lower()) and ("niet klopt" not in answer.lower())

        snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE)
        snippet = snippet_match.group(1).strip() if snippet_match else None

        return budget_correct, snippet

    except Exception:
        return False, None

# -------------------------------------------------------
#  Original check functions (for individual buttons)
# -------------------------------------------------------
def check_for_email(all_text, uploaded_pdf_bytes, client):
    with st.spinner("GPT controleren op e-mailadres..."):
        email_found, snippet = check_for_email_and_return(all_text, client)
        st.subheader("Resultaat e-mailcontrole")
        if email_found:
            st.success("E-mailadres gedetecteerd.")
        else:
            st.error("Geen e-mailadres gevonden.")

        if snippet:
            annotated_pdf_bytes = highlight_in_pdf(uploaded_pdf_bytes, snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            st.write(f"**Snippet:** {snippet}")

def check_for_full_name(all_text, uploaded_pdf_bytes, client):
    with st.spinner("GPT controleren op een volledige naam..."):
        name_found, snippet = check_for_full_name_and_return(all_text, client)
        st.subheader("Resultaat volledige naam controle")
        if name_found:
            st.success("Volledige naam gedetecteerd.")
        else:
            st.error("Geen volledige naam gevonden.")

        if snippet:
            annotated_pdf_bytes = highlight_in_pdf(uploaded_pdf_bytes, snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            st.write(f"**Snippet:** {snippet}")

def check_future_date(all_text, uploaded_pdf_bytes, client):
    with st.spinner("De datum controleren..."):
        date_found, snippet = check_future_date_and_return(all_text, client)
        st.subheader("Resultaat datumcontrole")
        if date_found:
            st.success("Toekomstige datum gedetecteerd.")
        else:
            st.error("Geen (toekomstige) datum gevonden of datum ontbreekt.")

        if snippet:
            annotated_pdf_bytes = highlight_in_pdf(uploaded_pdf_bytes, snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            st.write(f"**Snippet:** {snippet}")

def check_budget_correctness(all_text, uploaded_pdf_bytes, client):
    with st.spinner("Het budget valideren..."):
        budget_correct, snippet = check_budget_correctness_and_return(all_text, client)
        st.subheader("Resultaat budgetcontrole")
        if budget_correct:
            st.success("Budget lijkt correct te zijn.")
        else:
            st.error("Budgetoverzicht niet correct of niet gevonden.")

        if snippet:
            annotated_pdf_bytes = highlight_in_pdf(uploaded_pdf_bytes, snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            st.write(f"**Snippet:** {snippet}")

# -------------------------------------------------------
#  "Check All" Functionality
# -------------------------------------------------------
def check_all(all_text, uploaded_pdf_bytes, client):
    """
    Runs all four checks in sequence.
    If data is found/correct, color green. If not, color red.
    Also print out the snippet if available.
    """

    st.subheader("Resultaten van alle checks")

    # We'll keep track of the current PDF bytes so we can keep adding highlights
    current_pdf_bytes = uploaded_pdf_bytes

    with st.spinner("Alle checks uitvoeren..."):
        # 1) Email
        email_found, email_snippet = check_for_email_and_return(all_text, client)
        if email_found:
            st.success("E-mailadres gedetecteerd.")
        else:
            st.error("Geen e-mailadres gedetecteerd.")
        if email_snippet:
            st.write(f"**Snippet:** {email_snippet}")
            annotated_pdf_bytes = highlight_in_pdf(current_pdf_bytes, email_snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            current_pdf_bytes = annotated_pdf_bytes

        # 2) Full Name
        name_found, name_snippet = check_for_full_name_and_return(all_text, client)
        if name_found:
            st.success("Volledige naam gedetecteerd.")
        else:
            st.error("Geen volledige naam gedetecteerd.")
        if name_snippet:
            st.write(f"**Snippet:** {name_snippet}")
            annotated_pdf_bytes = highlight_in_pdf(current_pdf_bytes, name_snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            current_pdf_bytes = annotated_pdf_bytes

        # 3) Future Date
        date_found, date_snippet = check_future_date_and_return(all_text, client)
        if date_found:
            st.success("Toekomstige datum gedetecteerd.")
        else:
            st.error("Geen (toekomstige) datum gevonden of datum ontbreekt.")
        if date_snippet:
            st.write(f"**Snippet:** {date_snippet}")
            annotated_pdf_bytes = highlight_in_pdf(current_pdf_bytes, date_snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            current_pdf_bytes = annotated_pdf_bytes

        # 4) Budget Correctness
        budget_correct, budget_snippet = check_budget_correctness_and_return(all_text, client)
        if budget_correct:
            st.success("Budget lijkt correct te zijn.")
        else:
            st.error("Budgetoverzicht niet correct of niet gevonden.")
        if budget_snippet:
            st.write(f"**Snippet:** {budget_snippet}")
            annotated_pdf_bytes = highlight_in_pdf(current_pdf_bytes, budget_snippet)
            st.session_state["annotated_pdf"] = annotated_pdf_bytes
            current_pdf_bytes = annotated_pdf_bytes

# -------------------------------------------------------
#  Main App
# -------------------------------------------------------
def main():
    st.set_page_config(layout="wide")
    st.title("Formulier AI Controle")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_file = st.file_uploader("Upload een PDF", type=["pdf"])

        if uploaded_file is not None:
            # Extract all text from PDF
            with pdfplumber.open(uploaded_file) as pdf:
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"

            # --- Big "Check All" button, centered & bigger label ---
            # Simple approach: "larger label" in the text, some HTML to center it.
            st.markdown("<div style='text-align: center;'><strong style='font-size: 24px;'>Controleer Alles</strong></div>", unsafe_allow_html=True)
            check_all_clicked = st.button("##### KLIK HIER OM ALLE CONTROLES UIT TE VOEREN #####",
                                          key="check_all_main",
                                          use_container_width=True)
            if check_all_clicked:
                check_all(all_text, uploaded_file.getvalue(), client)

            st.markdown("---")
            st.markdown("### Individuele checks")

            # --- Smaller individual check buttons ---
            if st.button("Controleer op e-mailadres", key="check_email"):
                check_for_email(all_text, uploaded_file.getvalue(), client)

            if st.button("Controleer op volledige naam", key="check_name"):
                check_for_full_name(all_text, uploaded_file.getvalue(), client)

            if st.button("Controleer of de datum in de toekomst ligt", key="check_date"):
                check_future_date(all_text, uploaded_file.getvalue(), client)

            if st.button("Controleer of het budget klopt", key="check_budget"):
                check_budget_correctness(all_text, uploaded_file.getvalue(), client)

    with col2:
        if uploaded_file is not None:
            st.subheader("Originele of geannoteerde PDF")

            if "annotated_pdf" not in st.session_state:
                st.write("Hier zie je de geüploade PDF (geen highlights):")
                display_pdf(uploaded_file.getvalue())
            else:
                st.write("Hier zie je de PDF met highlights:")
                display_pdf(st.session_state["annotated_pdf"])

if __name__ == "__main__":
    main()

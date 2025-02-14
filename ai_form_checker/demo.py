import streamlit as st
import io
import base64
import re
import openai
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfMerger
from openai import OpenAI
import os

# Stel de pagina in op full width
st.set_page_config(layout="wide")

# Zorg ervoor dat knoppen de volledige breedte benutten
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# PDF-verwerkingsfuncties
# =============================================================================
def merge_pdfs(files):
    """
    Voegt alle geüploade PDF-bestanden samen en extraheert de tekst.
    Retourneert een BytesIO-object met de samengevoegde PDF en de samengevoegde tekst.
    """
    merger = PdfMerger()
    merged_text = ""
    for file in files:
        file.seek(0)
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                merged_text += page_text + "\n"
        file.seek(0)
        merger.append(file)
    merged_pdf = io.BytesIO()
    merger.write(merged_pdf)
    merger.close()
    merged_pdf.seek(0)
    return merged_pdf, merged_text

def display_pdf(pdf_bytes):
    """
    Converteert een PDF (als BytesIO) naar een base64-gecodeerde iframe-weergave.
    De parameter '#zoom=page-fit' zorgt ervoor dat de PDF volledig in het frame past.
    """
    pdf_data = pdf_bytes.getvalue()
    base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#zoom=page-fit" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def annotate_pdf(original_pdf_bytes, terms):
    """
    Zoekt de gegeven termen in de PDF en voegt highlight-annotaties toe.
    Retourneert een BytesIO-object met de geannoteerde PDF.
    """
    pdf_stream = io.BytesIO(original_pdf_bytes)
    doc = fitz.open(stream=pdf_stream.read(), filetype="pdf")
    for page in doc:
        for term in terms:
            text_instances = page.search_for(term)
            for inst in text_instances:
                annot = page.add_highlight_annot(inst)
                annot.set_colors(stroke=(1, 1, 0))  # geel
                annot.update()
    annotated_pdf = io.BytesIO()
    doc.save(annotated_pdf)
    annotated_pdf.seek(0)
    return annotated_pdf

# =============================================================================
# CHECKS: Gesorteerd per categorie
# =============================================================================
old_data_checks = False

if old_data_checks:

    # --- Oude regex-gebaseerde functies ---
    def check_huisnummer(text):
        pattern = r"Huisnummer\s*:?\s*(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group(0)
        else:
            return False, "Huisnummer niet gevonden of ongeldig."

    def check_telefoonnummer(text):
        pattern = r"Telefoonnummer\s*:?\s*((?:06|\+31\s*6|0031\s*6)[-\s]?\d{8})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group(0)
        else:
            return False, "Telefoonnummer niet gevonden of ongeldig."

    def check_email(text):
        pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        match = re.search(pattern, text)
        if match:
            return True, match.group(0)
        else:
            return False, "E-mailadres niet gevonden."

    def check_kvk(text):
        pattern = r"\bkvk(?:-nummer)?\s*:?\s*(\d{8})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return True, match.group(1)
        else:
            return False, "KvK-nummer niet gevonden."

else:
    def check_huisnummer(all_text, uploaded_pdf_bytes, client):
        """
        Controleert met GPT of er een huisnummer in de tekst staat.
        Als gevonden, wordt de bijbehorende snippet gebruikt om de PDF te annoteren.
        Retourneert (True, snippet) bij succes, anders (False, foutmelding).
        """
        with st.spinner("GPT controleren op huisnummer..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Je bent een assistent die een tekst controleert op een huisnummer. "
                                "Geef aan of er een huisnummer in de tekst staat. "
                                "Als er een huisnummer gevonden wordt, geef dan: 'Snippet: <stuk tekst rondom huisnummer>'."
                                "Als er geen huisnummer gevonden wordt, reageer met 'Geen huisnummer gevonden.''"
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Controleer de volgende tekst op een huisnummer:\n\n{all_text}"
                        }
                    ]
                )
                answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
                st.subheader("Resultaat huisnummercontrole")

                snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE | re.DOTALL)
                if snippet_match:
                    snippet = snippet_match.group(1).strip()
                    annotated_pdf_bytes = annotate_pdf(uploaded_pdf_bytes, [snippet])
                    st.session_state["annotated_pdf"] = annotated_pdf_bytes
                    #st.success(f"Huisnummer: {snippet}")
                    return True, snippet
                else:
                    # st.error("Geen huisnummer gevonden.")
                    return False, "Geen huisnummer gevonden."
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {e}")
                return False, f"Er is een fout opgetreden: {e}"

    def check_telefoonnummer(all_text, uploaded_pdf_bytes, client):
        """
        Controleert met GPT of er een telefoonnummer in de tekst staat.
        Een geldig telefoonnummer begint doorgaans met 06, +31 6 of 0031 6 en bevat 8 cijfers.
        Bij succes wordt de PDF geannoteerd met de snippet.
        Retourneert (True, snippet) bij succes, anders (False, foutmelding).
        """
        with st.spinner("GPT controleren op telefoonnummer..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Je bent een assistent die een tekst controleert op een telefoonnummer. "
                                "Een geldig telefoonnummer begint meestal met 06, +31 6 of 0031 6 en bevat 8 cijfers. "
                                "Geef aan of er een telefoonnummer in de tekst staat. "
                                "Als er een telefoonnummer gevonden wordt, geef dan: 'Telefoonnummer found: <telefoonnummer>' "
                                "en 'Snippet: <stuk tekst rondom telefoonnummer>'. "
                                "Als er geen telefoonnummer gevonden wordt, reageer met 'Geen telefoonnummer gevonden.'"
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Controleer de volgende tekst op een telefoonnummer:\n\n{all_text}"
                        }
                    ]
                )
                answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
                st.subheader("Resultaat telefoonnummercontrole")

                snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE | re.DOTALL)
                if snippet_match:
                    snippet = snippet_match.group(1).strip()
                    annotated_pdf_bytes = annotate_pdf(uploaded_pdf_bytes, [snippet])
                    st.session_state["annotated_pdf"] = annotated_pdf_bytes
                    st.success(f"Telefoonnummer: {snippet}")
                    return True, snippet
                else:
                    st.error("Geen telefoonnummer gevonden.")
                    return False, "Geen telefoonnummer gevonden."
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {e}")
                return False, f"Er is een fout opgetreden: {e}"

    def check_email(all_text, uploaded_pdf_bytes, client):
        """
        Controleert met GPT of er een e-mailadres in de tekst staat.
        Bij succes wordt de PDF geannoteerd met de snippet.
        Retourneert (True, snippet) bij succes, anders (False, foutmelding).
        """
        with st.spinner("GPT controleren op e-mailadres..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Je bent een assistent die een tekst controleert op e-mailadressen. "
                                "Geef aan of er een e-mailadres in de tekst staat. "
                                "Als er een e-mailadres gevonden wordt, geef dan: 'Email found: <e-mailadres>' "
                                "en 'Snippet: <stuk tekst rondom e-mail>'. "
                                "Als er geen e-mailadres gevonden wordt, reageer met 'Geen e-mailadres gevonden.'"
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Controleer de volgende tekst op een e-mailadres:\n\n{all_text}"
                        }
                    ]
                )
                answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
                st.subheader("Resultaat e-mailcontrole")

                snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE | re.DOTALL)
                if snippet_match:
                    snippet = snippet_match.group(1).strip()
                    annotated_pdf_bytes = annotate_pdf(uploaded_pdf_bytes, [snippet])
                    st.session_state["annotated_pdf"] = annotated_pdf_bytes
                    #st.success(f"E-mailadres: {snippet}")
                    return True, snippet
                else:
                    st.error("Geen e-mailadres gevonden.")
                    return False, "Geen e-mailadres gevonden."
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {e}")
                return False, f"Er is een fout opgetreden: {e}"

    def check_kvk(all_text, uploaded_pdf_bytes, client):
        """
        Controleert met GPT of er een KvK-nummer in de tekst staat.
        Een geldig KvK-nummer bestaat uit precies 8 cijfers.
        Bij succes wordt de PDF geannoteerd met de snippet.
        Retourneert (True, snippet) bij succes, anders (False, foutmelding).
        """
        with st.spinner("GPT controleren op KvK-nummer..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Je bent een assistent die een tekst controleert op een KvK-nummer. "
                                "Een geldig KvK-nummer bestaat uit precies 8 cijfers. "
                                "Geef aan of er een KvK-nummer in de tekst staat. "
                                "Als er een KvK-nummer gevonden wordt, geef dan: 'KvK found: <KvK-nummer>' "
                                "en 'Snippet: <stuk tekst rondom KvK-nummer>'. "
                                "Als er geen KvK-nummer gevonden wordt, reageer met 'Geen KvK-nummer gevonden.'"
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Controleer de volgende tekst op een KvK-nummer:\n\n{all_text}"
                        }
                    ]
                )
                answer = response.choices[0].message.content if response.choices else "Geen geldig antwoord van GPT."
                st.subheader("Resultaat KvK-nummercontrole")

                snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE | re.DOTALL)
                if snippet_match:
                    snippet = snippet_match.group(1).strip()
                    annotated_pdf_bytes = annotate_pdf(uploaded_pdf_bytes, [snippet])
                    st.session_state["annotated_pdf"] = annotated_pdf_bytes
                    #st.success(f"KvK-nummer: {snippet}")
                    return True, snippet
                else:
                    st.error("Geen KvK-nummer gevonden.")
                    return False, "Geen KvK-nummer gevonden."
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {e}")
                return False, f"Er is een fout opgetreden: {e}"

# ----- 2. Taal technische Checks -----

def check_taal(text, client):
    prompt = (
        "Lees de volgende tekst en geef een neutrale beschrijving van de taaltechnische kwaliteit, inclusief opmerkingen over helderheid en grammatica, zonder waardeoordeel. "
        "Geef eventueel suggesties in een neutrale toon.\n\n"
        f"Tekst:\n{text[:1000]}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij taalcheck: {str(e)}"

def check_schrijfstijl(text, client):
    prompt = (
        "Lees de volgende tekst en geef een neutrale beschrijving van de schrijfstijl, "
        "inclusief opmerkingen over consistentie en helderheid, zonder waardeoordeel.\n\n"
        f"Tekst:\n{text[:1000]}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij schrijfstijlcheck: {str(e)}"

# ----- 3. Inhoudelijke checks -----

def check_promotieplan_duration(text, client):
    prompt = (
        "Lees de onderstaande subsidieaanvraagtekst en zoek naar het gedeelte dat betrekking heeft op het promotieplan. "
        "Zoek specifiek naar de informatie over de duur van dit plan, die in weken of maanden vermeld kan worden. "
        "Geef je antwoord exact in de volgende vorm: 'Promotieplan duur: X weken' of 'Promotieplan duur: X maanden'. "
        "Indien de duur minder is dan 6 weken of minder dan 2 maanden, voeg dan '(aan de korte kant)' toe. "
        "Geef alleen de relevante duur en eventuele beoordeling terug, zonder extra toelichting.\n\n"
        "Tekst:\n" + text[:1500]
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij promotieplan duur check: {str(e)}"


def check_promotieplan_contents(text, client):
    prompt = (
        "Lees de volgende subsidieaanvraagtekst en identificeer het gedeelte dat betrekking heeft op het promotieplan. "
        "Geef een neutrale beschrijving van de inhoud: noteer welke details, doelen en acties er worden vermeld. "
        "Antwoord bijvoorbeeld: 'Promotieplan bevat details over marketingkanalen, doelgroep en planning.'\n\n"
        "Tekst:\n" + text[:1500]
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij promotieplan inhoud check: {str(e)}"

def summarize_promotieplan(text, client):
    prompt = (
        "Lees de volgende subsidieaanvraagtekst en identificeer het gedeelte dat betrekking heeft op het promotieplan. "
        "Vat dit gedeelte samen in een neutrale samenvatting van maximaal 200 woorden.\n\n"
        "Tekst:\n" + text[:1500]
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{summary}</span>'
    except Exception as e:
        return False, f"Fout bij samenvatting promotieplan: {str(e)}"

def check_activiteitenplan_duration(text, client):
    prompt = (
        "Lees de volgende subsidieaanvraagtekst en probeer het gedeelte te vinden dat betrekking heeft op het activiteitenplan. "
        "Geef een neutrale beschrijving van de vermelde duur (bijvoorbeeld een schema per week of per maand) en vermeld de lengte. "
        "Als het plan minder dan 6 weken duurt, vermeld dan dat het aan de korte kant is. "
        "Antwoord bijvoorbeeld: 'Activiteitenplan duur: 10 weken' of 'Activiteitenplan duur: 5 weken (aan de korte kant)'.\n\n"
        "Tekst:\n" + text[:1500]
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij activiteitenplan duur check: {str(e)}"

def check_activiteitenplan_contents(text, client):
    prompt = (
        "Lees de volgende subsidieaanvraagtekst en identificeer het gedeelte dat betrekking heeft op het activiteitenplan. "
        "Geef een neutrale beschrijving van de inhoud: noteer welke details, doelen en acties er worden vermeld. "
        "Antwoord bijvoorbeeld: 'Activiteitenplan bevat informatie over planning, uitvoering en betrokken partijen.'\n\n"
        "Tekst:\n" + text[:1500]
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij activiteitenplan inhoud check: {str(e)}"

def summarize_activiteitenplan(text, client):
    prompt = (
        "Lees de volgende subsidieaanvraagtekst en identificeer het gedeelte dat betrekking heeft op het activiteitenplan. "
        "Vat dit gedeelte samen in een neutrale samenvatting van maximaal 200 woorden.\n\n"
        "Tekst:\n" + text[:1500]
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{summary}</span>'
    except Exception as e:
        return False, f"Fout bij samenvatting activiteitenplan: {str(e)}"

# ----- 4. Financiële Validatie -----
def check_calculations(text):
    if re.search(r'\btotaal\b', text, re.IGNORECASE):
        return True, "Berekeningen gevonden."
    else:
        return False, "Berekeningen ontbreken of onduidelijk."

def check_costs_subsidy_connection(text):
    lower_text = text.lower()
    if "kosten" in lower_text and "subsidie" in lower_text:
        return True, "Koppeling tussen kosten en subsidie gevonden."
    else:
        return False, "Geen duidelijke koppeling tussen kosten en subsidie."

# ----- 5. Extra Validatie & Feedback -----
def check_extra_comments(text, client):
    prompt = (
        "Lees de volgende tekst en geef een neutrale samenvatting van eventuele aanvullende opmerkingen of suggesties voor dit document.\n\n"
        f"Tekst:\n{text[:1000]}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij extra opmerkingen check: {str(e)}"

def check_readability_completeness(text, client):
    prompt = (
        "Lees de volgende tekst en geef een neutrale beschrijving van de leesbaarheid en volledigheid van dit document, "
        "inclusief eventuele feedback en verbeterpunten.\n\n"
        f"Tekst:\n{text[:1000]}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        return True, f'<span style="color:blue">{result}</span>'
    except Exception as e:
        return False, f"Fout bij leesbaarheidscheck: {str(e)}"

# =============================================================================
# Dictionaries per categorie (eenvoudig uit te breiden)
# =============================================================================
# 1. Gegevens check (op basis van tekst)
gegevens_checks = {
    "Huisnummer validiteit": check_huisnummer,            
    "Telefoonnummer validiteit": check_telefoonnummer,      
    "E-mailadres validiteit": check_email,                  
    "KvK-nummer validiteit": check_kvk                      
}

# 2. Taal technische Checks
taal_checks = {
    "Taal check": check_taal,              
    "Schrijfstijl check": check_schrijfstijl  
}

# 3. Inhoudelijke checks
inhoud_checks = {
    "Promotieplan duur check": check_promotieplan_duration,           
    "Promotieplan inhoud check": check_promotieplan_contents,           
    "Promotieplan samenvatting": summarize_promotieplan,                
    "Activiteitenplan duur check": check_activiteitenplan_duration,    
    "Activiteitenplan inhoud check": check_activiteitenplan_contents,    
    "Activiteitenplan samenvatting": summarize_activiteitenplan         
}

# 4. Financiële Validatie
financial_checks = {
    "Berekeningen check": check_calculations,                  
    "Kosten-Subsidie connectie": check_costs_subsidy_connection   
}

# 5. Extra Validatie & Feedback
extra_checks = {
    "Aanvullende opmerkingen": check_extra_comments,           
    "Leesbaarheid & volledigheid": check_readability_completeness 
}

# =============================================================================
# Hoofdprogramma (Streamlit app)
# =============================================================================
def main():
    st.title("Demo: Versnellen Subsidieaanvragen met LM's")
    
    # Stel de OpenAI API-sleutel in
    if "OPENAI_API_KEY" in st.secrets:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
    else:
        st.warning("OpenAI API-sleutel niet gevonden in st.secrets. Sommige taalchecks werken mogelijk niet.")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Maak twee kolommen: links voor upload & checkknoppen, rechts voor resultaatoverzicht.
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.header("Document Upload & Initiële Verwerking")
        uploaded_files = st.file_uploader("Upload PDF documenten", type="pdf", accept_multiple_files=True)
        if uploaded_files:
            st.session_state['uploaded_files'] = uploaded_files
            merged_pdf, merged_text = merge_pdfs(uploaded_files)
            st.session_state['merged_text'] = merged_text
            # Bewaar de originele PDF-bytes (als bytes) voor herhaalde annotaties
            st.session_state['original_pdf_bytes'] = merged_pdf.getvalue()
            # Begin met een ongewijzigde annotatie (omgezet naar BytesIO)
            st.session_state['annotated_pdf'] = io.BytesIO(st.session_state['original_pdf_bytes'])
            st.session_state['highlight_terms'] = []
            st.success("PDF documenten samengevoegd en tekst geëxtraheerd.")
        
        st.markdown("---")
        # ----- 1. Gegevens check (op basis van tekst)
        st.subheader("Gegevens check (op basis van tekst)")
        if st.button("Run alle checks voor Gegevens check"):
            if uploaded_files and 'merged_text' in st.session_state:
                results = {}
                # Let op: de nieuwe functies vereisen drie parameters.
                for label, func in gegevens_checks.items():
                    res, detail = func(
                        st.session_state['merged_text'],
                        st.session_state['original_pdf_bytes'],
                        client
                    )
                    results[label] = (res, detail)
                st.session_state['gegevens_results'] = results
                st.success("Gegevens check uitgevoerd.")
            else:
                st.error("Upload eerst PDF documenten en verwerk de tekst.")
        show_gegevens = st.checkbox("Toon individuele checks voor Gegevens check")
        if show_gegevens:
            for label, func in gegevens_checks.items():
                if st.button(f"Check {label}"):
                    if not uploaded_files or 'merged_text' not in st.session_state:
                        st.error("Upload eerst PDF documenten.")
                    else:
                        res, detail = func(
                            st.session_state['merged_text'],
                            st.session_state['original_pdf_bytes'],
                            client
                        )
                        if res:
                            st.success(f"{label} geslaagd! \n {detail}")
                            st.session_state['highlight_terms'] = [str(detail)]
                            st.session_state['annotated_pdf'] = annotate_pdf(
                                st.session_state['original_pdf_bytes'],
                                st.session_state['highlight_terms']
                            )
                        else:
                            st.error(f"{label} mislukt: {detail}")
        
        st.markdown("---")
        # ----- 2. Taal technische Checks
        st.subheader("Taal technische Checks")
        if st.button("Run alle checks voor Taal technische Checks"):
            if 'merged_text' in st.session_state:
                results = {}
                for label, func in taal_checks.items():
                    res, detail = func(st.session_state['merged_text'], client)
                    results[label] = (res, detail)
                st.session_state['taal_results'] = results
                st.success("Taal technische checks uitgevoerd.")
            else:
                st.error("Upload eerst PDF documenten.")
        show_taal = st.checkbox("Toon individuele checks voor Taal technische Checks")
        if show_taal:
            for label, func in taal_checks.items():
                if st.button(f"Check {label}"):
                    if 'merged_text' not in st.session_state:
                        st.error("Upload eerst PDF documenten.")
                    else:
                        res, detail = func(st.session_state['merged_text'], client)
                        if res:
                            st.success(f"{label} geslaagd: {detail}")
                            st.session_state['highlight_terms'] = [str(detail)]
                            st.session_state['annotated_pdf'] = annotate_pdf(
                                st.session_state['original_pdf_bytes'],
                                st.session_state['highlight_terms']
                            )
                        else:
                            st.error(f"{label} mislukt: {detail}")
        
        st.markdown("---")
        # ----- 3. Inhoudelijke checks
        st.subheader("Inhoudelijke checks")
        if st.button("Run alle checks voor Inhoudelijke checks"):
            if 'merged_text' in st.session_state:
                results = {}
                for label, func in inhoud_checks.items():
                    try:
                        res, detail = func(st.session_state['merged_text'], client)
                    except TypeError:
                        res, detail = func(st.session_state['merged_text'])
                    results[label] = (res, detail)
                st.session_state['inhoud_results'] = results
                st.success("Inhoudelijke checks uitgevoerd.")
            else:
                st.error("Upload eerst PDF documenten.")
        show_inhoud = st.checkbox("Toon individuele checks voor Inhoudelijke checks")
        if show_inhoud:
            for label, func in inhoud_checks.items():
                if st.button(f"Check {label}"):
                    if 'merged_text' not in st.session_state:
                        st.error("Upload eerst PDF documenten.")
                    else:
                        try:
                            res, detail = func(st.session_state['merged_text'], client)
                        except TypeError:
                            res, detail = func(st.session_state['merged_text'])
                        if res:
                            st.success(f"{label} geslaagd: {detail}")
                            st.session_state['highlight_terms'] = [str(detail)]
                            st.session_state['annotated_pdf'] = annotate_pdf(
                                st.session_state['original_pdf_bytes'],
                                st.session_state['highlight_terms']
                            )
                        else:
                            st.error(f"{label} mislukt: {detail}")
        
        st.markdown("---")
        # ----- 4. Financiële Validatie
        st.subheader("Financiële Validatie")
        if st.button("Run alle checks voor Financiële Validatie"):
            if 'merged_text' in st.session_state:
                results = {}
                for label, func in financial_checks.items():
                    res, detail = func(st.session_state['merged_text'])
                    results[label] = (res, detail)
                st.session_state['financial_results'] = results
                st.success("Financiële Validatie checks uitgevoerd.")
            else:
                st.error("Upload eerst PDF documenten.")
        show_financial = st.checkbox("Toon individuele checks voor Financiële Validatie")
        if show_financial:
            for label, func in financial_checks.items():
                if st.button(f"Check {label}"):
                    if 'merged_text' not in st.session_state:
                        st.error("Upload eerst PDF documenten.")
                    else:
                        res, detail = func(st.session_state['merged_text'])
                        if res:
                            st.success(f"{label} geslaagd: {detail}")
                            st.session_state['highlight_terms'] = [str(detail)]
                            st.session_state['annotated_pdf'] = annotate_pdf(
                                st.session_state['original_pdf_bytes'],
                                st.session_state['highlight_terms']
                            )
                        else:
                            st.error(f"{label} mislukt: {detail}")
        
        st.markdown("---")
        # ----- 5. Extra Validatie & Feedback
        st.subheader("Extra Validatie & Feedback")
        if st.button("Run alle checks voor Extra Validatie & Feedback"):
            if 'merged_text' in st.session_state:
                results = {}
                for label, func in extra_checks.items():
                    res, detail = func(st.session_state['merged_text'], client)
                    results[label] = (res, detail)
                st.session_state['extra_results'] = results
                st.success("Extra Validatie & Feedback checks uitgevoerd.")
            else:
                st.error("Upload eerst PDF documenten.")
        show_extra = st.checkbox("Toon individuele checks voor Extra Validatie & Feedback")
        if show_extra:
            for label, func in extra_checks.items():
                if st.button(f"Check {label}"):
                    if 'merged_text' not in st.session_state:
                        st.error("Upload eerst PDF documenten.")
                    else:
                        res, detail = func(st.session_state['merged_text'], client)
                        if res:
                            st.success(f"{label} geslaagd:")
                            st.write(detail)
                            st.session_state['highlight_terms'] = [str(detail)]
                            st.session_state['annotated_pdf'] = annotate_pdf(
                                st.session_state['original_pdf_bytes'],
                                st.session_state['highlight_terms']
                            )
                        else:
                            st.error(f"{label} mislukt: {detail}")
        
    # =============================================================================
    # Rechter kolom: Overzicht van de geannoteerde PDF en alle checkresultaten
    # =============================================================================
    with right_col:
        st.header("Overzicht Documenten en Resultaten")
        if 'annotated_pdf' in st.session_state:
            st.markdown("### Samengevoegde PDF met highlights")
            display_pdf(st.session_state['annotated_pdf'])
            
            st.markdown("---")
            st.header("Check Resultaten")
            
            if 'gegevens_results' in st.session_state:
                st.markdown("#### Gegevens check:")
                for label, (res, detail) in st.session_state['gegevens_results'].items():
                    if res:
                        st.success(f"{label}: {detail}")
                    else:
                        st.error(f"{label}: {detail}")
            
            if 'taal_results' in st.session_state:
                st.markdown("#### Taal technische Checks:")
                for label, (res, detail) in st.session_state['taal_results'].items():
                    if res:
                        st.success(f"{label}: {detail}")
                    else:
                        st.error(f"{label}: {detail}")
            
            if 'inhoud_results' in st.session_state:
                st.markdown("#### Inhoudelijke checks:")
                for label, (res, detail) in st.session_state['inhoud_results'].items():
                    if res:
                        st.success(f"{label}: {detail}")
                    else:
                        st.error(f"{label}: {detail}")
            
            if 'financial_results' in st.session_state:
                st.markdown("#### Financiële Validatie:")
                for label, (res, detail) in st.session_state['financial_results'].items():
                    if res:
                        st.success(f"{label}: {detail}")
                    else:
                        st.error(f"{label}: {detail}")
            
            if 'extra_results' in st.session_state:
                st.markdown("#### Extra Validatie & Feedback:")
                for label, (res, detail) in st.session_state['extra_results'].items():
                    if res:
                        st.success(f"{label}:")
                        st.write(detail)
                    else:
                        st.error(f"{label}: {detail}")
        else:
            st.info("Upload PDF documenten in de linker kolom en voer de checks uit.")

if __name__ == '__main__':
    main()

import streamlit as st
import pdfplumber
from openai import OpenAI
import base64

# OpenAI client initialization
client = OpenAI(
    api_key="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"
)

def display_pdf(uploaded_file):
    # Read the PDF file
    base64_pdf = base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
    
    # Embedding PDF in HTML
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    
    st.markdown(pdf_display, unsafe_allow_html=True)

def main():
    # Set page configuration to wider layout
    st.set_page_config(layout="wide")

    # Title
    st.title("Formulier Controle Controle")

    # Two-column layout
    col1, col2 = st.columns([1, 1])

    with col1:
        # Description
        st.text(
            "Welkom bij de Formulier Controle Tool! Ben je het zat om alle specifieke informatie in een formulier zelf te moeten controleren? "
            "Wil je niet alles woord voor woord nalopen? Dat hoeft nu niet meer! Upload gewoon het formulier dat je wilt controleren, "
            "kies wat je wilt laten controleren en ontvang snel mogelijke correcties."
        )

        # PDF Uploader
        uploaded_file = st.file_uploader("Upload een PDF", type=["pdf"])

        # Process uploaded PDF
        if uploaded_file is not None:
            with pdfplumber.open(uploaded_file) as pdf:
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"

            # Extracted Text
            st.subheader("(1) Geëxtraheerde tekst uit PDF")
            st.text_area("Hieronder tonen we een platte versie van de tekst in de geüploade PDF.", all_text, height=200)

            # Check Email Button
            if st.button("Controleer op e-mailadres"):
                with st.spinner("GPT controleren op een e-mailadres..."):
                    try:
                        # GPT checks for email
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Je bent een assistent die een tekst controleert op e-mailadressen."
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        "Bevat de volgende tekst een e-mailadres? "
                                        "Zo ja, haal het eruit. Zo nee, reageer met 'Geen e-mailadres gevonden.'\n\n"
                                        f"{all_text}"
                                    )
                                }
                            ]
                        )
                        if response.choices and response.choices[0].message:
                            answer = response.choices[0].message.content
                        else:
                            answer = "Geen geldig antwoord van GPT."
                        st.subheader("Resultaat e-mailcontrole")
                        st.write(answer)
                    except Exception as e:
                        st.error(f"Er is een fout opgetreden: {e}")

            # Knop 2: Controleer of er een volledige naam in de tekst staat
            if st.button("Controleer op volledige naam"):
                with st.spinner("GPT controleren op een volledige naam..."):
                    try:
                        # GPT controleert op een volledige naam
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Je bent een assistent die een tekst controleert op volledige namen."
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        "Bevat de volgende tekst een volledige naam (voornaam en achternaam)? "
                                        "Zo ja, haal deze eruit. Zo nee, reageer met 'Geen volledige naam gevonden.'\n\n"
                                        f"{all_text}"
                                    )
                                }
                            ]
                        )
                        if response.choices and response.choices[0].message:
                            answer = response.choices[0].message.content
                        else:
                            answer = "Geen geldig antwoord van GPT."
                        st.subheader("Resultaat volledige naam controle")
                        st.write(answer)
                    except Exception as e:
                        st.error(f"Er is een fout opgetreden: {e}")

            # Knop 3: Controleer of de datum in de toekomst ligt
            if st.button("Controleer of de datum in de toekomst ligt"):
                with st.spinner("De datum controleren..."):
                    try:
                        # GPT controleert of de datum in de toekomst ligt
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Je bent een assistent die datums in tekst verifieert om te controleren of ze in de toekomst liggen."
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        "Bevat de volgende tekst een datum voor een evenement en ligt deze in de toekomst? "
                                        "Zo ja, bevestig dat deze geldig en in de toekomst is. "
                                        "Als de datum in het verleden ligt of ontbreekt, geef dit dan aan.\n\n"
                                        f"{all_text}"
                                    )
                                }
                            ]
                        )
                        if response.choices and response.choices[0].message:
                            answer = response.choices[0].message.content
                        else:
                            answer = "Geen geldig antwoord van GPT."
                        st.subheader("Resultaat datumcontrole")
                        st.write(answer)
                    except Exception as e:
                        st.error(f"Er is een fout opgetreden: {e}")

            # Knop 4: Controleer of het budget klopt
            if st.button("Controleer of het budget klopt"):
                with st.spinner("Het budget valideren..."):
                    try:
                        # GPT controleert of de begroting klopt
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Je bent een assistent die budgetberekeningen in tekst verifieert."
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        "Bevat de volgende tekst een budgetoverzicht en een totaalbudget? "
                                        "Zo ja, controleer of het totaal overeenkomt met de som van de onderdelen. "
                                        "Als het totaal niet klopt, leg dan uit wat het verschil is.\n\n"
                                        f"{all_text}"
                                    )
                                }
                            ]
                        )
                        if response.choices and response.choices[0].message:
                            answer = response.choices[0].message.content
                        else:
                            answer = "Geen geldig antwoord van GPT."
                        st.subheader("Resultaat budgetcontrole")
                        st.write(answer)
                    except Exception as e:
                        st.error(f"Er is een fout opgetreden: {e}")

            # Knop 5: Controleer of het aantal deelnemers past bij het budget
            if st.button("Controleer of deelnemers passen bij het budget"):
                with st.spinner("Deelnemers en budget evalueren..."):
                    try:
                        # GPT controleert of het aantal deelnemers redelijk is voor het budget
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {
                                    "role": "system",
                                    "content": "Je bent een assistent die evalueert of het verwachte aantal deelnemers overeenkomt met het budget voor een evenement."
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        "Wordt in de volgende tekst een totaalbudget en het verwachte aantal deelnemers vermeld? "
                                        "Zo ja, beoordeel of het budget redelijk lijkt voor het genoemde aantal deelnemers. "
                                        "Geef een uitleg bij je conclusie.\n\n"
                                        f"{all_text}"
                                    )
                                }
                            ]
                        )
                        if response.choices and response.choices[0].message:
                            answer = response.choices[0].message.content
                        else:
                            answer = "Geen geldig antwoord van GPT."
                        st.subheader("Resultaat deelnemers vs. budget controle")
                        st.write(answer)
                    except Exception as e:
                        st.error(f"Er is een fout opgetreden: {e}")

    with col2:
        # Display uploaded PDF
        if uploaded_file is not None:
            st.subheader("Geüploade PDF")
            st.write("Hier zie je de geüploade PDF:")
            display_pdf(uploaded_file)

if __name__ == "__main__":
    main()
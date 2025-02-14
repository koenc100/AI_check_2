import re
import string
import base64
from io import BytesIO

import fitz  # PyMuPDF

class PDFChecker:
    """
    A class that encapsulates:
      - Highlighting in PDFs
      - Checking for email, full name, future date, and budget correctness
      - 'check_all' method to run all checks in sequence
    """

    def __init__(self, openai_client):
        self.client = openai_client

    def highlight_in_pdf(self, original_pdf_bytes, search_text):
        """
        Highlight the search text in the PDF.

        1) Direct search with TEXT_DEHYPHENATE.
        2) Fallback approach for fuzzy matching.
        """
        if not search_text or not search_text.strip():
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
                        # Merge multiple spaces into one
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

    # -------------
    # GPT Checks
    # -------------
    def check_for_email_and_return(self, all_text):
        print("all text:", all_text)
        print("")

        print("client: ", self.client)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
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
            email_found = "email found:" in answer.lower()

            snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE)
            snippet = snippet_match.group(1).strip() if snippet_match else None

            return email_found, snippet

        except Exception:
            return False, None

    def check_for_full_name_and_return(self, all_text):

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
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
            name_found = "name found:" in answer.lower()

            snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE)
            snippet = snippet_match.group(1).strip() if snippet_match else None
            return name_found, snippet

        except Exception:
            return False, None

    def check_future_date_and_return(self, all_text):
        try:
            response = self.client.chat.completions.create(
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
            future_date_found = ("in de toekomst" in answer.lower()) and ("snippet:" in answer.lower())

            snippet_match = re.search(r"Snippet:\s*(.*)", answer, re.IGNORECASE)
            snippet = snippet_match.group(1).strip() if snippet_match else None

            return future_date_found, snippet

        except Exception:
            return False, None

    def check_budget_correctness_and_return(self, all_text):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
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
                            "Als het totaal niet klopt, leg dan uit wat het verschil is."
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

    def check_all(self, combined_text):
        """
        Combines all checks for the *combined* text. Returns a dict:
            {
                "email_found": bool,
                "email_snippet": str or None,
                "name_found": bool,
                "name_snippet": str or None,
                "date_found": bool,
                "date_snippet": str or None,
                "budget_correct": bool,
                "budget_snippet": str or None
            }
        """
        # 1) Email
        email_found, email_snippet = self.check_for_email_and_return(combined_text)

        # 2) Full Name
        name_found, name_snippet = self.check_for_full_name_and_return(combined_text)

        # 3) Future Date
        date_found, date_snippet = self.check_future_date_and_return(combined_text)

        # 4) Budget
        budget_correct, budget_snippet = self.check_budget_correctness_and_return(combined_text)

        return {
            "email_found": email_found,
            "email_snippet": email_snippet,
            "name_found": name_found,
            "name_snippet": name_snippet,
            "date_found": date_found,
            "date_snippet": date_snippet,
            "budget_correct": budget_correct,
            "budget_snippet": budget_snippet,
        }

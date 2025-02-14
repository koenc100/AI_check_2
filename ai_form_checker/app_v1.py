import streamlit as st
import pdfplumber
import os

# Import the new OpenAI client class
from openai import OpenAI

# 1) Create an OpenAI client instance
#    We are *directly* providing your API key here:
client = OpenAI(
    api_key="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"
)

def main():
    # 2) Build Streamlit Interface
    st.title("Form Correction Review")
    st.text(
        "Welcome to the Form Correction Reviewer! Tired of having to check all of the specific information in a form yourself? "
        "Don't want to go over everything word for word? You do not have to anymore! Simply insert the form you need to check, "
        "choose what you want it to check, and it will rapidly provide you with possible corrections."
    )
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

    # If a file has been uploaded, extract text with pdfplumber
    if uploaded_file is not None:
        with pdfplumber.open(uploaded_file) as pdf:
            all_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                all_text += page_text + "\n"

        # Show the extracted text in a text area (just for reference)
        st.subheader("(1) Extracted Text from PDF")
        st.text_area("Below, we provide you with a flattened out version of the text in the PDF you provided.", all_text, height=200)

        # Button 1 to ask GPT if there's an email in the text
        if st.button("Check for Email"):
            with st.spinner("Asking GPT to check for an email..."):
                try:
                    # GPT checks for an email address
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an assistant that checks a text for email addresses."
                            },
                            {
                                "role": "user",
                                "content": (
                                    "Does the following text contain an email address? "
                                    "If yes, extract it. If not, respond with 'No email found.'\n\n"
                                    f"{all_text}"
                                )
                            }
                        ]
                    )
                    if response.choices and response.choices[0].message:
                        answer = response.choices[0].message.content
                    else:
                        answer = "No valid response from GPT."
                    st.subheader("Email Check Result")
                    st.write(answer)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        # Button 2 to ask GPT if there's a full name in the text
        if st.button("Check for Full Name"):
            with st.spinner("Asking GPT to check for a full name..."):
                try:
                    # GPT checks for a full name
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an assistant that checks a text for full names."
                            },
                            {
                                "role": "user",
                                "content": (
                                    "Does the following text contain a full name (first name and last name)? "
                                    "If yes, extract it. If not, respond with 'No full name found.'\n\n"
                                    f"{all_text}"
                                )
                            }
                        ]
                    )
                    if response.choices and response.choices[0].message:
                        answer = response.choices[0].message.content
                    else:
                        answer = "No valid response from GPT."
                    st.subheader("Full Name Check Result")
                    st.write(answer)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        # Button 3 to ask GPT if the event is in the future
        if st.button("Check if Event Date is in the Future"):
            with st.spinner("Checking the event date..."):
                try:
                    # GPT checks if the event date is in the future
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an assistant that verifies dates in text to check if they are in the future."
                            },
                            {
                                "role": "user",
                                "content": (
                                    "Does the following text contain an event date, and is it in the future? "
                                    "If yes, confirm that it is valid and in the future. "
                                    "If the date is in the past or missing, provide a response indicating that.\n\n"
                                    f"{all_text}"
                                )
                            }
                        ]
                    )
                    if response.choices and response.choices[0].message:
                        answer = response.choices[0].message.content
                    else:
                        answer = "No valid response from GPT."
                    st.subheader("Event Date Check Result")
                    st.write(answer)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        # Button 4 check if the budget adds up
        if st.button("Check if Budget Adds Up"):
            with st.spinner("Validating the budget..."):
                try:
                    # GPT checks if the budget breakdown matches the total
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an assistant that verifies budget calculations in text."
                            },
                            {
                                "role": "user",
                                "content": (
                                    "Does the following text contain a budget breakdown and a total budget? "
                                    "If yes, check if the total matches the sum of the items. "
                                    "If the total is incorrect, explain the discrepancy.\n\n"
                                    f"{all_text}"
                                )
                            }
                        ]
                    )
                    if response.choices and response.choices[0].message:
                        answer = response.choices[0].message.content
                    else:
                        answer = "No valid response from GPT."
                    st.subheader("Budget Validation Result")
                    st.write(answer)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        # Button 5 check if the attendees match the budget
        if st.button("Check if Attendees Match the Budget"):
            with st.spinner("Evaluating attendees vs. budget..."):
                try:
                    # GPT checks if the number of attendees is reasonable given the budget
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an assistant that evaluates whether the expected number of attendees matches the budget for an event."
                            },
                            {
                                "role": "user",
                                "content": (
                                    "Does the following text mention a total budget and the expected number of attendees? "
                                    "If yes, assess whether the budget seems reasonable for the specified number of attendees. "
                                    "Provide an explanation for your conclusion.\n\n"
                                    f"{all_text}"
                                )
                            }
                        ]
                    )
                    if response.choices and response.choices[0].message:
                        answer = response.choices[0].message.content
                    else:
                        answer = "No valid response from GPT."
                    st.subheader("Attendees vs. Budget Result")
                    st.write(answer)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

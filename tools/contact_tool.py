import requests
from typing import Literal
from pydantic import BaseModel
from langchain_core.tools import tool
from langgraph.types import interrupt


# =====================================================
# SCHEMA
# =====================================================
class ContactInformationSchema(BaseModel):
    name: str
    company: str
    email: str
    interest: Literal[
        "Web App Development",
        "Andriod/Ios Application",
        "AI Application",
        "UI/Ux Design",
        "Branding",
        "Landing Page",
        "Maintenance",
        "Consultation"
    ]
    project_budget: Literal[
        "≤ $5K",
        "$5K-$10K",
        "$10K-$20K",
        "$20K-$30K",
        "$20K-$30K",
        "$30K-$40K",
        "$40K-$50K",
        "$50K-$60K",
        "$60K-$100K",
        ">$100K"
    ]
    project_details: str


# =====================================================
# TOOL
# =====================================================
@tool(
    "submit_contact_form",
    args_schema=ContactInformationSchema,
    description="Submit contact form lead to backend API after user confirmation."
)
def submit_contact_form(
    name: str,
    company: str,
    email: str,
    interest: str,
    project_budget: str,
    project_details: str
) -> dict:

    # =================================================
    # STEP 1: Build payload
    # =================================================
    payload = {
        "name": name,
        "company": company,
        "email": email,
        "interest": interest,
        "budget": project_budget,
        "message": project_details
    }

    print("DEBUG: payload created ->", payload)

    # =================================================
    # STEP 2: Human confirmation (HITL)
    # =================================================
    decision = interrupt({
        "type": "contact_form_confirmation",
        "message": f"""
Please confirm your submission:

Name: {name}
Company: {company}
Email: {email}
Service: {interest}
Budget: {project_budget}

Reply YES to confirm or NO to cancel.
""",
        "data": payload
    })

    decision = str(decision).strip().lower() if decision else "no"

    print("DEBUG: user decision ->", decision)

    if decision != "yes":
        return {
            "status": "cancelled",
            "delivered": False,
            "message": "Submission cancelled by user.",
            "data": payload
        }

    # =================================================
    # STEP 3: API CALL
    # =================================================
    try:
        response = requests.post(
            "https://www.groooh.com/api/contactmail",
            json=payload,
            timeout=10
        )

        print("DEBUG: API status ->", response.status_code)

        if response.status_code == 200:
                return {
                    "status": "success",
                    "delivered": True,
                    "message": "Your inquiry was successfully submitted.",
                    "data": payload
                }

        return {
            "status": "failed",
            "delivered": False,
            "message": "Submission failed due to server error. Nothing was sent.",
            "error": response.text,
            "status_code": response.status_code
        }

    except Exception as e:
        print("DEBUG: API error ->", str(e))

        return {
            "status": "failed",
            "delivered": False,
            "message": "Submission failed due to network error. Nothing was sent.",
            "error": str(e)
        }
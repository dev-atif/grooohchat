import json
import os
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langgraph.types import interrupt

# =====================================================
# DATA VALIDATION SCHEMA (DROPDOWN COMPLIANT)
# =====================================================
class ContactInformationSchema(BaseModel):
    name: str = Field(
        ..., 
        description="The full name of the user or main contact person."
    )
    company: str = Field(
        ..., 
        description="The company, business, or organization name."
    )
    email: str = Field(
        ..., 
        description="The validated primary email address of the client."
    )
    interest: Literal[
        "Web App Development",
        "Andriod/Ios Application",
        "AI Application",
        "UI/Ux Design",
        "Branding",
        "Landing Page",
        "Maintenance",
        "Consultation"
    ] = Field(
        ..., 
        description="The primary project service category the user is interested in."
    )
    project_budget: Literal[
        "≤ $5K",
        "$5K-$10K",
        "$10K-$20K",
        "$20K-$30K",
        "$30K-$40K",
        "$40K-$50K",
        "$50K-$60K",
        "$60K-$100K",
        ">$100K"
    ] = Field(
        ..., 
        description="The estimated project budget tiers chosen by the client."
    )
    project_details: str = Field(
        ..., 
        description="A descriptive summary outlining the project goals, features, or details provided by the user."
    )

# =====================================================
# DUMMY CONTACT INTAKE TOOL DEFINITION
# =====================================================
@tool("submit_contact_form", args_schema=ContactInformationSchema)
def submit_contact_form(
    name: str,
    company: str,
    email: str,
    interest: str,
    project_budget: str,
    project_details: str
) -> dict:
    """
    Submits a project inquiry lead and structured contact form data to the sales pipeline. 
    Use this tool immediately whenever a user explicitly states they want to work with us, 
    hire us, request a quote, or submit their project details.
    """
    # Package the incoming parsed information structured payload
    form_payload = {
        "client_name": name,
        "company_name": company,
        "client_email": email,
        "service_requested": interest,
        "budget_bracket": project_budget,
        "project_description": project_details
    }
    
    # Create a beautifully formatted Markdown string showing the fields
    review_message = (
        f"Please review the contact form details below before submission:\n\n"
        f"👤 **Name:** {name}\n"
        f"🏢 **Company:** {company}\n"
        f"📧 **Email:** {email}\n"
        f"🛠️ **Service:** {interest}\n"
        f"💰 **Budget:** {project_budget}\n"
        f"📝 **Description:** {project_details}\n\n"
        f"**Do you want to submit this data? (Reply 'yes' or 'no')**"
    )
    
    # Trigger the human-in-the-loop interrupt with the updated message
    decision = interrupt({
        "type": "contact_form_approval",
        "title": "Approve Project Submission",
        "message": review_message,     # Streamlit will render this markdown perfectly
        "pending_data": form_payload   # Keeps raw data accessible programmatically
    })
    
    # Handle the human approval decision safely
    if isinstance(decision, str) and decision.lower().strip() == "yes":
        return {
            "status": "success",
            "message": f"Project inquiry lead for {name} ({company}) submitted successfully.",
            "data": form_payload
        }
    else:
        # =======================================================================
        # CHANGE APPLIED HERE:
        # Raising a descriptive error breaks the LLM out of its optimistic "happy path" 
        # and forcefully commands it to pivot to cancellation handling.
        # =======================================================================
        return {
            "status": "user_cancelled_submission",
            "message": (
                f"SUBMISSION HALTED: The user  explicitly replied 'NO' or cancelled during the review step. "
                f"Do NOT submit any form data. Do NOT tell the user that their details were sent or that anyone will reach out. "
                f"Acknowledge the cancellation clearly and ask how they would like to proceed or modify the information."
            ),
            "data": None
        }
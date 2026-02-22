"""ClinicalTrials.gov API v2 integration."""

import logging
from typing import Optional

import requests

from models.schemas import ClinicalTrial
from app.config import CLINICAL_TRIALS_API

logger = logging.getLogger(__name__)


def find_relevant_trials(
    conditions: list[str],
    drugs: list[str],
    keywords: list[str] = [],
) -> list[ClinicalTrial]:
    """Search ClinicalTrials.gov for relevant recruiting trials.

    Args:
        conditions: List of medical conditions to search.
        drugs: List of drugs/interventions to search.
        keywords: Additional keywords to include.

    Returns:
        List of matching ClinicalTrial objects. Empty list on error.
    """
    if not conditions and not drugs:
        return []

    params = {
        "filter.overallStatus": "RECRUITING",
        "pageSize": 5,
        "fields": "NCTId,BriefTitle,OverallStatus,Condition,InterventionName,LocationCity,LocationState",
    }

    if conditions:
        params["query.cond"] = " OR ".join(conditions)
    if drugs:
        params["query.intr"] = " OR ".join(drugs)

    try:
        response = requests.get(
            CLINICAL_TRIALS_API,
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning(f"ClinicalTrials.gov API error: {e}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error fetching trials: {e}")
        return []

    trials = []
    studies = data.get("studies", [])

    for study in studies:
        protocol = study.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        arms_module = protocol.get("armsInterventionsModule", {})
        locations_module = protocol.get("contactsLocationsModule", {})

        nct_id = id_module.get("nctId", "")
        title = id_module.get("briefTitle", "")
        status = status_module.get("overallStatus", "")

        trial_conditions = conditions_module.get("conditions", [])

        interventions = []
        for arm in arms_module.get("interventions", []):
            name = arm.get("name", "")
            if name:
                interventions.append(name)

        # Get location
        location = ""
        locations_list = locations_module.get("locations", [])
        if locations_list:
            loc = locations_list[0]
            city = loc.get("city", "")
            state = loc.get("state", "")
            location = f"{city}, {state}".strip(", ")

        # Generate match explanation
        matched_conditions = [c for c in conditions if any(c.lower() in tc.lower() for tc in trial_conditions)]
        matched_drugs = [d for d in drugs if any(d.lower() in i.lower() for i in interventions)]
        explanation_parts = []
        if matched_conditions:
            explanation_parts.append(f"Matches condition(s): {', '.join(matched_conditions)}")
        if matched_drugs:
            explanation_parts.append(f"Matches drug(s): {', '.join(matched_drugs)}")
        if not explanation_parts:
            explanation_parts.append(f"Related to search terms: {', '.join(conditions + drugs)}")

        trials.append(ClinicalTrial(
            nct_id=nct_id,
            brief_title=title,
            status=status,
            conditions=trial_conditions,
            interventions=interventions,
            location=location,
            url=f"https://clinicaltrials.gov/study/{nct_id}",
            why_it_matches="; ".join(explanation_parts),
        ))

    return trials

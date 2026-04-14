import json
import csv
import re
from pathlib import Path


INPUT_FILE = "test.json"
OUTPUT_JSON = "extracted_jobs.json"
OUTPUT_CSV = "extracted_jobs.csv"


def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def text_value(value):
    if isinstance(value, dict):
        return value.get("text") or value.get("accessibilityText") or ""
    return value or ""


def urn_last_id(urn: str) -> str:
    # Example: "urn:li:fsd_jobPostingCard:(4401354844,JOB_DETAILS)" -> "4401354844"
    if not urn:
        return ""
    if "(" in urn and ")" in urn:
        inside = urn.split("(", 1)[1].split(")", 1)[0]
        return inside.split(",", 1)[0].strip()
    return urn.split(":")[-1]


def infer_job_type(workplace_types, title, location, description):
    if workplace_types:
        normalized = {str(x).strip().upper() for x in workplace_types}
        if "REMOTE" in normalized:
            return "remote"
        if "HYBRID" in normalized:
            return "hybrid"
        if "ON_SITE" in normalized or "ONSITE" in normalized:
            return "onsite"

    text = " ".join(
        [
            str(title or ""),
            str(location or ""),
            str(description or "")[:500],
        ]
    ).lower()

    if "hybrid" in text:
        return "hybrid"
    if "remote" in text or "work from home" in text or "wfh" in text:
        return "remote"
    if "on-site" in text or "onsite" in text or "in-office" in text or "in office" in text:
        return "onsite"
    return "unknown"


def clean_location_text(value):
    text = str(value or "").strip()
    if not text:
        return ""

    # Remove workplace mode labels from location text.
    text = re.sub(r"\b(remote|hybrid|on[\s-]?site|in[\s-]?office)\b", "", text, flags=re.IGNORECASE)
    text = text.replace("()", "")
    text = re.sub(r"\s*[\-\|•]\s*", " ", text)
    text = re.sub(r"\s*,\s*,+", ", ", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;-")
    return text


def extract_jobs_from_data(data):
    root = safe_get(data, "data", "data", default={})
    elements = safe_get(root, "jobsDashJobCardsByPrefetch", "elements", default=[]) or []
    included = data.get("included", []) or []

    # Build quick lookup maps
    job_posting_by_id = {}
    job_posting_card_by_id = {}
    company_name_by_urn = {}
    geo_name_by_urn = {}
    job_description_by_posting_urn = {}
    posted_on_text_by_posting_urn = {}
    app_detail_by_urn = {}

    JOB_POSTING_TYPE = "com.linkedin.voyager.dash.jobs.JobPosting"
    JOB_POSTING_CARD_TYPE = "com.linkedin.voyager.dash.jobs.JobPostingCard"
    COMPANY_TYPE = "com.linkedin.voyager.dash.organization.Company"
    JOB_DESCRIPTION_TYPE = "com.linkedin.voyager.dash.jobs.JobDescription"
    GEO_TYPE = "com.linkedin.voyager.dash.common.Geo"
    APP_DETAIL_TYPE = "com.linkedin.voyager.dash.jobs.JobSeekerApplicationDetail"

    for item in included:
        item_type = item.get("$type", "")

        # JobPosting object
        if item_type == JOB_POSTING_TYPE:
            posting_urn = item.get("entityUrn") or item.get("*jobPosting")
            posting_id = urn_last_id(posting_urn) if posting_urn else ""
            if posting_id:
                job_posting_by_id[posting_id] = item

        # JobPostingCard object
        if item_type == JOB_POSTING_CARD_TYPE:
            posting_urn = item.get("*jobPosting")
            posting_id = urn_last_id(posting_urn) if posting_urn else ""
            if posting_id:
                job_posting_card_by_id[posting_id] = item

        # Company object
        if item_type == COMPANY_TYPE:
            c_urn = item.get("entityUrn")
            c_name = (
                item.get("name")
                or safe_get(item, "nameResolutionResult", "name")
                or safe_get(item, "localizedName")
            )
            if c_urn and c_name:
                company_name_by_urn[c_urn] = c_name

        # Geo object
        if item_type == GEO_TYPE:
            g_urn = item.get("entityUrn")
            g_name = item.get("defaultLocalizedName") or item.get("abbreviatedLocalizedName")
            if g_urn and g_name:
                geo_name_by_urn[g_urn] = g_name

        # JobDescription object
        if item_type == JOB_DESCRIPTION_TYPE:
            posting_urn = item.get("*jobPosting")
            desc_text = safe_get(item, "descriptionText", "text") or safe_get(item, "description", "text")
            if posting_urn and desc_text:
                job_description_by_posting_urn[posting_urn] = desc_text
            posted_on_text = item.get("postedOnText")
            if posting_urn and posted_on_text:
                posted_on_text_by_posting_urn[posting_urn] = posted_on_text

        # JobSeekerApplicationDetail object
        if item_type == APP_DETAIL_TYPE:
            app_urn = item.get("entityUrn")
            if app_urn:
                app_detail_by_urn[app_urn] = item

    posting_ids_to_extract = []

    # Primary mode: jobs search payload with explicit cards in root elements.
    if elements:
        for el in elements:
            job_card = el.get("jobCard", {}) if isinstance(el, dict) else {}
            posting_card_urn = job_card.get("*jobPostingCard", "")
            posting_id = urn_last_id(posting_card_urn)
            if posting_id:
                posting_ids_to_extract.append(posting_id)
    else:
        # Fallback mode: extract from included maps when root elements are absent.
        # Useful for alternate LinkedIn payload variants where cards are not present.
        candidate_ids = set(job_posting_by_id.keys()) | set(job_posting_card_by_id.keys())
        posting_ids_to_extract = sorted(candidate_ids)

    extracted = []

    for posting_id in posting_ids_to_extract:
        posting_card_urn = f"urn:li:fsd_jobPostingCard:({posting_id},JOB_DETAILS)"

        posting = job_posting_by_id.get(posting_id, {})
        posting_card = job_posting_card_by_id.get(posting_id, {})

        # Title
        title = (
            safe_get(posting, "title", "text")
            or posting.get("title")
            or ""
        )

        # Company name
        company_urn = safe_get(posting, "companyDetails", "jobCompany", "*company")
        company = (
            safe_get(posting, "companyDetails", "jobCompany", "rawCompanyName")
            or company_name_by_urn.get(company_urn, "")
        )

        # Description
        posting_urn = posting.get("entityUrn") or posting.get("*jobPosting")
        description = (
            safe_get(posting, "description", "text")
            or job_description_by_posting_urn.get(posting_urn, "")
            or ""
        )

        # Apply details (from card -> application detail)
        app_detail_urn = safe_get(
            posting_card,
            "primaryActionV2",
            "applyJobAction",
            "*applyJobActionResolutionResult",
        )
        app_detail = app_detail_by_urn.get(app_detail_urn, {}) if app_detail_urn else {}
        apply_url = app_detail.get("companyApplyUrl") or ""
        apply_cta = safe_get(app_detail, "applyCtaText", "text") or ""
        apply_accessibility = safe_get(app_detail, "applyCtaText", "accessibilityText") or ""
        onsite_apply = app_detail.get("onsiteApply")
        in_page_offsite_apply = app_detail.get("inPageOffsiteApply")
        applicant_tracking_system = app_detail.get("applicantTrackingSystemName")
        applied = app_detail.get("applied")
        applied_at = app_detail.get("appliedAt")
        formatted_apply_date = app_detail.get("formattedApplyDate")

        if onsite_apply is True:
            apply_type = "internal"
        elif in_page_offsite_apply is True:
            apply_type = "external"
        elif apply_url:
            apply_type = "external"
        elif app_detail:
            apply_type = "unknown"
        else:
            apply_type = ""

        # Optional extra fields
        location_urn = posting.get("*location")
        location = (
            safe_get(posting, "formattedLocation")
            or geo_name_by_urn.get(location_urn, "")
            or safe_get(posting_card, "secondaryDescription", "text")
            or safe_get(posting, "location", "text")
            or ""
        )
        location = clean_location_text(location)
        workplace_types = posting.get("jobWorkplaceTypes") or []
        job_type = infer_job_type(workplace_types, title, location, description)
        reposted = posting.get("repostedJob")
        job_state = posting.get("jobState")
        tracking_urn = posting.get("trackingUrn")
        content_source = posting.get("contentSource")
        posted_on = posting.get("createdAt")
        posted_on_text = posted_on_text_by_posting_urn.get(posting_urn, "")

        extracted.append(
            {
                "job_id": posting_id,
                "job_title": title,
                "company": company,
                "location": location,
                "job_type": job_type,
                "workplace_types": workplace_types,
                "apply_type": apply_type,
                "apply_url": apply_url,
                "apply_cta_text": apply_cta,
                "apply_accessibility_text": apply_accessibility,
                "applicant_tracking_system": applicant_tracking_system,
                "applied": applied,
                "applied_at": applied_at,
                "formatted_apply_date": formatted_apply_date,
                "job_description": description,
                "posted_at": posted_on,
                "posted_on_text": posted_on_text,
                "reposted": reposted,
                "job_state": job_state,
                "tracking_urn": tracking_urn,
                "content_source": content_source,
                "job_posting_urn": posting_urn,
                "job_posting_card_urn": posting_card_urn,
                "application_detail_urn": app_detail_urn,
                "feed_update_urn": "",
            }
        )

    # Feed mode: some LinkedIn feed payloads can include job cards directly in updates.
    if not extracted:
        feed_entries = []
        for item in included:
            if item.get("$type") != "com.linkedin.voyager.dash.feed.Update":
                continue

            job_component = safe_get(item, "content", "jobComponent")
            if not job_component:
                continue

            title = text_value(job_component.get("title"))
            description = text_value(job_component.get("description"))
            company = text_value(safe_get(item, "actor", "name"))
            location = text_value(job_component.get("subtitle")) or text_value(job_component.get("footer"))
            location = clean_location_text(location)
            apply_url = (
                safe_get(job_component, "ctaButton", "navigationContext", "actionTarget")
                or safe_get(job_component, "navigationContext", "actionTarget")
                or ""
            )
            apply_cta = text_value(safe_get(job_component, "ctaButton", "text"))
            posted_on_text = text_value(safe_get(item, "actor", "subDescription"))

            apply_type = "external" if apply_url else ""
            job_type = infer_job_type([], title, location, description)
            update_urn = item.get("entityUrn") or ""
            feed_job_id = urn_last_id(update_urn) or f"feed_job_{len(feed_entries) + 1}"

            feed_entries.append(
                {
                    "job_id": feed_job_id,
                    "job_title": title,
                    "company": company,
                    "location": location,
                    "job_type": job_type,
                    "workplace_types": [],
                    "apply_type": apply_type,
                    "apply_url": apply_url,
                    "apply_cta_text": apply_cta,
                    "apply_accessibility_text": "",
                    "applicant_tracking_system": "",
                    "applied": None,
                    "applied_at": None,
                    "formatted_apply_date": "",
                    "job_description": description,
                    "posted_at": None,
                    "posted_on_text": posted_on_text,
                    "reposted": None,
                    "job_state": "",
                    "tracking_urn": "",
                    "content_source": "feed_update_job_component",
                    "job_posting_urn": "",
                    "job_posting_card_urn": "",
                    "application_detail_urn": "",
                    "feed_update_urn": update_urn,
                }
            )

        extracted.extend(feed_entries)

    return extracted


def extract_jobs(input_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return extract_jobs_from_data(data)


def save_outputs(rows, out_json, out_csv):
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "job_id",
        "job_title",
        "company",
        "location",
        "job_type",
        "workplace_types",
        "apply_type",
        "apply_url",
        "apply_cta_text",
        "apply_accessibility_text",
        "applicant_tracking_system",
        "applied",
        "applied_at",
        "formatted_apply_date",
        "job_description",
        "posted_at",
        "posted_on_text",
        "reposted",
        "job_state",
        "tracking_urn",
        "content_source",
        "job_posting_urn",
        "job_posting_card_urn",
        "application_detail_urn",
        "feed_update_urn",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    rows = extract_jobs(INPUT_FILE)
    save_outputs(rows, OUTPUT_JSON, OUTPUT_CSV)
    if rows:
        print(f"Extracted {len(rows)} jobs")
    else:
        print(
            "Extracted 0 jobs: this JSON does not appear to contain job postings "
            "(likely a feed payload, not jobs search payload)."
        )
    print(f"Saved JSON: {Path(OUTPUT_JSON).resolve()}")
    print(f"Saved CSV : {Path(OUTPUT_CSV).resolve()}")
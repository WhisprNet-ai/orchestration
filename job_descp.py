from flask import Flask, request, jsonify
from dataclasses import dataclass
from typing import List, Dict
import aiohttp
import asyncio
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@dataclass
class JobRequirement:
    job_title: str
    skills_required: List[str]
    experience_level: str
    location: str
    employment_type: str
    responsibilities: List[str]
    qualifications: List[str]
    company_name: str
    salary_range: str

class JobDescriptionGenerator:
    def __init__(self):
        self.model_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.model_name = "meta/llama-3.1-70b-instruct"
        self.api_key = os.getenv("NVIDIA_API_KEY")

    def _create_prompt(self, job: JobRequirement) -> str:
        return f"""
You are an expert HR professional.

Create an engaging and professional job description for the following position:

Job Title: {job.job_title}
Company: {job.company_name}
Location: {job.location}
Employment Type: {job.employment_type}
Experience Level: {job.experience_level}
Salary Range: {job.salary_range}

Skills Required:
{', '.join(job.skills_required)}

Responsibilities:
- {'\n- '.join(job.responsibilities)}

Qualifications:
- {'\n- '.join(job.qualifications)}

Format:
1. About the Company
2. Job Summary
3. Responsibilities
4. Required Skills
5. Qualifications
6. Benefits
7. How to Apply

Make it attractive to potential applicants and keep the tone inclusive and motivating.
"""

    async def generate_description(self, job: JobRequirement) -> str:
        prompt = self._create_prompt(job)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 800
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.model_url, headers=headers, json=payload) as resp:
                    result = await resp.json()
                    return result['choices'][0]['message']['content']
            except Exception as e:
                logger.error(f"Job description generation failed: {str(e)}")
                return "Unable to generate job description."

generator = JobDescriptionGenerator()

def parse_job_input(data: Dict) -> JobRequirement:
    return JobRequirement(
        job_title=data.get("job_title", data.get("title", "Software Engineer")),
        skills_required=data.get("skills_required", ["Python", "REST APIs", "Cloud"]),
        experience_level=data.get("experience_level", "Mid-Level"),
        location=data.get("location", "Unknown"),
        employment_type=data.get("employment_type", data.get("employmentStatus", "Full-Time")),
        responsibilities=data.get("responsibilities", [
            "Develop and maintain software applications",
            "Collaborate with cross-functional teams"
        ]),
        qualifications=data.get("qualifications", [
            "Bachelor’s degree in Computer Science or related field",
            "2+ years of experience in software development"
        ]),
        company_name=data.get("company_name", "Your Company"),
        salary_range=data.get("salary_range", "$80K–$120K")
    )

@app.route("/generate-job-description", methods=["POST"])
def generate_job_description():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({"error": "Missing JSON data"}), 400

        job = parse_job_input(json_data)
        description = asyncio.run(generator.generate_description(job))
        return jsonify({
            "job_description": description,
            "job_title": job.job_title,
            "location": job.location,
            "company": job.company_name
        }), 200

    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

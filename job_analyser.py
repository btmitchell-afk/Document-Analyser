import streamlit as st
import anthropic
import requests
import json
from dotenv import load_dotenv
import os
from collections import Counter
from bs4 import BeautifulSoup

load_dotenv()
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except:
    api_key = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

st.title("HN Job Market Analyser")
st.write("Scrapes the latest Hacker News 'Who is Hiring' thread and analyses it with Claude.")

def fetch_jobs(num_jobs):
    thread_id = 48357725
    url = f"https://hacker-news.firebaseio.com/v0/item/{thread_id}.json"
    response = requests.get(url)
    thread = response.json()
    kid_ids = thread.get('kids', [])
    jobs = []
    for kid_id in kid_ids[:num_jobs * 2]:
        url = f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json"
        response = requests.get(url)
        item = response.json()
        if item and item.get('text') and len(item.get('text', '')) > 100:
            text = BeautifulSoup(item['text'], 'html.parser').get_text()
            jobs.append(text)
        if len(jobs) >= num_jobs:
            break
    return jobs

def analyse_job(job_text):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": f"""Extract from this job posting and return as JSON only, no other text, no markdown, no backticks:
{{
  "company": "company name",
  "title": "job title",
  "location": "location or remote status",
  "salary": "salary or Not specified",
  "seniority": "Junior/Mid/Senior/Lead/Not specified",
  "ai_required": "Yes/No",
  "skills": "skill1, skill2, skill3",
  "summary": "one sentence summary"
}}

Job posting:
{job_text[:800]}"""
        }]
    )
    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except:
        return None

num_jobs = st.slider("Number of jobs to analyse", 10, 50, 20)

if st.button("Analyse Jobs"):
    with st.spinner("Fetching job postings..."):
        jobs = fetch_jobs(num_jobs)

    st.write(f"Found {len(jobs)} job postings. Analysing with Claude...")
    progress = st.progress(0)
    results = []

    for i, job in enumerate(jobs):
        result = analyse_job(job)
        if result:
            results.append(result)
        progress.progress((i + 1) / len(jobs))

    if len(results) == 0:
        st.error("No results could be parsed. Try again.")
    else:
        ai_count = sum(1 for r in results if r.get('ai_required') == 'Yes')
        st.subheader(f"Market Summary — {len(results)} roles analysed")

        col1, col2, col3 = st.columns(3)
        col1.metric("AI/ML Required", f"{ai_count} / {len(results)} roles", f"{round(ai_count/len(results)*100)}%")

        seniority_counts = {}
        for r in results:
            s = r.get('seniority', 'Not specified')
            seniority_counts[s] = seniority_counts.get(s, 0) + 1
        top_seniority = max(seniority_counts, key=seniority_counts.get)
        col2.metric("Most Common Level", top_seniority, f"{seniority_counts[top_seniority]} roles")

        all_skills = []
        for r in results:
            all_skills.extend([s.strip() for s in r.get('skills', '').split(',')])
        skill_counts = Counter(all_skills).most_common(5)
        top_skill = skill_counts[0][0] if skill_counts else 'N/A'
        col3.metric("Top Skill", top_skill)

        salaries = [r.get('salary', '') for r in results if r.get('salary') and r.get('salary') != 'Not specified']
        st.write(f"**Roles with salary disclosed:** {len(salaries)} / {len(results)}")
        if salaries:
            st.write("**Salaries mentioned:** " + " | ".join(salaries))

        st.write("**Top 5 most demanded skills:** " + ", ".join(f"{s} ({c})" for s, c in skill_counts))
        st.write("**Seniority breakdown:** " + ", ".join(f"{k}: {v}" for k, v in sorted(seniority_counts.items(), key=lambda x: x[1], reverse=True)))

        with st.spinner("Generating market insights..."):
            summary_data = f"""
Roles analysed: {len(results)}
AI/ML required: {ai_count} ({round(ai_count/len(results)*100)}%)
Top skills: {', '.join(f"{s}({c})" for s,c in skill_counts)}
Seniority: {seniority_counts}
Salaries: {salaries}
Companies: {', '.join(r.get('company','') for r in results)}
"""
            insight = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": f"Based on this job market data from Hacker News June 2026, write a 3-4 sentence plain English summary of what the market is looking for and what skills are most valuable:\n{summary_data}"
                }]
            )
            st.info(insight.content[0].text)

        st.subheader("Job Listings")
        ai_filter = st.checkbox("AI/ML roles only")
        filtered = [r for r in results if not ai_filter or r.get('ai_required') == 'Yes']
        st.dataframe(filtered, use_container_width=True)
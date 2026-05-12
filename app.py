import streamlit as st
import json
import re
from difflib import SequenceMatcher
from fpdf import FPDF
import PyPDF2
import docx  # for Word document parsing

# -------------------------------
# Load Questions
# -------------------------------
def load_questions(file_path="questions.json"):
    with open(file_path, "r") as f:
        return json.load(f)

questions = load_questions()

# -------------------------------
# Resume Readers
# -------------------------------
def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def read_docx(file):
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

# -------------------------------
# Screening
# -------------------------------
def screen_profile(candidate_resume, job_description):
    skills = re.findall(r'\b[A-Za-z]+\b', candidate_resume)
    skills = set([s.lower() for s in skills])

    score = 0
    matched_skills = []

    for skill in job_description["requiredSkills"]:
        if skill.lower() in skills:
            score += 10
            matched_skills.append(skill)
        else:
            score -= 5

    years = re.findall(r'(\d+)\s*year', candidate_resume.lower())
    years = int(years[0]) if years else 0

    if years >= job_description.get("minYears", 0):
        score += 15
    else:
        score -= 10

    return {
        "skillsMatched": matched_skills,
        "score": score,
        "summary": f"Matched skills: {matched_skills}, Years of experience: {years}"
    }

# -------------------------------
# Evaluation
# -------------------------------
def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def evaluate_responses(candidate_responses):
    score = 0
    strengths = []
    weaknesses = []

    for response in candidate_responses:
        if response["correct"]:
            if response["topic"] == "Behavioral":
                score += 5
            else:
                score += 15
            strengths.append(response["topic"])
        else:
            weaknesses.append(response["topic"])

    recommendation = "Hire" if score >= 60 else "Consider for junior role"

    return {
        "finalScore": score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "narrative": generate_summary(score, strengths, weaknesses, recommendation)
    }

def generate_summary(score, strengths, weaknesses, recommendation):
    summary = f"The candidate scored {score} points.\n"
    if strengths:
        summary += f"Strengths: {', '.join(set(strengths))}\n"
    if weaknesses:
        summary += f"Weaknesses: {', '.join(set(weaknesses))}\n"
    summary += f"Recommendation: {recommendation}\n"
    return summary

# -------------------------------
# Streamlit UI
# -------------------------------
st.title("Interview Assistant")

resume_file = st.file_uploader("Upload Candidate Resume (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
resume_text = ""
if resume_file is not None:
    if resume_file.type == "application/pdf":
        resume_text = read_pdf(resume_file)
    elif resume_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        resume_text = read_docx(resume_file)
    else:
        resume_text = resume_file.read().decode("utf-8")

job_file = st.file_uploader("Upload Job Description (.json)", type=["json"])
job_description = {}
if job_file is not None:
    job_description = json.load(job_file)

if resume_text and job_description:
    st.subheader("Screening Result")
    screening = screen_profile(resume_text, job_description)
    st.write(screening)

    st.subheader("Interview Questions")
    role = job_description.get("role", "")
    role_questions = questions.get(role, [])
    behavioral_questions = questions.get("Behavioral", [])
    all_questions = role_questions + behavioral_questions

    candidate_responses = []
    for q in all_questions:
        answer = st.text_input(f"{q['level']} - {q['question']}")
        if answer:
            correct = similarity(answer, q["answer"]) > 0.5 if q["level"] != "Behavioral" else True
            candidate_responses.append({"question": q["question"], "response": answer, "correct": correct, "topic": q["level"]})

    if st.button("Evaluate Responses"):
        evaluation = evaluate_responses(candidate_responses)
        st.subheader("Evaluation Report")
        st.write(evaluation["narrative"])

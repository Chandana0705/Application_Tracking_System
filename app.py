import os
import io
import json
import PyPDF2
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types # Import types for type safety if needed

app = Flask(__name__)

# --- CONFIGURATION ---

API_KEY = "" 

client = genai.Client(api_key=API_KEY)

def extract_text_from_pdf(file_stream):
    extracted_text = ""
    try:
        pdf_file = io.BytesIO(file_stream)
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text
        return extracted_text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    job_description = request.form.get('job_description', '') 

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        try:
            file_content = file.read()
            resume_text = extract_text_from_pdf(file_content)
        except Exception as e:
            print(f"PDF Error: {e}")
            return jsonify({"error": "Failed to process PDF."}), 400
        
        if not resume_text:
            return jsonify({"error": "Could not extract text from PDF."}), 400

        try:
            # --- Prompt Engineering ---
            if job_description:
                prompt = f"""
                You are an expert ATS (Applicant Tracking System). Compare the resume text below against the provided Job Description.

                RESUME:
                {resume_text}

                JOB DESCRIPTION:
                {job_description}
                
                Return a pure JSON response (no markdown, no backticks) with this structure:
                {{
                    "score": 0,
                    "summary": "Short summary of the match.",
                    "strengths": ["Matching Skill 1", "Matching Skill 2"],
                    "weaknesses": ["Missing Skill 1", "Experience Gap"]
                }}
                Ensure the score is an integer out of 100.
                """
            else:
                prompt = f"""
                You are an expert ATS scanner. Analyze this resume:
                {resume_text}
                
                Return a pure JSON response (no markdown, no backticks) with this structure:
                {{
                    "score": 0,
                    "summary": "Short summary of the candidate.",
                    "strengths": ["Strength 1", "Strength 2"],
                    "weaknesses": ["Weakness 1", "Weakness 2"]
                }}
                Ensure the score is an integer out of 100.
                """
            
            # Call Gemini
            response = client.models.generate_content(
                model="gemini-2.5-flash", # Updated to latest fast model
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            
            # Parse response
            data = json.loads(response.text)
            return jsonify(data)
            
        except Exception as e:
            print(f"AI Error: {e}") # CHECK YOUR TERMINAL FOR THIS MESSAGE
            return jsonify({"error": f"AI Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8000)
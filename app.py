import streamlit as st
import requests
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_ids_from_link(link):
    match = re.search(r'courses/(\d+)/assignments/(\d+)', link)
    if match:
        return match.group(1), match.group(2)
    else:
        return None, None

def get_rubric_criteria(api_url, api_key, course_id, assignment_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}", headers=headers)
    assignment = response.json()
    rubric = assignment.get('rubric', [])
    criteria = {}
    for criterion in rubric:
        ratings = []
        for rating in criterion['ratings']:
            ratings.append((rating['description'], rating['points']))
        criteria[criterion['description']] = {'id': criterion['id'], 'ratings': sorted(ratings, key=lambda x: x[1])}
    return criteria

def fetch_all_students(api_url, api_key, course_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    students = []
    page = 1
    while True:
        response = requests.get(f"{api_url}/api/v1/courses/{course_id}/students?per_page=100&page={page}", headers=headers)
        data = response.json()
        if not data:
            break
        students.extend(data)
        page += 1
    return students

def fetch_current_rubric(api_url, api_key, course_id, assignment_id, user_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}?include[]=rubric_assessment", headers=headers)
    if response.status_code != 200:
        return {}
    submission = response.json()
    return submission.get('rubric_assessment', {})

def extract_rubric_marks(api_url, api_key, course_id, assignment_id):
    students = fetch_all_students(api_url, api_key, course_id)
    results = []

    # Setting up the log display
    log_display = st.empty()
    log_text = ""

    for i, student in enumerate(students):
        user_id = student['id']
        log_text += f"\nFetching marks for Student {user_id} ({i+1}/{len(students)})"
        log_display.text(log_text)
        
        rubric_assessment = fetch_current_rubric(api_url, api_key, course_id, assignment_id, user_id)
        result = {"User ID": user_id}
        for criterion_id, details in rubric_assessment.items():
            points = details.get('points', 'N/A')
            comments = details.get('comments', 'No comments')
            result[criterion_id] = points
            result[f"{criterion_id}_comments"] = comments
            log_text += f"\n  Criterion {criterion_id}: {points} points, Comments: {comments}"
            log_display.text(log_text)

        results.append(result)
    
    results_df = pd.DataFrame(results)
    return results_df

# Streamlit GUI
st.set_page_config(layout="wide")

# Center the logo
left_column, center_column, right_column = st.columns([2.2, 2, 1])
with center_column:
    st.image("logo.png", width=150)  # Ensure the image path is correct

# Center the title
st.markdown("<h1 style='text-align: center;'>Canvas Rubric Extractor</h1>", unsafe_allow_html=True)

api_url = "https://canvas.parra.catholic.edu.au"
api_key = "11905~VUKvENv3Ft7Ckn39Jy2na878NEtaWaD9vAhZWmxv7LNhWBTPR382YBrMXvTmz7yU"
assignment_link = st.text_input("Assignment Link:")

if st.button("Extract Marks"):
    if not assignment_link:
        st.error("Please provide Assignment Link")
    else:
        course_id, assignment_id = extract_ids_from_link(assignment_link)
        if not course_id or not assignment_id:
            st.error("Invalid assignment link")
        else:
            st.info("Fetching rubric marks, please wait...")

            results_df = extract_rubric_marks(api_url, api_key, course_id, assignment_id)
            
            if results_df.empty:
                st.warning("No rubric marks were found for this assignment.")
            else:
                st.write("### Extracted Rubric Marks")
                st.dataframe(results_df)  # Display the extracted marks in a table
                st.success("Rubric marks extracted successfully")

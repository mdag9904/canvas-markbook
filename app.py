import streamlit as st
import requests
import pandas as pd
import re
import json
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

def match_points_to_rating(points, ratings):
    if points == 0:
        return "No Submission", 0.0
    for i, (description, rating_points) in enumerate(ratings):
        if points <= rating_points:
            return description, points
        if i < len(ratings) - 1 and points < ratings[i + 1][1]:
            return description, points
    return "Below Minimum", points

def fetch_current_rubric(api_url, api_key, course_id, assignment_id, sis_user_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/sis_user_id:{sis_user_id}?include[]=rubric_assessment", headers=headers)
    submission = response.json()
    return submission.get('rubric_assessment', {})

def update_rubric_for_student(api_url, api_key, course_id, assignment_id, sis_user_id, rubric_assessment):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "rubric_assessment": rubric_assessment,
        "posted_grade": sum([criterion['points'] for criterion in rubric_assessment.values()])
    }
    try:
        response = requests.put(f"{api_url}/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/sis_user_id:{sis_user_id}", headers=headers, json=data)
        response.raise_for_status()
        st.write(f"Updated rubric for student {sis_user_id}")
    except requests.exceptions.RequestException as e:
        st.write(f"Failed to update rubric for student {sis_user_id}: {e}")

def process_csv(api_url, api_key, file_path, course_id, assignment_id, criteria):
    df = pd.read_csv(file_path)
    tasks = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        for index, row in df.iterrows():
            sis_user_id = row['SIS User ID']
            current_rubric = fetch_current_rubric(api_url, api_key, course_id, assignment_id, sis_user_id)
            rubric_assessment = current_rubric.copy()

            for i, (outcome, details) in enumerate(criteria.items(), start=1):
                column_name = next((col for col in df.columns if col.startswith(outcome)), None)
                comment_column_name = f"Comments{i}"
                if column_name and column_name in row:
                    points = row[column_name]
                    comment = row.get(comment_column_name, None)
                    if pd.isna(points) or points == '-':
                        st.write(f"Skipping User {sis_user_id} for {outcome} due to missing points")
                        continue
                    rating, matched_points = match_points_to_rating(points, details['ratings'])
                    if pd.isna(comment):
                        comment = None
                    rubric_assessment[details['id']] = {'points': matched_points}
                    if comment:
                        rubric_assessment[details['id']]['comments'] = comment
                    st.write(f"Processing User {sis_user_id}: {outcome} Points = {points}, Rating = {rating}, Matched Points = {matched_points}, Comment = {comment}")

            if rubric_assessment != current_rubric:
                tasks.append(executor.submit(update_rubric_for_student, api_url, api_key, course_id, assignment_id, sis_user_id, rubric_assessment))

        for future in as_completed(tasks):
            future.result()

# Streamlit GUI
st.set_page_config(layout="wide")

# Center the logo
left_column, center_column, right_column = st.columns([2.2, 2, 1])
with center_column:
    st.image("logo.png", width=150)  # Ensure the image path is correct

# Center the title
st.markdown("<h1 style='text-align: center;'>Canvas Rubric Uploader</h1>", unsafe_allow_html=True)

api_url = "https://canvas-parra.beta.instructure.com"
api_key = st.text_input("Canvas API Key:", type="password")
assignment_link = st.text_input("Assignment Link:")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if st.button("Upload CSV") and uploaded_file is not None:
    if not api_key or not assignment_link:
        st.error("Please provide API Key and Assignment Link")
    else:
        course_id, assignment_id = extract_ids_from_link(assignment_link)
        if not course_id or not assignment_id:
            st.error("Invalid assignment link")
        else:
            criteria = get_rubric_criteria(api_url, api_key, course_id, assignment_id)
            st.write(f"Rubric Criteria: {json.dumps(criteria, indent=2)}")
            process_csv(api_url, api_key, uploaded_file, course_id, assignment_id, criteria)
            st.success("Rubric assessments processed successfully")

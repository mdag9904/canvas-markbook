import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import re

# Function to extract course ID from link
def extract_course_id_from_link(link):
    match = re.search(r'courses/(\d+)', link)
    if match:
        return match.group(1)
    else:
        return None

# Function to fetch assignment grades for a course
def get_grades(api_url, api_key, course_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/students/submissions?student_ids[]=all&include[]=submission_comments", headers=headers)
    response.raise_for_status()
    return response.json()

# Function to fetch assignment details
def get_assignments(api_url, api_key, course_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/assignments", headers=headers)
    response.raise_for_status()
    return response.json()

# Function to fetch student details
def get_students(api_url, api_key, course_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/enrollments?type[]=StudentEnrollment&state[]=active", headers=headers)
    response.raise_for_status()
    return response.json()

# Streamlit app layout
st.set_page_config(layout="wide")
st.title("Canvas Course Grade Analysis")

api_url = st.text_input("Canvas API URL", "https://canvas-parra.beta.instructure.com")
api_key = st.text_input("Canvas API Key", type="password")
course_link = st.text_input("Course Link")

if st.button("Load Assignments") or "assignments" in st.session_state:
    if not api_key or not course_link:
        st.error("Please provide API Key and Course Link")
    else:
        course_id = extract_course_id_from_link(course_link)
        if not course_id:
            st.error("Invalid course link")
        else:
            if "assignments" not in st.session_state:
                try:
                    st.session_state.assignments = get_assignments(api_url, api_key, course_id)
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching assignments: {e}")
                    st.stop()

            if "students" not in st.session_state:
                try:
                    st.session_state.students = get_students(api_url, api_key, course_id)
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching students: {e}")
                    st.stop()

            assignments_df = pd.DataFrame(st.session_state.assignments)
            
            # Normalize student data to flatten nested JSON
            students = st.session_state.students
            students_df = pd.json_normalize(students, sep='_')
            students_df = students_df[['user_id', 'user.name']].rename(columns={'user_id': 'Student ID', 'user.name': 'Student Name'})

            st.dataframe(assignments_df[['id', 'name', 'points_possible']])
            
            selected_assignments = st.multiselect("Select Assignments to Include", assignments_df['name'], key="selected_assignments")
            if selected_assignments:
                weights = {}
                for assignment in selected_assignments:
                    weight = st.number_input(f"Weight for {assignment}", min_value=0.0, max_value=1.0, step=0.1, key=f"weight_{assignment}")
                    weights[assignment] = weight
                
                if st.button("Generate Report"):
                    try:
                        grades = get_grades(api_url, api_key, course_id)
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error fetching grades: {e}")
                        st.stop()

                    student_grades = {student['Student ID']: {} for student in students_df.to_dict('records')}
                    
                    for grade in grades:
                        user_id = grade['user_id']
                        assignment_id = grade['assignment_id']
                        score = grade['score'] if grade['score'] is not None else 0

                        assignment_name = assignments_df.loc[assignments_df['id'] == assignment_id, 'name'].values[0]
                        if assignment_name in selected_assignments:
                            student_grades[user_id][assignment_name] = score
                    
                    student_scores = []
                    for student_id, grades in student_grades.items():
                        total_score = sum(grades.get(assignment, 0) * weights[assignment] for assignment in selected_assignments)
                        student_scores.append((student_id, total_score))
                    
                    student_scores_df = pd.DataFrame(student_scores, columns=['Student ID', 'Total Score'])
                    student_scores_df = student_scores_df.merge(students_df, on='Student ID', how='left')
                    student_scores_df['Rank'] = student_scores_df['Total Score'].rank(ascending=False)
                    
                    st.dataframe(student_scores_df)
                    
                    fig, ax = plt.subplots()
                    ax.hist(student_scores_df['Total Score'], bins=10)
                    ax.set_title('Distribution of Total Scores')
                    ax.set_xlabel('Total Score')
                    ax.set_ylabel('Number of Students')
                    st.pyplot(fig)
                    
                    fig, ax = plt.subplots()
                    ax.plot(student_scores_df['Student Name'], student_scores_df['Total Score'], marker='o')
                    ax.set_title('Total Scores by Student')
                    ax.set_xlabel('Student Name')
                    ax.set_ylabel('Total Score')
                    plt.xticks(rotation=90)
                    st.pyplot(fig)

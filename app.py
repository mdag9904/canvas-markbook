import streamlit as st
import requests
import pandas as pd
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
                    st.write("Students JSON structure:", st.session_state.students)  # Log the JSON structure
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching students: {e}")
                    st.stop()

            assignments_df = pd.DataFrame(st.session_state.assignments)
            
            # Normalize student data to flatten nested JSON
            students = st.session_state.students
            students_df = pd.json_normalize(students, sep='_')
            st.write("Normalized students_df structure:", students_df.columns.tolist())  # Log the DataFrame structure

            # Correct column names based on the normalized DataFrame
            students_df = students_df[['user_id', 'user_name']].rename(columns={'user_id': 'Student ID', 'user_name': 'Student Name'})

            # Ensure 'Student ID' is a string
            students_df['Student ID'] = students_df['Student ID'].astype(str)

            st.dataframe(assignments_df[['id', 'name', 'points_possible']])
            
            selected_assignments = st.multiselect("Select Assignments to Include", assignments_df['name'], key="selected_assignments")
            if selected_assignments:
                if st.button("Fetch Grades"):
                    try:
                        grades = get_grades(api_url, api_key, course_id)
                        st.write("Grades JSON structure:", grades)  # Log the grades structure
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error fetching grades: {e}")
                        st.stop()

                    student_grades = {str(student['Student ID']): {} for student in students_df.to_dict('records')}
                    st.write("Initialized student_grades:", student_grades)  # Log initialized student_grades

                    for grade in grades:
                        user_id = str(grade['user_id'])  # Ensure user_id is a string
                        assignment_id = grade['assignment_id']
                        score = grade['entered_grade'] if 'entered_grade' in grade else 0

                        # Check if assignment is selected
                        assignment_name = assignments_df.loc[assignments_df['id'] == assignment_id, 'name'].values[0]
                        if assignment_name in selected_assignments:
                            if user_id in student_grades:
                                student_grades[user_id][assignment_name] = float(score)
                            else:
                                st.warning(f"User ID {user_id} not found in student_grades")

                    # Convert the student_grades dictionary to a DataFrame
                    grades_df = pd.DataFrame.from_dict(student_grades, orient='index').reset_index().rename(columns={'index': 'Student ID'})
                    grades_df = grades_df.merge(students_df, on='Student ID', how='left')
                    st.dataframe(grades_df)

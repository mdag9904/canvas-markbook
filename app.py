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

# Function to fetch all pages of student details
def get_all_students(api_url, api_key, course_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    students = []
    url = f"{api_url}/api/v1/courses/{course_id}/enrollments?type[]=StudentEnrollment&state[]=active"
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        students.extend(response.json())
        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            url = None
    return students

# Streamlit app layout
st.set_page_config(layout="wide")
st.title("Canvas Course Student List")

api_url = st.text_input("Canvas API URL", "https://canvas-parra.beta.instructure.com")
api_key = st.text_input("Canvas API Key", type="password")
course_link = st.text_input("Course Link")

if st.button("Load Students") or "students" in st.session_state:
    if not api_key or not course_link:
        st.error("Please provide API Key and Course Link")
    else:
        course_id = extract_course_id_from_link(course_link)
        if not course_id:
            st.error("Invalid course link")
        else:
            if "students" not in st.session_state:
                try:
                    st.session_state.students = get_all_students(api_url, api_key, course_id)
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching students: {e}")
                    st.stop()

            # Normalize student data to flatten nested JSON
            students = st.session_state.students
            students_df = pd.json_normalize(students, sep='_')
            st.write("Normalized students_df structure:", students_df.columns.tolist())  # Log the DataFrame structure

            # Select relevant columns to display
            students_df = students_df[['user_id', 'user_name', 'enrollment_state']].rename(columns={'user_id': 'Student ID', 'user_name': 'Student Name'})

            # Remove duplicates based on 'Student ID'
            students_df.drop_duplicates(subset=['Student ID'], inplace=True)

            st.dataframe(students_df)

import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import re

# Function to extract course and assignment IDs from link
def extract_ids_from_link(link):
    match = re.search(r'courses/(\d+)/assignments/(\d+)', link)
    if match:
        return match.group(1), match.group(2)
    else:
        return None, None

# Function to fetch assignment grades for a course
def get_grades(api_url, api_key, course_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/students/submissions?student_ids[]=all", headers=headers)
    return response.json()

# Function to fetch assignment details
def get_assignments(api_url, api_key, course_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(f"{api_url}/api/v1/courses/{course_id}/assignments", headers=headers)
    return response.json()

# Streamlit app layout
st.set_page_config(layout="wide")
st.title("Canvas Course Grade Analysis")

api_url = st.text_input("Canvas API URL", "https://canvas-parra.beta.instructure.com")
api_key = st.text_input("Canvas API Key", type="password")
course_link = st.text_input("Course Link")

if st.button("Load Assignments"):
    if not api_key or not course_link:
        st.error("Please provide API Key and Course Link")
    else:
        course_id, _ = extract_ids_from_link(course_link)
        if not course_id:
            st.error("Invalid course link")
        else:
            assignments = get_assignments(api_url, api_key, course_id)
            assignments_df = pd.DataFrame(assignments)
            st.dataframe(assignments_df[['id', 'name', 'points_possible']])
            
            selected_assignments = st.multiselect("Select Assignments to Include", assignments_df['name'])
            if selected_assignments:
                weights = {}
                for assignment in selected_assignments:
                    weight = st.number_input(f"Weight for {assignment}", min_value=0.0, max_value=1.0, step=0.1)
                    weights[assignment] = weight
                
                if st.button("Generate Report"):
                    grades = get_grades(api_url, api_key, course_id)
                    student_grades = {}
                    
                    for grade in grades:
                        user_id = grade['user_id']
                        assignment_id = grade['assignment_id']
                        score = grade['score']
                        
                        if user_id not in student_grades:
                            student_grades[user_id] = {}
                        
                        assignment_name = assignments_df.loc[assignments_df['id'] == assignment_id, 'name'].values[0]
                        if assignment_name in selected_assignments:
                            student_grades[user_id][assignment_name] = score
                    
                    student_scores = []
                    for student, grades in student_grades.items():
                        total_score = sum(grades[assignment] * weights[assignment] for assignment in grades if assignment in weights)
                        student_scores.append((student, total_score))
                    
                    student_scores_df = pd.DataFrame(student_scores, columns=['Student ID', 'Total Score'])
                    student_scores_df['Rank'] = student_scores_df['Total Score'].rank(ascending=False)
                    
                    st.dataframe(student_scores_df)
                    
                    fig, ax = plt.subplots()
                    ax.hist(student_scores_df['Total Score'], bins=10)
                    ax.set_title('Distribution of Total Scores')
                    ax.set_xlabel('Total Score')
                    ax.set_ylabel('Number of Students')
                    st.pyplot(fig)
                    
                    fig, ax = plt.subplots()
                    ax.plot(student_scores_df['Student ID'], student_scores_df['Total Score'], marker='o')
                    ax.set_title('Total Scores by Student')
                    ax.set_xlabel('Student ID')
                    ax.set_ylabel('Total Score')
                    st.pyplot(fig)

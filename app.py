import streamlit as st
import requests
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
API_KEY = "11905~VUKvENv3Ft7Ckn39Jy2na878NEtaWaD9vAhZWmxv7LNhWBTPR382YBrMXvTmz7yU"
BASE_URL = "https://canvas.parra.catholic.edu.au/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Function to extract course ID and assignment ID from the link
def extract_ids_from_link(assignment_link):
    parts = assignment_link.split('/')
    course_id = parts[-3]
    assignment_id = parts[-1]
    return course_id, assignment_id

# Function to get user details by user_id
def get_user_details(course_id, user_id):
    url = f"{BASE_URL}/courses/{course_id}/users/{user_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

# Function to get rubric details from the assignment
def get_rubric_details(course_id, assignment_id):
    url = f"{BASE_URL}/courses/{course_id}/assignments/{assignment_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    assignment_data = response.json()
    rubric_criteria = assignment_data.get('rubric', [])
    return rubric_criteria

# Function to get all pages of rubric assessments
def get_all_rubric_assessments(course_id, assignment_id):
    submissions = []
    url = f"{BASE_URL}/courses/{course_id}/assignments/{assignment_id}/submissions"
    params = {
        'include[]': 'rubric_assessment',
        'per_page': 100
    }
    while url:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        submissions.extend(response.json())
        # Check if there's a next page
        url = response.links.get('next', {}).get('url')
    return submissions

# Function to process submission and fetch details concurrently
def process_submission(course_id, submission, criterion_titles):
    user_id = submission.get('user_id')
    user_details = get_user_details(course_id, user_id)
    student_name = user_details.get('name', 'N/A')
    rubric_assessment = submission.get('rubric_assessment', {})
    
    row = {'Student Name': student_name}
    for criterion_id, assessment in rubric_assessment.items():
        criterion_title = criterion_titles.get(criterion_id)
        if criterion_title:  # Only add it if the criterion title exists in fieldnames
            row[criterion_title] = assessment.get('points', 'N/A')
    
    return row

# Function to extract and export rubric marks to CSV using concurrency
def export_rubric_marks_to_csv(assignment_link):
    course_id, assignment_id = extract_ids_from_link(assignment_link)
    submissions = get_all_rubric_assessments(course_id, assignment_id)
    
    # Get rubric criterion names
    rubric_criteria = get_rubric_details(course_id, assignment_id)
    criterion_titles = {criterion['id']: criterion['description'] for criterion in rubric_criteria}

    # Create a CSV file and write data
    csv_filename = 'rubric_marks.csv'
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['Student Name'] + list(criterion_titles.values())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_submission, course_id, submission, criterion_titles): submission for submission in submissions}
            for future in as_completed(futures):
                try:
                    row = future.result()
                    writer.writerow(row)
                except ValueError as e:
                    st.warning(f"Skipped a row due to a mismatch: {e}")

    return csv_filename

# Streamlit App
def main():
    st.title("Canvas Rubric Marks Exporter")
    
    assignment_link = st.text_input("Please paste the Canvas assignment link:")

    if st.button("Export Rubric Marks"):
        if assignment_link:
            try:
                csv_filename = export_rubric_marks_to_csv(assignment_link)
                st.success(f"Rubric marks have been exported to {csv_filename}.")
                with open(csv_filename, 'rb') as f:
                    st.download_button(
                        label="Download CSV",
                        data=f,
                        file_name=csv_filename,
                        mime='text/csv',
                    )
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please enter a valid Canvas assignment link.")

if __name__ == "__main__":
    main()

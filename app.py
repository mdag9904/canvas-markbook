import streamlit as st
import requests
import pandas as pd

# Function to fetch all students with pagination
def fetch_all_students(api_url, headers, params):
    students = []
    page_number = 1

    while True:
        response = requests.get(api_url, headers=headers, params=params)
        
        if response.status_code == 429:  # Rate limit hit
            retry_after = int(response.headers.get("Retry-After", 1))
            st.write(f"Rate limit hit. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            continue
        
        response.raise_for_status()
        data = response.json()
        students.extend(data)
        
        if 'next' in response.links:
            api_url = response.links['next']['url']
            page_number += 1
            st.write(f"Fetching page {page_number}")
        else:
            break

    return students

# Streamlit app
st.title("Canvas Course Student List")

# User inputs
api_url_input = st.text_input("Canvas API URL", "https://canvas-parra.beta.instructure.com")
api_key_input = st.text_input("Canvas API Key", type="password")
course_link_input = st.text_input("Course Link", "https://canvas-parra.beta.instructure.com/courses/22365")

if st.button("Fetch Students"):
    api_url = f"{api_url_input}/api/v1/courses/22365/enrollments"
    headers = {
        "Authorization": f"Bearer {api_key_input}"
    }
    params = {
        "per_page": 100,  # Increase per page limit
        "type": ["StudentEnrollment"],
        "enrollment_state": "active"
    }

    # Fetch all students
    students_data = fetch_all_students(api_url, headers, params)
    st.write(f"Total students fetched: {len(students_data)}")

    # Normalize JSON data into a pandas DataFrame
    students_df = pd.json_normalize(students_data)

    # Display the DataFrame structure
    st.write("Normalized students_df structure:")
    st.write(students_df.columns.tolist())

    # Display the DataFrame
    st.write(students_df)

    # Save to CSV
    students_df.to_csv("students_list.csv", index=False)
    st.success("Students list has been saved to 'students_list.csv'")

# Footer
st.write("Normalized students_df structure:", students_df.columns.tolist())
st.write("Total unique students fetched:", len(students_df))

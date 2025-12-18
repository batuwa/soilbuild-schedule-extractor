import json
import os

import pandas as pd
import pdfplumber
import streamlit as st

# Import the extraction module
from extract_json import extract_doors_from_table, is_valid_door_entry

st.set_page_config(
    page_title="Soilbuild Door Schedule Extractor",
    page_icon="🚪",
    layout="wide",
)

st.title("🏗️ Soilbuild Demo Door Schedule Data Extractor")
st.markdown("---")


# Function to extract door data from PDF (file object or path)
def extract_from_pdf(pdf_file):
    """Extract door schedule data from PDF file."""
    all_doors = []

    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)
        progress_bar = st.progress(0, text=f"Processing page 1 of {total_pages}...")

        for page_num, page in enumerate(pdf.pages, start=1):
            progress_bar.progress(
                page_num / total_pages,
                text=f"Processing page {page_num} of {total_pages}...",
            )

            try:
                tables = page.extract_tables()
                if not tables:
                    continue

                for table in tables:
                    table_doors = extract_doors_from_table(table)
                    valid_doors = [d for d in table_doors if is_valid_door_entry(d)]
                    all_doors.extend(valid_doors)

            except Exception as e:
                continue

        progress_bar.empty()

    # Post-processing: clean up data
    for door in all_doors:
        door["fire_rating"] = door["fire_rating"].replace("FIRE-RATING", "").strip()
        door["description"] = door["description"].replace("DESCRIPTION", "").strip()
        door["location"] = door["location"].replace("LOCATION", "").strip()
        door["remarks"] = door["remarks"].replace("REMARKS", "").strip()

    return all_doors


# Initialize session state
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown(
        """
        This tool extracts door schedule data from PDF files.

        **How to use:**
        1. Upload a PDF file
        2. Click Extract Data
        3. View the extracted data
        4. Export as JSON or CSV
        """
    )

    st.markdown("---")

    if st.session_state.extracted_data:
        st.subheader("📊 Summary")
        door_data = st.session_state.extracted_data
        st.metric("Total Doors", len(door_data))
        st.metric("Unique Types", len(set(d["door_type"] for d in door_data)))
        with_dims = len([d for d in door_data if d["dimensions"]])
        st.metric("With Dimensions", with_dims)

# Main panel - Upload and Extract section
st.subheader("📄 Upload PDF and Extract Data")

uploaded_file = st.file_uploader(
    "Choose a door schedule PDF file:",
    type=["pdf"],
    help="Upload a PDF file containing door schedule tables",
)

if uploaded_file is not None:
    # Store filename
    if (
        "uploaded_filename" not in st.session_state
        or st.session_state.uploaded_filename != uploaded_file.name
    ):
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.extracted_data = (
            None  # Clear previous data when new file is uploaded
        )

    extract_button = st.button(
        "🔄 Extract Data from PDF", type="primary", use_container_width=True
    )

    if extract_button:
        with st.spinner(f"Extracting from {uploaded_file.name}..."):
            door_data = extract_from_pdf(uploaded_file)
            st.session_state.extracted_data = door_data
            st.session_state.selected_project = uploaded_file.name

        if door_data:
            st.success(f"✅ Successfully extracted {len(door_data)} doors!")
        else:
            st.error("❌ No data could be extracted from this PDF")

st.markdown("---")

# Show data if extracted
if st.session_state.extracted_data is not None:
    door_data = st.session_state.extracted_data
    filename = st.session_state.get("selected_project", "Unknown")

    st.subheader(f"📊 Extracted Data - {filename}")

    # Convert to DataFrame
    df = pd.DataFrame(door_data)
    column_order = [
        "door_type",
        "dimensions",
        "fire_rating",
        "description",
        "location",
        "remarks",
    ]
    df = df[column_order]

    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        height=500,
        hide_index=True,
    )

    st.markdown("---")

    # Export section
    st.subheader("💾 Export Data")

    col1, col2 = st.columns(2)

    with col1:
        # JSON export
        json_str = json.dumps(door_data, indent=4, ensure_ascii=False)
        filename = st.session_state.get("selected_project", "output")
        base_name = filename.replace(".pdf", "").replace(" ", "_")
        st.download_button(
            label="📥 Export as JSON",
            data=json_str,
            file_name=f"{base_name}_doors.json",
            mime="application/json",
            use_container_width=True,
        )

    with col2:
        # CSV export
        csv = df.to_csv(index=False)
        filename = st.session_state.get("selected_project", "output")
        base_name = filename.replace(".pdf", "").replace(" ", "_")
        st.download_button(
            label="📥 Export as CSV",
            data=csv,
            file_name=f"{base_name}_doors.csv",
            mime="text/csv",
            use_container_width=True,
        )

else:
    # Initial state - no data extracted yet
    if uploaded_file is None:
        st.info("👆 Upload a PDF file to begin")
    else:
        st.info("👆 Click **Extract Data from PDF** to process the uploaded file")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>Soilbuild Door Schedule Data Extractor</div>",
    unsafe_allow_html=True,
)

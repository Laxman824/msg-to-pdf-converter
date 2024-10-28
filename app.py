import streamlit as st
import os
import tempfile
from msg_converter import MSGtoPDFConverter
import zipfile
from datetime import datetime
import shutil
from pathlib import Path

# Configure page settings
st.set_page_config(
    page_title="MSG to PDF Converter",
    page_icon="📧",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #1e90ff;
    }
    .stButton>button {
        background-color: #1e90ff;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .success-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
        margin: 1rem 0;
    }
    .error-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        color: #721c24;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

def process_uploaded_files(uploaded_files, progress_bar, status_text):
    """Process uploaded MSG files and return results"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save uploaded files temporarily
        msg_files = []
        for uploaded_file in uploaded_files:
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            msg_files.append(temp_path)

        # Create converter instance
        converter = MSGtoPDFConverter(
            base_output_dir=os.path.join(temp_dir, "output"),
            max_workers=4
        )

        # Process files
        results = []
        errors = []
        total_files = len(msg_files)

        for i, file_path in enumerate(msg_files):
            try:
                status_text.text(f"Processing {os.path.basename(file_path)}...")
                folder_path, zip_path = converter.convert_single_file(
                    file_path, 
                    prefix=f"batch_{i}"
                )
                results.append((file_path, zip_path))
            except Exception as e:
                errors.append((file_path, str(e)))
            finally:
                progress_bar.progress((i + 1) / total_files)

        # Create master ZIP file
        if results:
            master_zip = os.path.join(temp_dir, "converted_emails.zip")
            with zipfile.ZipFile(master_zip, 'w') as zipf:
                for _, zip_path in results:
                    zipf.write(zip_path, os.path.basename(zip_path))
            
            # Read ZIP file content
            with open(master_zip, 'rb') as f:
                zip_data = f.read()

        return results, errors, zip_data if results else None

def main():
    st.title("📧 MSG to PDF Converter")
    st.write("""
    Upload your MSG files to convert them to PDF format with attachments.
    The converter will maintain all formatting and save attachments in their original format.
    """)

    # File uploader
    uploaded_files = st.file_uploader(
        "Choose MSG files",
        type=['msg'],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.write(f"Selected {len(uploaded_files)} files")
        
        # Create progress bar and status text
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process button
        if st.button("Convert Files"):
            try:
                # Process files
                results, errors, zip_data = process_uploaded_files(
                    uploaded_files,
                    progress_bar,
                    status_text
                )

                # Display results
                if results:
                    st.markdown(
                        f'<div class="success-message">Successfully converted {len(results)} files!</div>',
                        unsafe_allow_html=True
                    )
                    
                    # Provide download link
                    st.download_button(
                        label="Download Converted Files (ZIP)",
                        data=zip_data,
                        file_name="converted_emails.zip",
                        mime="application/zip"
                    )

                if errors:
                    st.markdown(
                        f'<div class="error-message">Errors occurred while processing {len(errors)} files:</div>',
                        unsafe_allow_html=True
                    )
                    for file_path, error in errors:
                        st.error(f"{os.path.basename(file_path)}: {error}")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
            finally:
                # Reset progress bar
                progress_bar.empty()
                status_text.empty()

    # Add footer with information
    st.markdown("---")
    st.markdown("""
    ### Instructions:
    1. Upload one or more MSG files using the file uploader above
    2. Click the 'Convert Files' button to start processing
    3. Wait for the conversion to complete
    4. Download the ZIP file containing all converted files
    
    ### Features:
    - Converts MSG files to PDF format
    - Preserves all formatting and inline images
    - Saves attachments in their original format
    - Combines all converted files into a single ZIP
    - Handles multiple files simultaneously
    """)

if __name__ == "__main__":
    main()
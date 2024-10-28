import streamlit as st
import os
import tempfile
from msg_converter import MSGtoPDFConverter
import zipfile
from datetime import datetime
import shutil
import logging
from pathlib import Path
import base64
from tqdm import tqdm
import time
# Add this at the start of your app.py
import sys
import subprocess
import logging

def check_weasyprint_dependencies():
    try:
        from weasyprint import HTML, CSS
        # Try to create a simple PDF to verify everything works
        HTML(string='<p>Test</p>').write_pdf('/tmp/test.pdf')
        return True
    except Exception as e:
        logging.error(f"WeasyPrint initialization error: {str(e)}")
        try:
            # Try to install missing dependencies
            subprocess.check_call(['apt-get', 'update'])
            subprocess.check_call(['apt-get', 'install', '-y', 
                                 'libpango-1.0-0', 'libharfbuzz0b', 
                                 'libpangoft2-1.0-0', 'libffi-dev'])
            return True
        except Exception as install_error:
            logging.error(f"Failed to install dependencies: {str(install_error)}")
            return False

# Add this check at the start of your main() function
def main():
    if not check_weasyprint_dependencies():
        st.error("""
        Error: Required system libraries are missing. 
        Please contact the administrator to install the required dependencies.
        """)
        return
    

# Configure page settings
st.set_page_config(
    page_title="MSG to PDF Converter",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to improve UI
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
    .stButton>button:hover {
        background-color: #0066cc;
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

def create_download_link(file_path, link_text):
    """Create a download link for a file"""
    with open(file_path, 'rb') as f:
        bytes = f.read()
        b64 = base64.b64encode(bytes).decode()
        href = f'<a href="data:application/zip;base64,{b64}" download="{os.path.basename(file_path)}">{link_text}</a>'
        return href

def setup_logging():
    """Setup logging configuration"""
    log_dir = "logs"
    Path(log_dir).mkdir(exist_ok=True)
    
    log_file = os.path.join(log_dir, f"conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file

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
                logging.error(f"Error processing {file_path}: {str(e)}")
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

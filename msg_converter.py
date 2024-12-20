# #4th best version with 10000 docs parallel processing and 
# # First install required dependencies
# # !pip install extract-msg weasyprint beautifulsoup4 tqdm
# # !apt-get install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# import extract_msg
# from weasyprint import HTML, CSS
# import base64
# import tempfile
# import os
# import shutil
# from datetime import datetime
# from google.colab import files
# from bs4 import BeautifulSoup
# import re
# from tqdm.notebook import tqdm
# import concurrent.futures
# import threading
# from pathlib import Path
# import logging
# import gc
# import time
# import zipfile

# class MSGtoPDFConverter:
#     def __init__(self, base_output_dir="output", max_workers=4):
#         """Initialize converter with base output directory and threading parameters."""
#         self.base_output_dir = base_output_dir
#         self.max_workers = max_workers
#         self.thread_local = threading.local()
        
#         # Set up logging
#         self.setup_logging()
        
#         # Create output directory
#         Path(base_output_dir).mkdir(parents=True, exist_ok=True)


#     def _format_email_header(self, msg):
#         """Create a formatted HTML header for the email metadata."""
#         header = f"""
#         <div style="font-family: Arial, sans-serif; margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
#             <div style="margin: 5px 0;"><strong>From:</strong> {msg.sender}</div>
#             <div style="margin: 5px 0;"><strong>To:</strong> {msg.to}</div>
#             <div style="margin: 5px 0;"><strong>Subject:</strong> {msg.subject}</div>
#             <div style="margin: 5px 0;"><strong>Date:</strong> {msg.date}</div>
#         </div>
#         """
#         return header

#     def setup_logging(self):
#         """Set up logging configuration."""
#         logging.basicConfig(
#             level=logging.INFO,
#             format='%(asctime)s - %(levelname)s - %(message)s',
#             handlers=[
#                 logging.FileHandler('conversion.log'),
#                 logging.StreamHandler()
#             ]
#         )

#     def _create_email_folder(self, msg, prefix=''):
#         """Create a unique folder for the email and its attachments."""
#         subject = msg.subject or "No Subject"
#         clean_subject = re.sub(r'[<>:"/\\|?*]', '_', subject)[:50]
#         folder_name = f"{prefix}_{clean_subject}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#         folder_path = os.path.join(self.base_output_dir, folder_name)
        
#         Path(folder_path).mkdir(parents=True, exist_ok=True)
#         Path(folder_path, "attachments").mkdir(exist_ok=True)
        
#         return folder_path

#     def _optimize_images(self, img_data, max_size_mb=1):
#         """Optimize image size if needed."""
#         from PIL import Image
#         import io
        
#         # Convert bytes to max MB
#         max_size = max_size_mb * 1024 * 1024
        
#         if len(img_data) <= max_size:
#             return img_data
        
#         # Open image
#         img = Image.open(io.BytesIO(img_data))
        
#         # Calculate new size while maintaining aspect ratio
#         ratio = (max_size / len(img_data)) ** 0.5
#         new_size = tuple(int(dim * ratio) for dim in img.size)
        
#         # Resize image
#         img = img.resize(new_size, Image.Resampling.LANCZOS)
        
#         # Save optimized image
#         buffer = io.BytesIO()
#         img.save(buffer, format=img.format, optimize=True, quality=85)
#         return buffer.getvalue()

#     def _save_attachments(self, msg, folder_path):
#         """Save all attachments efficiently."""
#         saved_attachments = []
#         attachments_folder = os.path.join(folder_path, "attachments")
        
#         for attachment in msg.attachments:
#             try:
#                 filename = attachment.longFilename or attachment.shortFilename
#                 filepath = self._get_unique_filepath(attachments_folder, filename)
                
#                 # Save attachment
#                 with open(filepath, 'wb') as f:
#                     attachment_data = attachment.data
#                     # Optimize images if they're too large
#                     if any(filepath.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
#                         attachment_data = self._optimize_images(attachment_data)
#                     f.write(attachment_data)
                
#                 saved_attachments.append({
#                     'filename': os.path.basename(filepath),
#                     'original_filename': filename,
#                     'filepath': filepath,
#                     'size': len(attachment_data),
#                     'cid': getattr(attachment, 'cid', None)
#                 })
                
#             except Exception as e:
#                 logging.error(f"Error saving attachment {filename}: {str(e)}")
#                 continue
        
#         return saved_attachments


#     def _process_inline_images(self, msg, html_content, saved_attachments):
#         """Process inline images and replace them with base64 encoded versions."""
#         if not msg.htmlBody:
#             return html_content

#         soup = BeautifulSoup(html_content, 'html.parser')
        
#         for img in soup.find_all('img'):
#             src = img.get('src', '')
            
#             if src.startswith('cid:'):
#                 # Handle inline images with Content-ID
#                 cid = src[4:]
#                 for attachment in saved_attachments:
#                     if attachment['cid'] == cid:
#                         with open(attachment['filepath'], 'rb') as f:
#                             img_data = f.read()
#                             img_base64 = base64.b64encode(img_data).decode()
#                             ext = os.path.splitext(attachment['filename'])[1][1:]
#                             img['src'] = f"data:image/{ext};base64,{img_base64}"
#                         break
#             elif not src.startswith('data:'):
#                 # Try to find attachment by filename
#                 filename = os.path.basename(src)
#                 for attachment in saved_attachments:
#                     if attachment['original_filename'] == filename:
#                         with open(attachment['filepath'], 'rb') as f:
#                             img_data = f.read()
#                             img_base64 = base64.b64encode(img_data).decode()
#                             ext = os.path.splitext(attachment['filename'])[1][1:]
#                             img['src'] = f"data:image/{ext};base64,{img_base64}"
#                         break

#         return str(soup)


#     def _create_attachments_list_html(self, saved_attachments):
#         """Create HTML list of attachments with file sizes."""
#         def format_size(size_bytes):
#             for unit in ['B', 'KB', 'MB', 'GB']:
#                 if size_bytes < 1024:
#                     return f"{size_bytes:.1f} {unit}"
#                 size_bytes /= 1024
#             return f"{size_bytes:.1f} GB"

#         attachments_html = ""
#         non_inline_attachments = [a for a in saved_attachments if not a['cid']]
        
#         if non_inline_attachments:
#             attachments_html = """
#             <div style='margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px;'>
#                 <h3>Attachments:</h3>
#                 <p style='color: #666;'>All attachments have been saved in the 'attachments' folder.</p>
#                 <ul>
#             """
#             for attachment in non_inline_attachments:
#                 size_str = format_size(attachment['size'])
#                 attachments_html += f"""
#                     <li style='margin: 5px 0;'>
#                         {attachment['filename']} ({size_str})
#                     </li>
#                 """
#             attachments_html += "</ul></div>"
        
#         return attachments_html



#     def _get_unique_filepath(self, folder, filename):
#         """Get unique filepath handling duplicates efficiently."""
#         filepath = os.path.join(folder, filename)
#         if not os.path.exists(filepath):
#             return filepath
        
#         base, ext = os.path.splitext(filename)
#         counter = 1
#         while True:
#             new_filepath = os.path.join(folder, f"{base}_{counter}{ext}")
#             if not os.path.exists(new_filepath):
#                 return new_filepath
#             counter += 1

#     def _create_optimized_html_content(self, msg, saved_attachments):
#         """Create optimized HTML content with better page layout."""
#         header_html = self._format_email_header(msg)
        
#         # Process body content
#         body_content = msg.htmlBody if msg.htmlBody else f"<pre>{msg.body}</pre>"
#         if msg.htmlBody:
#             body_content = self._process_inline_images(msg, body_content, saved_attachments)
        
#         # Create attachments list
#         attachments_html = self._create_attachments_list_html(saved_attachments)

#         # Optimize layout to avoid empty pages
#         html_content = f"""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <meta charset="UTF-8">
#             <style>
#                 @page {{
#                     margin: 1cm;
#                     size: A4;
#                     @top-right {{
#                         content: counter(page);
#                     }}
#                 }}
#                 body {{
#                     font-family: Arial, sans-serif;
#                     line-height: 1.6;
#                     color: #333;
#                     max-width: 800px;
#                     margin: 0 auto;
#                     padding: 20px;
#                 }}
#                 img {{
#                     max-width: 100%;
#                     height: auto;
#                     page-break-inside: avoid;
#                 }}
#                 pre {{
#                     white-space: pre-wrap;
#                     word-wrap: break-word;
#                 }}
#                 .page-break {{
#                     page-break-after: always;
#                 }}
#                 .avoid-break {{
#                     page-break-inside: avoid;
#                 }}
#                 .header {{
#                     position: relative;
#                     margin-bottom: 20px;
#                 }}
#                 .content {{
#                     position: relative;
#                 }}
#                 .attachments {{
#                     position: relative;
#                     margin-top: 20px;
#                 }}
#             </style>
#         </head>
#         <body>
#             <div class="header avoid-break">
#                 {header_html}
#             </div>
#             <div class="content">
#                 {body_content}
#             </div>
#             <div class="attachments avoid-break">
#                 {attachments_html}
#             </div>
#         </body>
#         </html>
#         """
#         return html_content

#     def convert_single_file(self, msg_path, prefix=''):
#         """Convert a single MSG file to PDF and extract attachments."""
#         try:
#             msg = extract_msg.Message(msg_path)
#             folder_path = self._create_email_folder(msg, prefix)
            
#             # Save attachments
#             saved_attachments = self._save_attachments(msg, folder_path)
            
#             # Create and optimize HTML content
#             html_content = self._create_optimized_html_content(msg, saved_attachments)
            
#             # Generate PDF
#             pdf_path = os.path.join(folder_path, "email_content.pdf")
#             css = CSS(string='''
#                 @page { 
#                     margin: 1cm;
#                     size: A4;
#                     @top-right {
#                         content: counter(page);
#                     }
#                 }
#             ''')
            
#             HTML(string=html_content).write_pdf(
#                 pdf_path,
#                 stylesheets=[css],
#                 optimize_size=('fonts', 'images')
#             )
            
#             # Create ZIP
#             zip_path = f"{folder_path}.zip"
#             shutil.make_archive(folder_path, 'zip', folder_path)
            
#             # Cleanup
#             msg.close()
#             gc.collect()
            
#             return folder_path, zip_path
            
#         except Exception as e:
#             logging.error(f"Error converting {msg_path}: {str(e)}")
#             raise
#         finally:
#             if 'msg' in locals():
#                 msg.close()

#     def batch_convert(self, msg_files):
#         """Convert multiple MSG files in parallel."""
#         results = []
#         errors = []
        
#         with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
#             # Create a progress bar
#             pbar = tqdm(total=len(msg_files), desc="Converting emails")
            
#             # Submit all conversion tasks
#             future_to_file = {
#                 executor.submit(self.convert_single_file, file_path, f"batch_{i}"): file_path
#                 for i, file_path in enumerate(msg_files)
#             }
            
#             # Process completed conversions
#             for future in concurrent.futures.as_completed(future_to_file):
#                 file_path = future_to_file[future]
#                 try:
#                     folder_path, zip_path = future.result()
#                     results.append((file_path, zip_path))
#                 except Exception as e:
#                     errors.append((file_path, str(e)))
#                     logging.error(f"Error processing {file_path}: {str(e)}")
#                 finally:
#                     pbar.update(1)
            
#             pbar.close()
        
#         return results, errors

# # Function to handle batch upload and processing
# def process_batch():
#     print("Please upload your MSG files (you can select multiple files):")
#     uploaded = files.upload()
    
#     if not uploaded:
#         print("No files were uploaded.")
#         return
    
#     # Save uploaded files temporarily
#     msg_files = []
#     for filename, content in uploaded.items():
#         temp_path = os.path.join('/tmp', filename)
#         with open(temp_path, 'wb') as f:
#             f.write(content)
#         msg_files.append(temp_path)
    
#     # Create converter instance
#     converter = MSGtoPDFConverter(max_workers=4)  # Adjust max_workers based on available resources
    
#     try:
#         # Process all files
#         results, errors = converter.batch_convert(msg_files)
        
#         # Download results
#         print("\nProcessing complete!")
#         print(f"Successfully converted: {len(results)} files")
#         print(f"Errors encountered: {len(errors)} files")
        
#         if errors:
#             print("\nErrors:")
#             for file_path, error in errors:
#                 print(f"- {os.path.basename(file_path)}: {error}")
        
#         # Create a master ZIP file containing all converted files
#         if results:
#             master_zip = "all_converted_emails.zip"
#             with zipfile.ZipFile(master_zip, 'w') as zipf:
#                 for _, zip_path in results:
#                     zipf.write(zip_path, os.path.basename(zip_path))
            
#             print("\nDownloading combined ZIP file containing all converted emails...")
#             files.download(master_zip)
    
#     finally:
#         # Cleanup
#         for file_path in msg_files:
#             try:
#                 os.remove(file_path)
#             except:
#                 pass

# # Run the batch processor
# process_batch()
#############################################PREVIOUS CODE FOR GOOGLE COLAB####################

# import extract_msg
# from weasyprint import HTML, CSS
# import base64
# import tempfile
# import os
# import shutil
# from datetime import datetime
# from bs4 import BeautifulSoup
# import re
# import concurrent.futures
# import threading
# from pathlib import Path
# import logging
# import gc
# import zipfile
# from utils import setup_logging, optimize_images, get_unique_filepath

# class MSGtoPDFConverter:
#     def __init__(self, base_output_dir="output", max_workers=4):
#         """Initialize converter with base output directory and threading parameters."""
#         self.base_output_dir = base_output_dir
#         self.max_workers = max_workers
#         self.thread_local = threading.local()
        
#         # Set up logging
#         setup_logging()
        
#         # Create output directory
#         Path(base_output_dir).mkdir(parents=True, exist_ok=True)

#     def _format_email_header(self, msg):
#         """Create a formatted HTML header for the email metadata."""
#         try:
#             header = f"""
#             <div style="font-family: Arial, sans-serif; margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
#                 <div style="margin: 5px 0;"><strong>From:</strong> {msg.sender}</div>
#                 <div style="margin: 5px 0;"><strong>To:</strong> {msg.to}</div>
#                 <div style="margin: 5px 0;"><strong>Subject:</strong> {msg.subject}</div>
#                 <div style="margin: 5px 0;"><strong>Date:</strong> {msg.date}</div>
#             </div>
#             """
#             return header
#         except Exception as e:
#             logging.error(f"Error formatting email header: {str(e)}")
#             return "<div>Error formatting email header</div>"

#     def _create_email_folder(self, msg, prefix=''):
#         """Create a unique folder for the email and its attachments."""
#         try:
#             subject = msg.subject or "No Subject"
#             clean_subject = re.sub(r'[<>:"/\\|?*]', '_', subject)[:50]
#             folder_name = f"{prefix}_{clean_subject}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#             folder_path = os.path.join(self.base_output_dir, folder_name)
            
#             Path(folder_path).mkdir(parents=True, exist_ok=True)
#             Path(folder_path, "attachments").mkdir(exist_ok=True)
            
#             return folder_path
#         except Exception as e:
#             logging.error(f"Error creating email folder: {str(e)}")
#             raise

#     def _save_attachments(self, msg, folder_path):
#         """Save all attachments efficiently."""
#         saved_attachments = []
#         attachments_folder = os.path.join(folder_path, "attachments")
        
#         for attachment in msg.attachments:
#             try:
#                 filename = attachment.longFilename or attachment.shortFilename
#                 filepath = get_unique_filepath(attachments_folder, filename)
                
#                 with open(filepath, 'wb') as f:
#                     attachment_data = attachment.data
#                     # Optimize images if they're too large
#                     if any(filepath.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
#                         attachment_data = optimize_images(attachment_data)
#                     f.write(attachment_data)
                
#                 saved_attachments.append({
#                     'filename': os.path.basename(filepath),
#                     'original_filename': filename,
#                     'filepath': filepath,
#                     'size': len(attachment_data),
#                     'cid': getattr(attachment, 'cid', None)
#                 })
                
#             except Exception as e:
#                 logging.error(f"Error saving attachment {filename}: {str(e)}")
#                 continue
        
#         return saved_attachments

#     def _process_inline_images(self, msg, html_content, saved_attachments):
#         """Process inline images and replace them with base64 encoded versions."""
#         if not msg.htmlBody:
#             return html_content

#         try:
#             soup = BeautifulSoup(html_content, 'html.parser')
            
#             for img in soup.find_all('img'):
#                 src = img.get('src', '')
                
#                 if src.startswith('cid:'):
#                     cid = src[4:]
#                     for attachment in saved_attachments:
#                         if attachment['cid'] == cid:
#                             with open(attachment['filepath'], 'rb') as f:
#                                 img_data = f.read()
#                                 img_base64 = base64.b64encode(img_data).decode()
#                                 ext = os.path.splitext(attachment['filename'])[1][1:]
#                                 img['src'] = f"data:image/{ext};base64,{img_base64}"
#                             break
#                 elif not src.startswith('data:'):
#                     filename = os.path.basename(src)
#                     for attachment in saved_attachments:
#                         if attachment['original_filename'] == filename:
#                             with open(attachment['filepath'], 'rb') as f:
#                                 img_data = f.read()
#                                 img_base64 = base64.b64encode(img_data).decode()
#                                 ext = os.path.splitext(attachment['filename'])[1][1:]
#                                 img['src'] = f"data:image/{ext};base64,{img_base64}"
#                             break

#             return str(soup)
#         except Exception as e:
#             logging.error(f"Error processing inline images: {str(e)}")
#             return html_content

#     def _create_attachments_list(self, saved_attachments):
#         """Create HTML list of attachments with file sizes."""
#         try:
#             def format_size(size_bytes):
#                 for unit in ['B', 'KB', 'MB', 'GB']:
#                     if size_bytes < 1024:
#                         return f"{size_bytes:.1f} {unit}"
#                     size_bytes /= 1024
#                 return f"{size_bytes:.1f} GB"

#             attachments_html = ""
#             non_inline_attachments = [a for a in saved_attachments if not a['cid']]
            
#             if non_inline_attachments:
#                 attachments_html = """
#                 <div style='margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px;'>
#                     <h3>Attachments:</h3>
#                     <p style='color: #666;'>All attachments have been saved in the 'attachments' folder.</p>
#                     <ul>
#                 """
#                 for attachment in non_inline_attachments:
#                     size_str = format_size(attachment['size'])
#                     attachments_html += f"""
#                         <li style='margin: 5px 0;'>
#                             {attachment['filename']} ({size_str})
#                         </li>
#                     """
#                 attachments_html += "</ul></div>"
            
#             return attachments_html
#         except Exception as e:
#             logging.error(f"Error creating attachments list: {str(e)}")
#             return ""

#     def _create_optimized_html_content(self, msg, saved_attachments):
#         """Create optimized HTML content with better page layout."""
#         try:
#             header_html = self._format_email_header(msg)
#             body_content = msg.htmlBody if msg.htmlBody else f"<pre>{msg.body}</pre>"
            
#             if msg.htmlBody:
#                 body_content = self._process_inline_images(msg, body_content, saved_attachments)
            
#             attachments_html = self._create_attachments_list(saved_attachments)

#             html_content = f"""
#             <!DOCTYPE html>
#             <html>
#             <head>
#                 <meta charset="UTF-8">
#                 <style>
#                     @page {{
#                         size: A4;
#                         margin: 2cm;
#                     }}
#                     body {{
#                         font-family: Arial, sans-serif;
#                         line-height: 1.6;
#                         color: #333;
#                         margin: 0;
#                         padding: 20px;
#                     }}
#                     img {{
#                         max-width: 100%;
#                         height: auto;
#                         page-break-inside: avoid;
#                     }}
#                     pre {{
#                         white-space: pre-wrap;
#                         word-wrap: break-word;
#                     }}
#                     .avoid-break {{
#                         page-break-inside: avoid;
#                     }}
#                 </style>
#             </head>
#             <body>
#                 <div class="avoid-break">{header_html}</div>
#                 <div class="content">{body_content}</div>
#                 <div class="avoid-break">{attachments_html}</div>
#             </body>
#             </html>
#             """
#             return html_content
#         except Exception as e:
#             logging.error(f"Error creating HTML content: {str(e)}")
#             raise

#     def convert_single_file(self, file_path, prefix=''):
#         """Convert a single MSG file to PDF and extract attachments."""
#         msg = None
#         temp_dir = None
#         try:
#             msg = extract_msg.Message(file_path)
#             folder_path = self._create_email_folder(msg, prefix)
            
#             # Create temporary directory for processing
#             temp_dir = tempfile.mkdtemp()
            
#             # Save attachments
#             saved_attachments = self._save_attachments(msg, folder_path)
            
#             # Create HTML content
#             html_content = self._create_optimized_html_content(msg, saved_attachments)
            
#             # Save HTML to temporary file
#             html_path = os.path.join(temp_dir, 'temp.html')
#             with open(html_path, 'w', encoding='utf-8') as f:
#                 f.write(html_content)
            
#             # Generate PDF path
#             pdf_path = os.path.join(folder_path, "email_content.pdf")
            
#             # Convert to PDF using WeasyPrint
#             HTML(filename=html_path).write_pdf(
#                 pdf_path,
#                 stylesheets=[CSS(string='''
#                     @page {
#                         size: A4;
#                         margin: 2cm;
#                         @top-right {
#                             content: counter(page);
#                         }
#                     }
#                 ''')]
#             )
            
#             # Create ZIP
#             zip_path = f"{folder_path}.zip"
#             shutil.make_archive(folder_path, 'zip', folder_path)
            
#             return folder_path, zip_path
            
#         except Exception as e:
#             logging.error(f"Error converting {file_path}: {str(e)}")
#             raise
#         finally:
#             if msg:
#                 msg.close()
#             if temp_dir and os.path.exists(temp_dir):
#                 shutil.rmtree(temp_dir)
#             gc.collect()

#     def batch_convert(self, file_paths, progress_callback=None):
#         """Convert multiple MSG files in parallel with progress tracking."""
#         results = []
#         errors = []
#         total_files = len(file_paths)
        
#         with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
#             future_to_file = {
#                 executor.submit(self.convert_single_file, file_path, f"batch_{i}"): file_path
#                 for i, file_path in enumerate(file_paths)
#             }
            
#             completed = 0
#             for future in concurrent.futures.as_completed(future_to_file):
#                 file_path = future_to_file[future]
#                 completed += 1
                
#                 if progress_callback:
#                     progress_callback(completed / total_files)
                
#                 try:
#                     folder_path, zip_path = future.result()
#                     results.append((file_path, zip_path))
#                 except Exception as e:
#                     errors.append((file_path, str(e)))
#                     logging.error(f"Error processing {file_path}: {str(e)}")
        
#         return results, errors


####################SECOND UPDATE IS ABOVE FOR BACKUP CODE###############

#adding email format cc,bcc,attachment and included table format view and OUTLOOK CLASSIC VIEW
##msg2 pdf OUTLOOK VIEW cUSTomise and handliing table view in
#CODE FOR GOOGLE COLAB TO WORK DIRECTLY ON MULTIPLE .msg files to select and convert to pdf
#https://msg-to-pdf-converter-cams.streamlit.app/
#4th best version with 10000 docs parallel processing and 
# First install required dependencies
#!pip install extract-msg weasyprint beautifulsoup4 tqdm
#!apt-get install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0


from tqdm import tqdm  # Regular tqdm instead of notebook version

import extract_msg
from weasyprint import HTML, CSS
import base64
import tempfile
import os
import shutil
from datetime import datetime
# from google.colab import files
from bs4 import BeautifulSoup
import re
from tqdm.notebook import tqdm
import concurrent.futures
import threading
from pathlib import Path
import logging
import gc
import time
import zipfile

class MSGtoPDFConverter:
    def __init__(self, base_output_dir="output", max_workers=4):
        """Initialize converter with base output directory and threading parameters."""
        self.base_output_dir = base_output_dir
        self.max_workers = max_workers
        self.thread_local = threading.local()
        
        # Set up logging
        self.setup_logging()
        
        # Create output directory
        Path(base_output_dir).mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('conversion.log'),
                logging.StreamHandler()
            ]
        )

    def _clean_and_normalize_html(self, html_content):
        """Clean and normalize HTML content, especially tables."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process all tables
        for table in soup.find_all('table'):
            # Add missing tbody if not present
            if not table.find('tbody') and not table.find('thead'):
                rows = table.find_all('tr', recursive=False)
                if rows:
                    tbody = soup.new_tag('tbody')
                    for row in rows:
                        tbody.append(row.extract())
                    table.append(tbody)
            
            # Normalize table attributes
            table['class'] = table.get('class', []) + ['email-content-table']
            for attr in ['width', 'height', 'border', 'cellspacing', 'cellpadding']:
                if table.get(attr):
                    del table[attr]
            
            # Process all cells
            for cell in table.find_all(['td', 'th']):
                # Handle alignment
                align = cell.get('align')
                if align:
                    cell['style'] = f"text-align: {align}; " + cell.get('style', '')
                    del cell['align']
                
                # Handle width
                width = cell.get('width')
                if width:
                    cell['style'] = f"width: {width}; " + cell.get('style', '')
                    del cell['width']
                
                # Add scope for header cells
                if cell.name == 'th' and not cell.get('scope'):
                    cell['scope'] = 'col'

        return str(soup)


    def _format_email_header(self, msg):
        """Create a formatted HTML header in Outlook classic style with CC, BCC, and attachments."""
        
        # Get CC and BCC recipients if available
        cc = getattr(msg, 'cc', None)
        bcc = getattr(msg, 'bcc', None)
        
        # Get attachment names for the header
        attachment_names = []
        for attachment in msg.attachments:
            filename = attachment.longFilename or attachment.shortFilename
            if filename and not getattr(attachment, 'cid', None):  # Exclude inline images
                attachment_names.append(filename)
        
        # Format attachment string
        attachment_str = '; '.join(attachment_names) if attachment_names else 'None'
        
        header = f"""
        <div class="email-header">
            <table class="header-table">
                <tr>
                    <td class="header-label">From:</td>
                    <td class="header-value">{msg.sender}</td>
                </tr>
                <tr>
                    <td class="header-label">Sent:</td>
                    <td class="header-value">{msg.date}</td>
                </tr>
                <tr>
                    <td class="header-label">To:</td>
                    <td class="header-value">{msg.to}</td>
                </tr>
                {f'''<tr>
                    <td class="header-label">CC:</td>
                    <td class="header-value">{cc}</td>
                </tr>''' if cc else ''}
                {f'''<tr>
                    <td class="header-label">BCC:</td>
                    <td class="header-value">{bcc}</td>
                </tr>''' if bcc else ''}
                <tr>
                    <td class="header-label">Subject:</td>
                    <td class="header-value subject">{msg.subject}</td>
                </tr>
                <tr>
                    <td class="header-label">Attachments:</td>
                    <td class="header-value attachments-preview">{attachment_str}</td>
                </tr>
            </table>
        </div>
        """
        return header



    def _create_email_folder(self, msg, prefix=''):
        """Create a unique folder for the email and its attachments."""
        subject = msg.subject or "No Subject"
        clean_subject = re.sub(r'[<>:"/\\|?*]', '_', subject)[:50]
        folder_name = f"{prefix}_{clean_subject}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        folder_path = os.path.join(self.base_output_dir, folder_name)
        
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        Path(folder_path, "attachments").mkdir(exist_ok=True)
        
        return folder_path

    def _optimize_images(self, img_data, max_size_mb=1):
        """Optimize image size if needed."""
        from PIL import Image
        import io
        
        # Convert bytes to max MB
        max_size = max_size_mb * 1024 * 1024
        
        if len(img_data) <= max_size:
            return img_data
        
        # Open image
        img = Image.open(io.BytesIO(img_data))
        
        # Calculate new size while maintaining aspect ratio
        ratio = (max_size / len(img_data)) ** 0.5
        new_size = tuple(int(dim * ratio) for dim in img.size)
        
        # Resize image
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save optimized image
        buffer = io.BytesIO()
        img.save(buffer, format=img.format, optimize=True, quality=85)
        return buffer.getvalue()

    def _save_attachments(self, msg, folder_path):
        """Save all attachments efficiently."""
        saved_attachments = []
        attachments_folder = os.path.join(folder_path, "attachments")
        
        for attachment in msg.attachments:
            try:
                filename = attachment.longFilename or attachment.shortFilename
                filepath = self._get_unique_filepath(attachments_folder, filename)
                
                # Save attachment
                with open(filepath, 'wb') as f:
                    attachment_data = attachment.data
                    # Optimize images if they're too large
                    if any(filepath.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                        attachment_data = self._optimize_images(attachment_data)
                    f.write(attachment_data)
                
                saved_attachments.append({
                    'filename': os.path.basename(filepath),
                    'original_filename': filename,
                    'filepath': filepath,
                    'size': len(attachment_data),
                    'cid': getattr(attachment, 'cid', None)
                })
                
            except Exception as e:
                logging.error(f"Error saving attachment {filename}: {str(e)}")
                continue
        
        return saved_attachments


    def _process_inline_images(self, msg, html_content, saved_attachments):
        """Process inline images and replace them with base64 encoded versions."""
        if not msg.htmlBody:
            return html_content

        soup = BeautifulSoup(html_content, 'html.parser')
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            
            if src.startswith('cid:'):
                cid = src[4:]
                for attachment in saved_attachments:
                    if attachment['cid'] == cid:
                        with open(attachment['filepath'], 'rb') as f:
                            img_data = f.read()
                            img_base64 = base64.b64encode(img_data).decode()
                            ext = os.path.splitext(attachment['filename'])[1][1:]
                            img['src'] = f"data:image/{ext};base64,{img_base64}"
                        break
            elif not src.startswith('data:'):
                filename = os.path.basename(src)
                for attachment in saved_attachments:
                    if attachment['original_filename'] == filename:
                        with open(attachment['filepath'], 'rb') as f:
                            img_data = f.read()
                            img_base64 = base64.b64encode(img_data).decode()
                            ext = os.path.splitext(attachment['filename'])[1][1:]
                            img['src'] = f"data:image/{ext};base64,{img_base64}"
                        break

        return str(soup)


    def _create_attachments_list_html(self, saved_attachments):
        """Create HTML list of attachments with Outlook-style icons."""
        def format_size(size_bytes):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024
            return f"{size_bytes:.1f} GB"

        attachments_html = ""
        non_inline_attachments = [a for a in saved_attachments if not a['cid']]
        
        if non_inline_attachments:
            attachments_html = """
            <div class="attachments-section">
                <div class="attachments-header">
                    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAANJJREFUOI2l0rFKA0EQBuAvJqmsBAvR0s7KR7ASBCsrwUdI4QuIYGFhYeUTiGBhYWFhYWFhYWFhYWFhYSGIQgQRRBA5i72F47hr7gcDszPzz7+zs0REaOAE7/jCJY4xUwERsYQn9DHAFhbxiXt0IqIREUMZEVu4zPU2drGPBvbwkBLcp5Eq0MIFjrCWqlpKFe2cz+MT1zlB0RzXuMrKznDwx55ZXGeSzgT1TvLPYBU36GEfHxHxW+oi4hA7/yEHzVxf4xYvecF6J6zjJfd3ETH8A6NcMYlJJHpAAAAAAElFTkSuQmCC" 
                    class="attachment-icon" alt="attachments"/>
                    Attachments
                </div>
                <div class="attachments-list">
            """
            for attachment in non_inline_attachments:
                size_str = format_size(attachment['size'])
                attachments_html += f"""
                    <div class="attachment-item">
                        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAAK5JREFUOI3t0rEKQVEcx/HPJYPJYDKZTCaTyWQymUwmk8lkMplMJpPJZDL5r3fwvtw6dQeD31P3Of/zPed/zzmhKIoQwhw7PLDH5Ns+xBxHLNCM8YQV9EJ6KQYLnLFEB3XUkGGNPaZYI4x/iBLvlKAjBhvccEcbGc7YRnENZSRlgu8kmQxwwiWKO+I+xRk9NFBJyUYxxxBj7GKCLs5Y4RaTF9HHJopvn7mIDxz7Lw8UNUIdAAAAAElFTkSuQmCC" 
                        class="file-icon" alt="file"/>
                        <span class="attachment-name">{attachment['filename']}</span>
                        <span class="attachment-size">({size_str})</span>
                    </div>
                """
            attachments_html += "</div></div>"
        
        return attachments_html




    def _get_unique_filepath(self, folder, filename):
        """Get unique filepath handling duplicates efficiently."""
        filepath = os.path.join(folder, filename)
        if not os.path.exists(filepath):
            return filepath
        
        base, ext = os.path.splitext(filename)
        counter = 1
        while True:
            new_filepath = os.path.join(folder, f"{base}_{counter}{ext}")
            if not os.path.exists(new_filepath):
                return new_filepath
            counter += 1

    def _create_optimized_html_content(self, msg, saved_attachments):
        """Create optimized HTML content with Outlook classic style."""
        header_html = self._format_email_header(msg)
        
        # Process body content
        body_content = msg.htmlBody if msg.htmlBody else f"<pre>{msg.body}</pre>"
        if msg.htmlBody:
            # First clean and normalize HTML/tables
            body_content = self._clean_and_normalize_html(body_content)
            # Then process inline images
            body_content = self._process_inline_images(msg, body_content, saved_attachments)
        
        attachments_html = self._create_attachments_list_html(saved_attachments)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    margin: 2cm;
                    size: A4;
                    @top-right {{
                        content: counter(page);
                        font-family: "Segoe UI", Arial, sans-serif;
                        font-size: 8pt;
                        color: #666;
                    }}
                }}
                body {{
                    font-family: "Segoe UI", Arial, sans-serif;
                    line-height: 1.4;
                    color: #333;
                    margin: 0;
                    padding: 0;
                }}
                /* Email Header Styles */
                .email-header {{
                    background-color: #f8f8f8;
                    border: 1px solid #e1e1e1;
                    border-radius: 4px;
                    padding: 12px;
                    margin-bottom: 20px;
                }}
                .header-table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .header-label {{
                    width: 75px;
                    color: #666;
                    font-size: 11pt;
                    vertical-align: top;
                    padding: 3px 0;
                }}
                .header-value {{
                    color: #333;
                    font-size: 11pt;
                    padding: 3px 0;
                }}
                .subject {{
                    font-weight: bold;
                }}
                
                /* Table Styles */
                .email-content-table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                    border: 1px solid #d1d1d1;
                    page-break-inside: avoid;
                }}
                .email-content-table th,
                .email-content-table td {{
                    padding: 8px;
                    border: 1px solid #d1d1d1;
                    text-align: left;
                    vertical-align: top;
                    font-size: 11pt;
                }}
                .email-content-table th {{
                    background-color: #f5f5f5;
                    font-weight: bold;
                    color: #333;
                }}
                .email-content-table tr:nth-child(even) {{
                    background-color: #fafafa;
                }}
                
                /* Nested Tables */
                .email-content-table .email-content-table {{
                    margin: 0;
                    border: none;
                }}
                .email-content-table .email-content-table td,
                .email-content-table .email-content-table th {{
                    border: 1px solid #e0e0e0;
                }}
                
                /* Content Styles */
                .content {{
                    padding: 0 12px;
                    margin-bottom: 20px;
                }}
                pre {{
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-family: "Segoe UI", Arial, sans-serif;
                    margin: 0;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    page-break-inside: avoid;
                }}
                
                /* Attachments Styles */
                .attachments-section {{
                    background-color: #f8f8f8;
                    border: 1px solid #e1e1e1;
                    border-radius: 4px;
                    padding: 12px;
                    margin-top: 20px;
                }}
                .attachments-header {{
                    font-size: 11pt;
                    font-weight: bold;
                    color: #666;
                    border-bottom: 1px solid #e1e1e1;
                    padding-bottom: 8px;
                    margin-bottom: 8px;
                }}
                .attachment-item {{
                    padding: 4px 0;
                    display: flex;
                    align-items: center;
                }}
                .attachment-name {{
                    color: #0066cc;
                    margin-right: 8px;
                }}
                .attachment-size {{
                    color: #666;
                    font-size: 10pt;
                }}
                .page-break {{
                    page-break-after: always;
                }}
                .avoid-break {{
                    page-break-inside: avoid;
                }}
            </style>
        </head>
        <body>
            <div class="avoid-break">
                {header_html}
            </div>
            <div class="content">
                {body_content}
            </div>
            <div class="avoid-break">
                {attachments_html}
            </div>
        </body>
        </html>
        """
        return html_content

    def convert_single_file(self, msg_path, prefix=''):
        """Convert a single MSG file to PDF and extract attachments."""
        try:
            msg = extract_msg.Message(msg_path)
            folder_path = self._create_email_folder(msg, prefix)
            
            # Save attachments
            saved_attachments = self._save_attachments(msg, folder_path)
            
            # Create and optimize HTML content
            html_content = self._create_optimized_html_content(msg, saved_attachments)
            
            # Generate PDF
            pdf_path = os.path.join(folder_path, "email_content.pdf")
            HTML(string=html_content).write_pdf(
                pdf_path,
                stylesheets=[],
                optimize_size=('fonts', 'images')
            )
            
            # Create ZIP
            zip_path = f"{folder_path}.zip"
            shutil.make_archive(folder_path, 'zip', folder_path)
            
            # Cleanup
            msg.close()
            gc.collect()
            
            return folder_path, zip_path
            
        except Exception as e:
            logging.error(f"Error converting {msg_path}: {str(e)}")
            raise
        finally:
            if 'msg' in locals():
                msg.close()



    def batch_convert(self, msg_files):
        """Convert multiple MSG files in parallel."""
        results = []
        errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            pbar = tqdm(total=len(msg_files), desc="Converting emails")
            future_to_file = {
                executor.submit(self.convert_single_file, file_path, f"batch_{i}"): file_path
                for i, file_path in enumerate(msg_files)
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    folder_path, zip_path = future.result()
                    results.append((file_path, zip_path))
                except Exception as e:
                    errors.append((file_path, str(e)))
                    logging.error(f"Error processing {file_path}: {str(e)}")
                finally:
                    pbar.update(1)
            
            pbar.close()
        
        return results, errors

# Function to handle batch upload and processing
# def process_batch():
#     print("Please upload your MSG files (you can select multiple files):")
#     uploaded = files.upload()
    
#     if not uploaded:
#         print("No files were uploaded.")
#         return
    
#     # Save uploaded files temporarily
#     msg_files = []
#     for filename, content in uploaded.items():
#         temp_path = os.path.join('/tmp', filename)
#         with open(temp_path, 'wb') as f:
#             f.write(content)
#         msg_files.append(temp_path)
    
#     # Create converter instance
#     converter = MSGtoPDFConverter(max_workers=4)  # Adjust max_workers based on available resources
    
#     try:
#         # Process all files
#         results, errors = converter.batch_convert(msg_files)
        
#         # Download results
#         print("\nProcessing complete!")
#         print(f"Successfully converted: {len(results)} files")
#         print(f"Errors encountered: {len(errors)} files")
        
#         if errors:
#             print("\nErrors:")
#             for file_path, error in errors:
#                 print(f"- {os.path.basename(file_path)}: {error}")
        
#         # Create a master ZIP file containing all converted files
#         if results:
#             master_zip = "all_converted_emails.zip"
#             with zipfile.ZipFile(master_zip, 'w') as zipf:
#                 for _, zip_path in results:
#                     zipf.write(zip_path, os.path.basename(zip_path))
            
#             print("\nDownloading combined ZIP file containing all converted emails...")
#             files.download(master_zip)
    
#     finally:
#         # Cleanup
#         for file_path in msg_files:
#             try:
#                 os.remove(file_path)
#             except:
#                 pass

# # Run the batch processor
# process_batch()

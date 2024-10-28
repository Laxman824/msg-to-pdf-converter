import logging
import os
from pathlib import Path
from datetime import datetime
import io
from PIL import Image
import tempfile
import shutil
import zipfile

def setup_logging():
    """Setup logging configuration with rotation and proper formatting."""
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Configure logging with both file and console handlers
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        # Keep only last 5 log files
        clean_old_logs(log_dir, keep_last=5)
        
    except Exception as e:
        print(f"Error setting up logging: {str(e)}")
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

def clean_old_logs(log_dir, keep_last=5):
    """Clean old log files keeping only the specified number of recent files."""
    try:
        log_files = sorted(
            [f for f in log_dir.glob("*.log")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        for log_file in log_files[keep_last:]:
            try:
                log_file.unlink()
            except Exception as e:
                logging.warning(f"Could not delete old log file {log_file}: {str(e)}")
    except Exception as e:
        logging.error(f"Error cleaning old logs: {str(e)}")

def optimize_images(img_data, max_size_mb=1, quality=85):
    """Optimize image size while maintaining quality."""
    try:
        max_size = max_size_mb * 1024 * 1024
        
        if len(img_data) <= max_size:
            return img_data
        
        # Open image
        with Image.open(io.BytesIO(img_data)) as img:
            # Calculate new size while maintaining aspect ratio
            ratio = (max_size / len(img_data)) ** 0.5
            new_size = tuple(int(dim * ratio) for dim in img.size)
            
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            
            # Resize image
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            buffer = io.BytesIO()
            
            # Determine format
            save_format = img.format if img.format else 'JPEG'
            if save_format == 'PNG':
                img.save(buffer, format=save_format, optimize=True)
            else:
                img.save(buffer, format=save_format, quality=quality, optimize=True)
            
            return buffer.getvalue()
            
    except Exception as e:
        logging.error(f"Error optimizing image: {str(e)}")
        return img_data

def get_unique_filepath(folder, filename):
    """Get unique filepath handling duplicates efficiently."""
    try:
        filepath = Path(folder) / filename
        if not filepath.exists():
            return str(filepath)
        
        base, ext = os.path.splitext(filename)
        counter = 1
        
        while True:
            new_filepath = Path(folder) / f"{base}_{counter}{ext}"
            if not new_filepath.exists():
                return str(new_filepath)
            counter += 1
            
    except Exception as e:
        logging.error(f"Error getting unique filepath: {str(e)}")
        return str(Path(folder) / f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}{os.path.splitext(filename)[1]}")

def create_zip_archive(source_dir, output_path=None):
    """Create a ZIP archive from a directory with progress tracking."""
    try:
        if output_path is None:
            output_path = f"{source_dir}.zip"
        
        # Get total file count for progress
        total_files = sum(len(files) for _, _, files in os.walk(source_dir))
        processed_files = 0
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    processed_files += 1
                    
        return output_path
        
    except Exception as e:
        logging.error(f"Error creating ZIP archive: {str(e)}")
        raise

def clean_temp_files(file_paths):
    """Clean up temporary files and directories."""
    for path in file_paths:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            logging.warning(f"Error cleaning up {path}: {str(e)}")

def get_safe_filename(filename):
    """Convert filename to a safe version."""
    # Remove invalid characters
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    return filename if filename else 'unnamed_file'

def create_temp_directory():
    """Create a temporary directory with proper cleanup."""
    temp_dir = tempfile.mkdtemp()
    return temp_dir

class TempFileManager:
    """Context manager for handling temporary files and directories."""
    def __init__(self):
        self.temp_paths = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def create_temp_dir(self):
        """Create a temporary directory and track it."""
        temp_dir = tempfile.mkdtemp()
        self.temp_paths.append(temp_dir)
        return temp_dir

    def add_path(self, path):
        """Add a path to be cleaned up."""
        self.temp_paths.append(path)

    def cleanup(self):
        """Clean up all temporary files and directories."""
        for path in self.temp_paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                logging.warning(f"Error cleaning up {path}: {str(e)}")

def check_system_dependencies():
    """Check if required system dependencies are installed."""
    try:
        import weasyprint
        test_html = '<p>Test</p>'
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as tmp_file:
            HTML(string=test_html).write_pdf(tmp_file.name)
        return True
    except Exception as e:
        logging.error(f"System dependencies check failed: {str(e)}")
        return False

def format_error_message(error):
    """Format error message for user display."""
    if isinstance(error, Exception):
        return f"{type(error).__name__}: {str(error)}"
    return str(error)

class ProgressTracker:
    """Track progress of long-running operations."""
    def __init__(self, total_steps, description="Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = datetime.now()

    def update(self, step=1):
        """Update progress by specified number of steps."""
        self.current_step += step
        self._log_progress()

    def _log_progress(self):
        """Log progress information."""
        percentage = (self.current_step / self.total_steps) * 100
        elapsed_time = datetime.now() - self.start_time
        logging.info(f"{self.description}: {percentage:.1f}% complete ({self.current_step}/{self.total_steps})")
        logging.debug(f"Elapsed time: {elapsed_time}")

def estimate_memory_usage(file_size, safety_factor=1.5):
    """Estimate memory usage for processing a file."""
    # Rough estimation: file size * safety factor for processing overhead
    return file_size * safety_factor

def check_memory_availability():
    """Check available system memory."""
    try:
        import psutil
        return psutil.virtual_memory().available
    except ImportError:
        return None  # Cannot determine available memory

def is_safe_to_process(file_size):
    """Check if it's safe to process a file given system resources."""
    available_memory = check_memory_availability()
    if available_memory is None:
        return True  # Cannot check, assume it's safe
        
    estimated_usage = estimate_memory_usage(file_size)
    return estimated_usage < available_memory

def create_error_pdf(error_message, output_path):
    """Create a PDF containing error information when conversion fails."""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .error {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>Conversion Error</h1>
        <div class="error">
            <p>{error_message}</p>
            <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    try:
        HTML(string=html_content).write_pdf(output_path)
        return True
    except Exception as e:
        logging.error(f"Error creating error PDF: {str(e)}")
        return False
# MSG to PDF Converter
.msg files (Microsoft Outlook Message files) are widely used for managing and storing email correspondence conversations .
Financial institutions must adhere to strict regulatory requirements for communication retention. .msg files allow emails, attachments, and metadata (like timestamps) to be preserved in their original format for auditing and legal purposes.
A Streamlit web application that converts MSG (Outlook Message) files to PDF format while preserving formatting and attachments.

## Features

- Convert MSG files to PDF format
- Preserve all formatting and inline images
- Save attachments in their original format
- Handle multiple files simultaneously
- Download results as ZIP file

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/msg-to-pdf-converter.git
cd msg-to-pdf-converter
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run app.py
```

## Usage

1. Open the web application
2. Upload one or more MSG files
3. Click "Convert Files"
4. Download the converted files as ZIP

## Development

Requirements:
- Python 3.8+
- Streamlit
- extract-msg
- weasyprint
- Other dependencies in requirements.txt


## License

MIT License

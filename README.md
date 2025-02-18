# Document Management System

A simple and efficient document management system built with Django. This project allows project managers and team members to easily organize, share, and manage documents within a team.

## Features

- User Authentication & Authorization
  - User registration and login/logout
  - Role-based access (Project Manager & Team Member)
- Document Management
  - Upload documents (PDF, Word, Excel, images)
  - View and download documents
  - File type validation
  - Document deletion with proper authorization
- Document Organization
  - Category-based organization
  - Document metadata (title, description, upload date, owner)
- Access Control
  - Private (owner-only) or shared documents
- Search & Filter
  - Search by title, category, or uploader
- Clean and Responsive UI
  - Bootstrap-based dashboard
  - Easy navigation
  - Mobile-friendly design

## Tech Stack

- Backend: Django
- Frontend: HTML, CSS, JavaScript
- Database: SQLite
- CSS Framework: Bootstrap
- File Storage: Local storage
- Authentication: Django's built-in authentication

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/avishekpaul1310/document-management.git
    cd document-management
    ```plaintext

2. Create a virtual environment and activate it:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```plaintext

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Apply migrations:

    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5. Create a superuser:

    ```bash
    python manage.py createsuperuser
    ```

6. Run the development server:

    ```bash
    python manage.py runserver
    ```

7. Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser

## Project Structure

```
document_management/
├── document_management/    # Project settings
├── documents/             # Main app
│   ├── migrations/
│   ├── templates/
│   ├── templatetags/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── static/               # Static files
│   ├── css/
│   └── js/
├── media/               # Uploaded files
├── templates/           # Global templates
├── manage.py
├── requirements.txt
└── README.md
```

## Usage

1. Register a new account or log in with existing credentials
2. Upload documents through the dashboard
3. Organize documents by categories
4. Set document privacy (private/shared)
5. Search and filter documents
6. View, download, or delete documents

## File Type Support

Supported file types:

- PDF (.pdf)
- Microsoft Word (.doc, .docx)
- Microsoft Excel (.xls, .xlsx)
- Images (.png, .jpg, .jpeg)

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Created By

Avishek Paul  
Last Updated: 2025-02-18
# QR Code Authentication System

A robust web-based QR code authentication system built with FastAPI and PostgreSQL. This system allows administrators to manage student records and generate unique QR codes for authentication purposes.

## Features

- Admin Authentication & Authorization
- Student Registration & Management
- QR Code Generation
- Secure API Endpoints
- Audit Logging
- Responsive Admin Dashboard

## Tech Stack

- **Backend:**
  - FastAPI (Python 3.9)
  - SQLAlchemy ORM
  - PostgreSQL Database
  - JWT Authentication
  - Pydantic for data validation

- **Frontend:**
  - HTML5
  - Tailwind CSS
  - JavaScript/jQuery
  - Font Awesome Icons

- **Development Tools:**
  - Docker & Docker Compose
  - uvicorn ASGI server

## Project Structure

```
auth-qrcode/
├── backend/
│   ├── admin/
│   │   ├── adminservice.py    # Admin service logic
│   │   ├── dependencies.py    # Admin dependencies
│   │   ├── model.py          # Admin database models
│   │   └── schema.py         # Admin Pydantic schemas
│   ├── api/
│   │   ├── admin.py          # Admin API routes
│   │   ├── QRroute.py        # QR code routes
│   │   └── student.py        # Student API routes
│   ├── database/
│   │   ├── base.py           # Database initialization
│   │   ├── config.py         # Database configuration
│   │   └── data.py          # Data management
│   ├── qrcode/
│   │   ├── qservice.py       # QR code generation service
│   │   └── util.py           # QR utilities
│   ├── security/
│   │   ├── config.py         # Security configuration
│   │   ├── exceptions.py     # Custom exceptions
│   │   ├── middleware.py     # Security middleware
│   │   ├── password.py       # Password handling
│   │   ├── permissions.py    # Permission management
│   │   └── token.py         # JWT token handling
│   └── student/
│       ├── model.py          # Student database models
│       └── schema.py         # Student Pydantic schemas
├── frontend/
│   ├── admin_dashboard.html  # Admin dashboard
│   ├── admin_login_page.html # Admin login
│   └── index.html           # Main QR generation page
├── .env                     # Environment variables
├── docker-compose.yml       # Docker composition
├── Dockerfile              # Docker configuration
├── main.py                 # Application entry point
└── requirements.txt        # Python dependencies
```

## Setup & Installation

1. Clone the repository:
```sh
git clone <https://github.com/King-kin5/auth-qrcode>
cd auth-qrcode
```

2. Create and configure `.env` file:
```env
DATABASE_URL=postgresql://postgres:password@postgres:5432/Qrcode
SECRET_KEY=your_secret_key
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=your_secure_password
INITIAL_ADMIN_NAME=Admin User
```

3. Run with Docker Compose:
```sh
docker-compose up --build
```

## API Documentation

Once running, access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Key Features

### Admin Management
- Secure admin authentication
- Role-based access control
- Admin activity audit logging
- Password security enforcement

### Student Management
- Student registration
- QR code generation for students
- Student record updates
- Student search functionality

### Security Features
- JWT token authentication
- Password hashing with bcrypt
- Request rate limiting
- SQL injection protection
- Cross-Origin Resource Sharing (CORS)



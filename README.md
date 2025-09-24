# Default Rate Backend API

A FastAPI-based backend service for default rate prediction and analysis with machine learning capabilities.

## 🚀 Features

- **Machine Learning Predictions**: Advanced ML models for default rate prediction
- **User Management**: Multi-role authentication system (Super Admin, JPMorgan Admin, Morgan Admin, Tenant Admin)
- **Data Processing**: Excel/CSV file upload and processing
- **Background Tasks**: Celery-based asynchronous job processing
- **Dashboard API**: Comprehensive statistics and reporting
- **Docker Support**: Production-ready containerization

## 📋 Requirements

- Python 3.9+
- PostgreSQL
- Redis (for Celery)
- Docker (optional)

## 🛠 Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   # Make sure PostgreSQL is running
   # Database will be auto-created on first run
   ```

6. **Start Redis**
   ```bash
   redis-server
   ```

7. **Run the application**
   ```bash
   python main.py
   ```

### Production Deployment

#### Using Docker

```bash
# Build and run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

#### Manual Production Setup

```bash
# Install production dependencies
pip install -r requirements.prod.txt

# Set production environment variables
export ENVIRONMENT=production
export DATABASE_URL=your_production_db_url
export REDIS_URL=your_production_redis_url

# Run with production server
python main.py
```

## 🗂 Project Structure

```
backend/
├── app/                    # Main application code
│   ├── api/               # API routes
│   ├── core/              # Core configuration
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── utils/             # Utility functions
│   └── workers/           # Celery workers
├── deployment/            # Deployment configurations
├── docs/                  # API documentation
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── unused/                # Archived/unused files
├── main.py               # Application entry point
├── requirements.txt      # Development dependencies
├── requirements.prod.txt # Production dependencies
└── docker-compose.prod.yml
```

## 🔧 Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# Application
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000
```

## 🔗 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/change-password` - Change password

### Predictions
- `POST /predictions/annual` - Annual predictions
- `POST /predictions/quarterly` - Quarterly predictions
- `GET /predictions/` - List predictions
- `DELETE /predictions/{id}` - Delete prediction

### Dashboard
- `GET /dashboard/statistics` - Get dashboard statistics
- `GET /dashboard/predictions` - Get predictions summary

### Admin
- `GET /admin/users` - Manage users (admin only)
- `POST /admin/bulk-upload` - Bulk data upload

## 🧪 Testing

```bash
# Run tests (when implemented)
python -m pytest tests/

# Run specific test
python -m pytest tests/test_api.py
```

## 📊 Background Jobs

The application uses Celery for background processing:

```bash
# Start Celery worker
celery -A app.workers.celery worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.workers.celery beat --loglevel=info
```

## 🐳 Docker

### Development
```bash
docker-compose up
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Documentation

- API documentation available at `/docs` (Swagger UI)
- Alternative documentation at `/redoc`
- Additional documentation in `unused/documentation/`

## 🔐 User Roles

1. **Super Admin** - Full system access
2. **JPMorgan Admin** - JPMorgan-specific data access
3. **Morgan Admin** - Morgan-specific data access  
4. **Tenant Admin** - Tenant-specific data access

## 🚀 Deployment

### Railway
The application is configured for Railway deployment with `render.yaml`.

### Custom Server
1. Install production requirements
2. Set environment variables
3. Run database migrations
4. Start the application with `python main.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

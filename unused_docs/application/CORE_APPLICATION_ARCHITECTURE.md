# 🏗️ AccuNode - Core Application Architecture

## 📋 **Table of Contents**
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Database Design](#database-design)
5. [Access Control System](#access-control-system)
6. [ML Pipeline](#ml-pipeline)
7. [Security & Authentication](#security--authentication)

---

## 🎯 **Architecture Overview**

AccuNode is a **multi-tenant ML-based Default Rate Prediction API** built with FastAPI, utilizing machine learning models to predict corporate default probabilities based on financial ratios.

### **System Architecture**
```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATIONS                          │
│   Web Apps │ Mobile Apps │ CLI Tools │ Third-party APIs       │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS/REST API
┌─────────────────────▼───────────────────────────────────────────┐
│                  APPLICATION LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Rate Limit  │  │ Auth/JWT    │  │ CORS/Security│            │
│  │ Middleware  │  │ Middleware  │  │ Headers      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Predictions │  │ Companies   │  │ Auth & User │            │
│  │ API         │  │ API         │  │ Management  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   SERVICE LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ML Prediction│  │Company      │  │Bulk Upload  │            │
│  │Service      │  │Service      │  │Service      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    DATA LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │PostgreSQL   │  │Redis Cache  │  │ML Models    │            │
│  │Database     │  │& Sessions   │  │(.pkl files) │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### **Technology Stack**

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API Framework** | FastAPI 0.104+ | High-performance async REST API |
| **Database** | PostgreSQL 15+ | Primary data storage with ACID compliance |
| **Cache** | Redis 7+ | Session management, rate limiting, caching |
| **ML Framework** | Scikit-learn, LightGBM | Pre-trained models for predictions |
| **Authentication** | JWT (JSON Web Tokens) | Stateless authentication & authorization |
| **Validation** | Pydantic | Request/response data validation |
| **ORM** | SQLAlchemy 2.0+ | Database abstraction and relationships |
| **Async Processing** | Celery + Redis | Background job processing |

---

## 🧩 **Core Components**

### **1. Multi-Tenant Authentication System**

#### **User Role Hierarchy** (5 Levels)
```python
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"      # Platform-wide access
    TENANT_ADMIN = "tenant_admin"    # Cross-organization access  
    ORG_ADMIN = "org_admin"          # Organization admin
    ORG_MEMBER = "org_member"        # Organization member
    USER = "user"                    # Basic authenticated user
```

#### **Access Control Flow**
```
Registration → Email Verification → Role Assignment → Organization Joining
     │              │                    │                    │
     ▼              ▼                    ▼                    ▼
[pending] → [verified] → [role_assigned] → [active_in_org]
```

### **2. Data Access Levels** (3-Tier System)

```python
class AccessLevel(str, Enum):
    PERSONAL = "personal"        # User's own data
    ORGANIZATION = "organization" # Organization shared data  
    SYSTEM = "system"            # Platform-wide public data
```

#### **Data Visibility Matrix**
| User Role | Personal Data | Org Data | System Data | Cross-Org Data |
|-----------|---------------|----------|-------------|----------------|
| `super_admin` | ✅ All | ✅ All | ✅ All | ✅ All |
| `tenant_admin` | ✅ Own | ✅ All Orgs | ✅ All | ✅ All |
| `org_admin` | ✅ Own | ✅ Own Org | ✅ All | ❌ |
| `org_member` | ✅ Own | ✅ Own Org | ✅ All | ❌ |
| `user` | ✅ Own | ❌ | ✅ All | ❌ |

### **3. Prediction Engine Architecture**

```
Financial Data Input → Validation → ML Processing → Risk Assessment → Storage
        │                 │            │              │             │
        ▼                 ▼            ▼              ▼             ▼
   [5 Ratios]     [Schema Check]  [2 Models]   [Risk Levels]   [Database]
```

#### **Annual Prediction Pipeline**
```python
# Input: 5 Financial Ratios
{
    "long_term_debt_to_total_capital": float,  # Leverage ratio
    "total_debt_to_ebitda": float,            # Debt coverage
    "net_income_margin": float,               # Profitability
    "ebit_to_interest_expense": float,        # Interest coverage
    "return_on_assets": float                 # Asset efficiency
}

# ML Models: Ensemble Approach
├── Logistic Regression Model
└── Step Function Model

# Output: Risk Assessment
{
    "probability": float,           # Default probability (0-1)
    "risk_level": str,             # "Low"|"Medium"|"High"  
    "confidence": float,           # Model confidence (0-1)
    "predicted_at": datetime       # Prediction timestamp
}
```

#### **Quarterly Prediction Pipeline**
```python
# Input: 6 Financial Ratios  
{
    "current_ratio": float,                   # Liquidity
    "quick_ratio": float,                     # Immediate liquidity
    "debt_to_equity": float,                  # Capital structure
    "inventory_turnover": float,              # Operational efficiency
    "receivables_turnover": float,            # Collection efficiency
    "working_capital_to_total_assets": float  # Working capital management
}

# ML Models: Advanced Ensemble
├── Logistic Regression Model
├── LightGBM Model  
└── Step Function Model

# Output: Enhanced Risk Assessment
{
    "logistic_probability": float,    # Logistic model result
    "gbm_probability": float,         # LightGBM model result
    "ensemble_probability": float,    # Combined result
    "risk_level": str,               # Risk classification
    "confidence": float,             # Prediction confidence
    "predicted_at": datetime         # Timestamp
}
```

---

## 📊 **Data Flow Diagrams**

### **1. User Registration & Authentication Flow**
```mermaid
graph TD
    A[User Registration] --> B{Email Validation}
    B -->|Valid| C[Send Verification Email]
    B -->|Invalid| D[Return Error]
    C --> E[User Clicks Verification Link]
    E --> F{Token Valid?}
    F -->|Yes| G[Activate Account]
    F -->|No| H[Show Error]
    G --> I[User Can Login]
    I --> J[Generate JWT Token]
    J --> K[Access Protected Resources]
    
    style A fill:#e1f5fe
    style G fill:#c8e6c9
    style D fill:#ffcdd2
    style H fill:#ffcdd2
```

### **2. Prediction Creation Flow**
```mermaid
graph TD
    A[API Request] --> B{Authentication}
    B -->|Valid JWT| C[Extract User Context]
    B -->|Invalid| D[Return 401 Error]
    
    C --> E{Validate Financial Data}
    E -->|Valid| F[Determine Access Level]
    E -->|Invalid| G[Return 400 Error]
    
    F --> H[Create/Find Company]
    H --> I[Check Duplicate Prediction]
    I -->|New| J[Run ML Models]
    I -->|Duplicate| K[Return Conflict Error]
    
    J --> L[Store Prediction]
    L --> M[Return Success Response]
    
    style A fill:#e1f5fe
    style M fill:#c8e6c9
    style D fill:#ffcdd2
    style G fill:#ffcdd2
    style K fill:#fff3e0
```

### **3. Bulk Upload Processing Flow**
```mermaid
graph TD
    A[Upload CSV File] --> B{File Validation}
    B -->|Valid| C[Create Bulk Job]
    B -->|Invalid| D[Return Error]
    
    C --> E[Queue Background Task]
    E --> F[Process Each Row]
    F --> G{Row Valid?}
    G -->|Yes| H[Create Prediction]
    G -->|No| I[Log Error]
    
    H --> J[Increment Success Count]
    I --> K[Increment Error Count]
    
    J --> L{More Rows?}
    K --> L
    L -->|Yes| F
    L -->|No| M[Update Job Status]
    M --> N[Send Completion Notification]
    
    style A fill:#e1f5fe
    style N fill:#c8e6c9
    style D fill:#ffcdd2
```

---

## 🗄️ **Database Design**

### **Core Entity Relationships**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Users       │    │ Organizations   │    │   Companies     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (UUID)       │    │ id (UUID)       │    │ id (UUID)       │
│ email           │◄──►│ name            │    │ symbol          │
│ role            │    │ domain          │    │ name            │
│ organization_id │    │ created_at      │    │ sector          │
│ created_at      │    │ updated_at      │◄──►│ market_cap      │
└─────────────────┘    └─────────────────┘    │ organization_id │
                                              │ access_level    │
                                              └─────────────────┘
                                                       │
                              ┌────────────────────────┴────────────────────────┐
                              ▼                                                 ▼
                    ┌─────────────────┐                              ┌─────────────────┐
                    │AnnualPredictions│                              │QuarterlyPredicts│
                    ├─────────────────┤                              ├─────────────────┤
                    │ id (UUID)       │                              │ id (UUID)       │
                    │ company_id      │                              │ company_id      │
                    │ organization_id │                              │ organization_id │
                    │ reporting_year  │                              │ reporting_year  │
                    │ probability     │                              │ reporting_quarter│
                    │ risk_level      │                              │ ensemble_prob   │
                    │ confidence      │                              │ logistic_prob   │
                    │ access_level    │                              │ gbm_probability │
                    │ created_by      │                              │ risk_level      │
                    │ [5 ratios]      │                              │ [6 ratios]      │
                    └─────────────────┘                              └─────────────────┘
```

### **Key Database Constraints**

#### **Unique Constraints**
```sql
-- Prevent duplicate predictions
UNIQUE(company_id, reporting_year, organization_id) -- Annual
UNIQUE(company_id, reporting_year, reporting_quarter, organization_id) -- Quarterly

-- Ensure unique user emails  
UNIQUE(email)

-- Company symbol uniqueness per organization
UNIQUE(symbol, organization_id)
```

#### **Foreign Key Relationships**
```sql
-- User belongs to organization
users.organization_id → organizations.id

-- Predictions belong to company and user
predictions.company_id → companies.id
predictions.created_by → users.id
predictions.organization_id → organizations.id

-- Companies can belong to organizations  
companies.organization_id → organizations.id
```

### **Indexing Strategy**
```sql
-- Performance optimization indexes
CREATE INDEX idx_predictions_created_at ON annual_predictions(created_at);
CREATE INDEX idx_predictions_company_year ON annual_predictions(company_id, reporting_year);
CREATE INDEX idx_predictions_access_level ON annual_predictions(access_level);
CREATE INDEX idx_predictions_organization ON annual_predictions(organization_id);
CREATE INDEX idx_companies_symbol ON companies(symbol);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);
```

---

## 🔐 **Access Control System**

### **Authentication Flow**
```python
# 1. JWT Token Generation
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 2. Token Validation
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user
```

### **Authorization Levels**

#### **Data Access Rules**
```python
def get_data_access_filter(user: User, prediction_model, include_system: bool = False):
    """Generate SQL filter based on user access permissions"""
    
    if user.role == "super_admin":
        return None  # No filter - access all data
    
    elif user.role == "tenant_admin":
        return None  # No filter - cross-organization access
    
    elif user.organization_id:  # org_admin or org_member
        filters = [
            prediction_model.created_by == str(user.id),  # Own data
            prediction_model.organization_id == user.organization_id  # Org data
        ]
        if include_system:
            filters.append(prediction_model.access_level == "system")
        return or_(*filters)
    
    else:  # user role
        filters = [prediction_model.created_by == str(user.id)]  # Only own data
        if include_system:
            filters.append(prediction_model.access_level == "system")
        return or_(*filters)
```

#### **Resource Permission Matrix**

| Resource | Create | Read | Update | Delete | Bulk Operations |
|----------|--------|------|--------|--------|-----------------|
| **Own Predictions** | ✅ All Roles | ✅ All Roles | ✅ Creator Only | ✅ Creator Only | ✅ All Roles |
| **Org Predictions** | ✅ Org Members+ | ✅ Org Members+ | ✅ Org Admin+ | ✅ Org Admin+ | ✅ Org Admin+ |
| **System Predictions** | ✅ Super Admin | ✅ All Roles | ✅ Super Admin | ✅ Super Admin | ✅ Super Admin |
| **User Management** | ❌ | ✅ Self + Admin | ✅ Self + Admin | ✅ Admin Only | ✅ Admin Only |
| **Organization Management** | ✅ Tenant Admin+ | ✅ Members+ | ✅ Org Admin+ | ✅ Tenant Admin+ | ✅ Tenant Admin+ |

---

## 🤖 **ML Pipeline**

### **Model Architecture**

#### **Annual Prediction Models**
```python
# Model Files Location: /app/models/
├── annual_logistic_model.pkl    # Logistic Regression (primary)
├── annual_step.pkl              # Step Function (secondary) 
└── scoring_info.pkl             # Feature scaling parameters

# Ensemble Logic
def predict_annual(financial_data: dict) -> dict:
    # 1. Data preprocessing & scaling
    scaled_features = scaler.transform(financial_ratios)
    
    # 2. Run both models
    logistic_prob = logistic_model.predict_proba(scaled_features)[0][1]
    step_prob = step_model.predict_proba(scaled_features)[0][1]
    
    # 3. Ensemble combination (weighted average)
    final_probability = (logistic_prob * 0.7) + (step_prob * 0.3)
    
    # 4. Risk categorization
    risk_level = categorize_risk(final_probability)
    confidence = calculate_confidence(logistic_prob, step_prob)
    
    return {
        "probability": final_probability,
        "risk_level": risk_level,
        "confidence": confidence
    }
```

#### **Quarterly Prediction Models**  
```python
# Model Files Location: /app/models/
├── quarterly_lgb_model.pkl       # LightGBM (primary)
├── quarterly_logistic_model.pkl  # Logistic Regression (secondary)
├── quarterly_step.pkl            # Step Function (tertiary)
└── quarterly_scoring_info.pkl    # Feature scaling parameters

# Advanced Ensemble Logic
def predict_quarterly(financial_data: dict) -> dict:
    # 1. Feature engineering & scaling
    scaled_features = quarterly_scaler.transform(financial_ratios)
    
    # 2. Run all three models
    lgb_prob = lgb_model.predict(scaled_features)[0]
    logistic_prob = logistic_model.predict_proba(scaled_features)[0][1] 
    step_prob = step_model.predict_proba(scaled_features)[0][1]
    
    # 3. Weighted ensemble (LightGBM has highest weight)
    ensemble_prob = (lgb_prob * 0.5) + (logistic_prob * 0.3) + (step_prob * 0.2)
    
    # 4. Risk assessment with enhanced confidence
    risk_level = categorize_risk_quarterly(ensemble_prob)
    confidence = calculate_ensemble_confidence(lgb_prob, logistic_prob, step_prob)
    
    return {
        "logistic_probability": logistic_prob,
        "gbm_probability": lgb_prob, 
        "ensemble_probability": ensemble_prob,
        "risk_level": risk_level,
        "confidence": confidence
    }
```

### **Risk Classification System**
```python
def categorize_risk(probability: float) -> str:
    """Convert probability to risk level"""
    if probability < 0.3:
        return "Low"      # < 30% default probability
    elif probability < 0.7:
        return "Medium"   # 30-70% default probability  
    else:
        return "High"     # > 70% default probability

def calculate_confidence(prob1: float, prob2: float) -> float:
    """Calculate model confidence based on agreement"""
    agreement = 1.0 - abs(prob1 - prob2)  # Higher agreement = higher confidence
    return min(max(agreement, 0.0), 1.0)   # Bound between 0-1
```

---

## 🛡️ **Security & Authentication**

### **Security Layers**

#### **1. Input Validation & Sanitization**
```python
# Pydantic Models for Request Validation
class AnnualPredictionRequest(BaseModel):
    company_symbol: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., gt=0)
    sector: str = Field(..., min_length=1, max_length=100)
    reporting_year: str = Field(..., regex=r'^\d{4}$')
    
    # Financial ratios with realistic bounds
    long_term_debt_to_total_capital: float = Field(..., ge=0, le=2.0)
    total_debt_to_ebitda: float = Field(..., ge=0, le=50.0)
    net_income_margin: float = Field(..., ge=-1.0, le=1.0)
    ebit_to_interest_expense: float = Field(..., ge=0, le=100.0)
    return_on_assets: float = Field(..., ge=-1.0, le=1.0)

# SQL Injection Prevention (SQLAlchemy ORM)
# All queries use parameterized statements automatically
```

#### **2. Rate Limiting Strategy**
```python
# Rate limits per endpoint type
RATE_LIMITS = {
    "ml_predictions": "10/minute",      # ML inference endpoints
    "data_read": "100/minute",          # Data retrieval endpoints
    "upload": "5/minute",               # File upload endpoints
    "auth": "20/minute",                # Authentication endpoints
    "analytics": "50/minute"            # Statistics/dashboard endpoints
}

# Implementation using Redis-backed sliding window
@rate_limit_ml
async def create_prediction(request: Request, ...):
    # Rate limiting automatically applied
    pass
```

#### **3. Data Encryption**
```python
# At Rest: Database-level encryption
DATABASE_URL = "postgresql://user:pass@encrypted-rds-endpoint/db"

# In Transit: HTTPS/TLS 1.2+
app.add_middleware(HTTPSRedirectMiddleware)

# Secrets Management: AWS Parameter Store
async def get_secret(parameter_name: str):
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(
        Name=parameter_name,
        WithDecryption=True
    )
    return response['Parameter']['Value']
```

#### **4. Security Headers**
```python
# Security middleware configuration
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY" 
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response
```

### **Audit & Logging**
```python
# Comprehensive logging for security events
logger.info(f"User {user.email} created prediction {prediction.id}")
logger.warning(f"Failed login attempt for {email} from IP {client_ip}")
logger.error(f"Unauthorized access attempt to {endpoint} by user {user.id}")

# Database audit trails
class BaseModel(SQLAlchemyBase):
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)  # Track who created each record
```

---

## 📈 **Performance Optimization**

### **Caching Strategy**
```python
# Redis caching for frequently accessed data
@cache_result(ttl=3600)  # 1 hour cache
async def get_company_predictions(company_id: str):
    # Expensive database query cached
    pass

# Database query optimization
def get_predictions_optimized(user_id: str, page: int = 1):
    return db.query(Prediction)\
        .options(joinedload(Prediction.company))\  # Eager loading
        .filter(Prediction.created_by == user_id)\
        .offset((page-1) * PAGE_SIZE)\
        .limit(PAGE_SIZE)\
        .all()
```

### **Async Processing**
```python
# Background job processing with Celery
@celery_app.task
def process_bulk_upload(file_data: bytes, user_id: str):
    # Long-running bulk operations moved to background
    df = pd.read_csv(io.StringIO(file_data.decode()))
    
    for index, row in df.iterrows():
        # Process each prediction asynchronously
        create_prediction_from_row.delay(row.to_dict(), user_id)
```

This completes the **Core Application Architecture** documentation. Would you like me to continue with the next documentation section? I can proceed with:

2. **Detailed API Documentation**
3. **AWS Infrastructure Guide** 
4. **Local Development Setup**
5. **Production Deployment Guide**

Which section would you like me to work on next?

# 🏠 Local Development Setup Scripts

This directory contains scripts for setting up your local development environment with sample data and admin accounts.

## 📋 Overview

These scripts help you quickly set up a complete local development environment with:
- ✅ Database schema creation
- ✅ Super admin account
- ✅ Sample tenant and organizations
- ✅ Admin accounts at all levels

## 🚀 Quick Start

### 1. Start Docker Services
```bash
# From the backend directory
make start
```

### 2. Run Setup Scripts
```bash
# Step 1: Create super admin
python scripts/local/setup_super_admin_local.py

# Step 2: Create tenant and organizations  
python scripts/local/setup_tenant_local.py
```

Or use the complete setup (if starting fresh):
```bash
make init-local
```

That's it! Your local development environment is ready.

## 📁 Available Scripts

### `complete_local_setup.py` (Recommended)
**The easiest way** - runs everything in sequence:
```bash
python scripts/local/complete_local_setup.py
```

### `setup_super_admin_local.py` 
Creates database schema and super admin:
```bash
python scripts/local/setup_super_admin_local.py
```

### `setup_tenant_local.py`
Sets up sample tenant via API (requires super admin to exist):
```bash
python scripts/local/setup_tenant_local.py
```

## 🔑 Default Credentials

### Super Admin
- 📧 **Email:** `local@accunode.ai`
- 🔐 **Password:** `LocalAdmin2024!`
- 🎯 **Access:** Full system access

### Tenant Admin
- 📧 **Email:** `cro@localbank.dev`
- 🔐 **Password:** `LocalTenantAdmin2024!`
- 🎯 **Access:** Tenant-level management

### Organization Admins

#### 1. Retail Credit Risk Team
- 📧 **Email:** `retail@localbank.dev`
- 🔐 **Password:** `RetailRisk2024!`

#### 2. Corporate Risk Team
- 📧 **Email:** `corporate@localbank.dev`
- 🔐 **Password:** `CorpRisk2024!`

#### 3. Data Science Team
- 📧 **Email:** `analytics@localbank.dev`
- 🔐 **Password:** `DataScience2024!`

## 🗄️ Database Connection (TablePlus)

### Connection Settings:
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `accunode_development`
- **Username:** `admin`
- **Password:** `dev_password_123`

### Connection String:
```
postgresql://admin:dev_password_123@localhost:5432/accunode_development
```

## 🌐 API Access

### Base URLs:
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

### Testing API Endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Login as super admin
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@accunode.local&password=LocalAdmin2024!"

# Get tenants (with token)
curl -X GET "http://localhost:8000/admin/tenants" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🛠️ What Gets Created

### Database Tables:
- `tenants` - Multi-tenant isolation
- `organizations` - Sub-divisions within tenants
- `users` - All user accounts
- `user_roles` - Role assignments
- `api_keys` - API access management

### Sample Data:

#### Tenant: Test Bank Local
- **Name:** Test Bank Local
- **Domain:** testbank.local
- **Description:** Local development tenant

#### Organizations:
1. **Local Credit Risk Team**
   - Domain: risk.testbank.local
   - Focus: Credit risk assessment

2. **Local Operations Team**
   - Domain: ops.testbank.local
   - Focus: Operations and compliance

3. **Local Analytics Team**
   - Domain: analytics.testbank.local
   - Focus: Data analytics and reporting

## 🔧 Troubleshooting

### "Docker services not running"
```bash
# Check Docker status
docker ps

# Start services
make start

# Check logs
make logs
```

### "API not responding"
```bash
# Check API container
docker logs accunode-api-dev

# Restart API
docker restart accunode-api-dev
```

### "Database connection failed"
```bash
# Check PostgreSQL container
docker logs accunode-postgres-dev

# Check if port is available
lsof -i :5432

# Restart database
docker restart accunode-postgres-dev
```

### "Authentication failed"
Make sure you run the database setup first:
```bash
python scripts/local/setup_super_admin_local.py
```

## 🔄 Reset Everything

To start fresh:

```bash
# Stop all services
make stop

# Remove volumes (this deletes all data)
docker volume rm backend_postgres_data backend_redis_data

# Start services again
make start

# Run setup again
python scripts/local/complete_local_setup.py
```

## 📈 Development Workflow

1. **Start Development:**
   ```bash
   make start
   python scripts/local/complete_local_setup.py
   ```

2. **Make Code Changes:**
   - Edit your code (hot reload is enabled)
   - Test with created accounts

3. **Database Exploration:**
   - Use TablePlus with provided credentials
   - Run SQL queries directly

4. **API Testing:**
   - Use Swagger UI at http://localhost:8000/docs
   - Test with different user roles

5. **Clean Slate Testing:**
   - Reset database as shown above
   - Re-run setup scripts

## 🎯 Next Steps

1. **Explore the API:** Visit http://localhost:8000/docs
2. **Connect Database:** Use TablePlus with provided credentials
3. **Test Authentication:** Try logging in with different accounts
4. **Build Features:** Start developing with hot reload enabled
5. **Test Multi-tenancy:** Use different tenant/org accounts

## 📞 Need Help?

- Check Docker logs: `make logs`
- Verify services: `docker ps`
- Test API health: `curl http://localhost:8000/health`
- Review setup output for any error messages

---

*Happy Development! 🚀*

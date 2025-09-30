# Authentication API Performance Testing Suite

This comprehensive testing framework is designed to measure and optimize the performance of authentication APIs in your FastAPI backend.

## 🎯 Tested APIs

### Authentication Endpoints (`/api/v1/auth`)
- **POST** `/api/v1/auth/register` - User registration
- **POST** `/api/v1/auth/login` - User authentication  
- **POST** `/api/v1/auth/refresh` - Token refresh
- **POST** `/api/v1/auth/logout` - User logout
- **POST** `/api/v1/auth/change-password` - Password change
- **POST** `/api/v1/auth/join` - Organization join

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd performance_tests
chmod +x setup.sh
./setup.sh
```

### 2. Start Your API Server
Make sure your FastAPI server is running:
```bash
cd ../
uvicorn app.main:app --reload --port 8000
```

### 3. Run Tests

#### Basic Performance Tests
```bash
python3 run_auth_tests.py --test-type basic
```

#### Concurrent Load Tests (10 users)
```bash
python3 run_auth_tests.py --test-type concurrent --users 10
```

#### Stress Test (up to 50 users)
```bash
python3 run_auth_tests.py --test-type stress --max-users 50
```

#### Full Test Suite
```bash
python3 run_auth_tests.py --test-type full
```

## 📊 Test Types

### 1. Basic Performance Tests
- **Sequential testing** of each auth endpoint
- **Response time measurement** (average, min, max, P95, P99)
- **Success/failure rate** analysis
- **Memory and CPU usage** monitoring
- **Validation error handling** performance

### 2. Concurrent Load Tests
- **Multiple simulated users** making requests simultaneously
- **Realistic user flows** (register → login → logout cycles)
- **Throughput measurement** (requests per second)
- **Concurrent request handling** analysis
- **Resource contention** detection

### 3. Stress Tests
- **Gradual load increase** (5 → 10 → 20 → 30+ users)
- **Breaking point identification**
- **Performance degradation** analysis
- **Error rate monitoring** under high load

## 📈 Performance Thresholds

Current performance expectations:

| Endpoint | Threshold | Description |
|----------|-----------|-------------|
| `/register` | 2000ms | User registration |
| `/login` | 1000ms | User authentication |
| `/refresh` | 500ms | Token refresh |
| `/logout` | 200ms | User logout |
| `/change-password` | 1500ms | Password change |
| `/join` | 1500ms | Organization join |

## 📋 Test Results

### Sample Output
```
==============================================================
Performance Test Results: /api/v1/auth/login
==============================================================
Total Requests:     50
Successful:         48
Failed:             2
Error Rate:         4.00%
Throughput:         16.67 req/sec

Response Times (ms):
Average:            234.56
Min:                89.12
Max:                1245.67
95th Percentile:    456.78
99th Percentile:    987.65

Threshold (1000ms): ✓ PASS
==============================================================
```

## 🔧 Configuration

### Environment Variables
```bash
export API_BASE_URL="http://localhost:8000"
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
```

### Test Configuration (`config.py`)
```python
TEST_CONFIG = {
    "concurrent_users": [1, 5, 10, 20, 50],
    "test_duration": 30,
    "iterations_per_user": 10,
    "timeout": 30,
    "delay_between_requests": 0.1
}
```

## 📁 Directory Structure
```
performance_tests/
├── config.py                      # Test configuration
├── requirements.txt                # Testing dependencies
├── setup.sh                      # Environment setup
├── run_auth_tests.py             # Main test runner
├── auth_apis/
│   ├── test_auth_performance.py   # Sequential auth tests
│   └── test_concurrent_auth.py    # Concurrent/load tests
├── utils/
│   └── test_utils.py             # Testing utilities
└── reports/                      # Test reports (auto-generated)
```

## 🎛️ Advanced Usage

### Custom Test Configuration
```bash
# Test against production API
python3 run_auth_tests.py --url https://your-api.com --test-type basic

# High-load concurrent test
python3 run_auth_tests.py --test-type concurrent --users 100

# Extended stress test
python3 run_auth_tests.py --test-type stress --max-users 200
```

### Programmatic Usage
```python
from auth_apis.test_auth_performance import AuthAPITester

# Create tester
tester = AuthAPITester("http://localhost:8000")

# Run specific tests
await tester.test_login_performance(iterations=20)
await tester.test_register_performance(iterations=15)
```

## 📊 Performance Optimization Tips

Based on test results, here are common optimization areas:

### 1. Database Optimization
- **Connection pooling** - Use SQLAlchemy connection pools
- **Query optimization** - Add indexes on email, username fields
- **Async database operations** - Use asyncpg for PostgreSQL

### 2. Password Hashing
- **Bcrypt rounds** - Reduce from 12 to 10 for better performance
- **Async hashing** - Move password hashing to background tasks

### 3. JWT Token Generation
- **Token caching** - Cache user data in tokens to reduce DB queries
- **Faster algorithms** - Consider RS256 for better performance

### 4. API Response Optimization
- **Response compression** - Enable gzip compression
- **Minimal responses** - Return only necessary data
- **Async endpoints** - Use async/await throughout

### 5. Caching Layer
- **Redis integration** - Cache user sessions and permissions
- **Query result caching** - Cache frequent database queries

## 🔍 Interpreting Results

### Good Performance Indicators
- ✅ Response times under thresholds
- ✅ Error rate < 5%
- ✅ Linear scalability with concurrent users
- ✅ Stable memory usage

### Performance Issues
- ❌ Response times exceeding thresholds
- ❌ Error rate > 15%
- ❌ Exponential response time growth
- ❌ Memory leaks or excessive CPU usage

### Common Issues & Solutions
1. **High login times** → Check password hashing complexity
2. **Database timeouts** → Optimize queries, add connection pooling  
3. **Memory growth** → Check for connection leaks
4. **High error rates** → Review validation logic and error handling

## 🛠️ Troubleshooting

### Server Not Responding
```bash
# Check if server is running
curl http://localhost:8000/

# Check server logs for errors
tail -f app.log
```

### Test Dependencies Issues
```bash
# Reinstall requirements
pip install --upgrade -r requirements.txt

# Check Python version (requires 3.8+)
python3 --version
```

### Database Connection Issues
```bash
# Check database connectivity
psql -h localhost -U username -d database_name

# Verify DATABASE_URL format
echo $DATABASE_URL
```

## 📧 Support

For issues and questions:
1. Check the test output for specific error messages
2. Review server logs during test execution  
3. Ensure all dependencies are properly installed
4. Verify API server is running and accessible

## 🎯 Next Steps

After running auth tests, expand to other API sections:
- **User Management APIs** (`/api/v1/users`)  
- **Organization APIs** (`/api/v1/organizations`)
- **Prediction APIs** (`/api/v1/predictions`)
- **Company APIs** (`/api/v1/companies`)

Each section can use similar testing patterns with endpoint-specific optimizations.

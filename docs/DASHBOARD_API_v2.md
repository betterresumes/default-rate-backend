# Dashboard API v2 - Enhanced Performance

## Overview

The Dashboard API has been significantly enhanced for performance and flexibility:

1. **Removed super admin restriction** from `/stats` - now all authenticated users can access platform statistics
2. **Converted `/dashboard` to POST** - allows passing custom parameters and organization details
3. **Major performance optimizations** - should achieve sub-15 second response times
4. **Platform statistics integration** - users can get both their data + platform stats in one call

## API Endpoints

### 1. Platform Statistics (Available to All Users)

```http
GET /api/v1/predictions/stats
```

**Access**: All authenticated users (previously super admin only)

**Response**: Complete platform statistics including:
- Total predictions, companies, users, organizations
- Breakdown by access level, organization, user role
- Top contributors and most predicted companies
- Recent activity metrics

### 2. Dashboard Statistics (Enhanced POST)

```http
POST /api/v1/predictions/dashboard
Content-Type: application/json

{
  "include_platform_stats": true,
  "organization_filter": "optional_org_id",
  "custom_scope": "personal|organization|tenant|system"
}
```

**Request Parameters**:
- `include_platform_stats` (boolean, default: true): Include platform-wide statistics
- `organization_filter` (string, optional): Override organization ID for data scope
- `custom_scope` (string, optional): Override user's default scope

**Response Structure**:
```json
{
  "scope": "personal|organization|tenant|system",
  "user_name": "User Name",
  "organization_name": "Org Name",
  "total_companies": 150,
  "total_predictions": 1200,
  "average_default_rate": 0.0850,
  "high_risk_companies": 25,
  "sectors_covered": 8,
  "data_scope": "Description of data scope",
  "platform_statistics": {
    "total_companies": 5000,
    "total_users": 200,
    "total_organizations": 50,
    "total_predictions": 15000,
    "average_default_rate": 0.0920,
    "high_risk_companies": 750,
    "sectors_covered": 15
  },
  "organizations_breakdown": [...],  // For tenant admin
  "tenants_breakdown": [...]         // For super admin
}
```

## Performance Optimizations

### 1. SQL Query Optimizations

- **Single-query approach**: Replaced N+1 query patterns with complex CTEs
- **Window functions**: Used for efficient latest-per-company calculations  
- **Aggregate optimization**: Moved calculations to SQL level instead of Python loops
- **Index-friendly queries**: Designed queries to leverage database indexes

### 2. Database Indexes

Critical indexes for performance (create these in production):

```sql
-- Company indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_org_access 
ON companies(organization_id, access_level);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_created_by 
ON companies(created_by);

-- Prediction indexes  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_annual_company_created 
ON annual_predictions(company_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quarterly_company_created 
ON quarterly_predictions(company_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_annual_probability 
ON annual_predictions(probability) WHERE probability IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quarterly_logistic 
ON quarterly_predictions(logistic_probability) WHERE logistic_probability IS NOT NULL;
```

### 3. Expected Performance

- **Before**: 60-78 seconds
- **After**: Under 10-15 seconds  
- **Improvement**: 5-8x faster

## Usage Examples

### Example 1: Personal User Dashboard with Platform Stats

```http
POST /api/v1/predictions/dashboard
{
  "include_platform_stats": true
}
```

### Example 2: Organization Admin Viewing Another Org

```http
POST /api/v1/predictions/dashboard
{
  "include_platform_stats": true,
  "organization_filter": "different-org-id",
  "custom_scope": "organization"
}
```

### Example 3: Tenant Admin System View

```http
POST /api/v1/predictions/dashboard
{
  "include_platform_stats": true,
  "custom_scope": "system"
}
```

## Migration Notes

### For Frontend Developers

1. **Update API calls**: Change GET to POST for `/dashboard`
2. **Add request body**: Include parameters as needed
3. **Handle platform_statistics**: New field in response
4. **Update organization filter**: Can now pass specific org ID

### For Backend Deployment

1. **Database indexes**: Run index creation script in production
2. **Connection pooling**: Ensure adequate pool size for performance
3. **Monitor queries**: Use database logs to verify query performance
4. **Test endpoints**: Verify sub-15 second response times

## Security & Access Control

- **Stats endpoint**: All authenticated users can access (changed from super admin only)
- **Dashboard endpoint**: Respects user roles and access levels
- **Organization filter**: Users can only access orgs they have permissions for
- **Data scope**: Automatically determined by user role unless overridden

## Performance Monitoring

Monitor these metrics:
- Response time for `/dashboard` endpoint (target: <15 seconds)
- Database query execution time
- Index usage statistics
- Connection pool utilization

Use these queries to monitor performance:

```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
WHERE query LIKE '%predictions%' 
ORDER BY mean_time DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE tablename IN ('companies', 'annual_predictions', 'quarterly_predictions');
```

## Troubleshooting

### Slow Performance
1. Verify indexes are created and being used
2. Check database connection pool settings
3. Monitor query execution plans
4. Consider query timeout settings

### High Memory Usage  
1. Limit result set sizes in queries
2. Use pagination for large datasets
3. Monitor database connection counts
4. Consider query result caching

### Access Issues
1. Verify user roles and permissions
2. Check organization_id relationships
3. Validate request parameters
4. Review access control logic

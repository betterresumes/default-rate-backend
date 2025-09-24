# 🔧 Job Management API Documentation

This document describes the comprehensive **Job Management APIs** for monitoring, managing, and controlling bulk upload jobs in the Financial Default Risk Prediction system.

## 📋 Overview

The Job Management API provides three main endpoints for interacting with bulk upload jobs:

1. **`GET /api/v1/predictions/jobs/{job_id}`** - Get comprehensive job details
2. **`DELETE /api/v1/predictions/jobs/{job_id}`** - Delete completed/failed jobs  
3. **`POST /api/v1/predictions/jobs/{job_id}/cancel`** - Cancel running jobs

These endpoints complement the existing job status and listing endpoints to provide complete job lifecycle management.

---

## 🔍 GET Job Details

### **Endpoint**
```http
GET /api/v1/predictions/jobs/{job_id}?include_errors=true
```

### **Description**
Retrieves comprehensive information about a specific bulk upload job, including progress metrics, performance statistics, error details, and timestamps.

### **Parameters**
- **`job_id`** (path, required) - UUID of the job
- **`include_errors`** (query, optional) - Set to `true` to include detailed error information

### **Response Example**
```json
{
  "success": true,
  "job": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "job_type": "annual",
    
    "file_info": {
      "original_filename": "annual_predictions_1000_rows.csv",
      "file_size": 2048576,
      "file_size_mb": 1.95
    },
    
    "progress": {
      "total_rows": 1000,
      "processed_rows": 1000,
      "successful_rows": 985,
      "failed_rows": 15,
      "progress_percentage": 100.0,
      "remaining_rows": 0
    },
    
    "performance": {
      "processing_time_seconds": 125.5,
      "rows_per_second": 7.97,
      "estimated_completion_time": null
    },
    
    "timestamps": {
      "created_at": "2024-01-15T10:30:00Z",
      "started_at": "2024-01-15T10:30:05Z", 
      "completed_at": "2024-01-15T10:32:10Z",
      "updated_at": "2024-01-15T10:32:10Z"
    },
    
    "context": {
      "user_id": "user-uuid",
      "organization_id": "org-uuid",
      "created_by": "john.doe"
    },
    
    "errors": {
      "has_errors": true,
      "error_message": null,
      "error_details": {
        "errors": [
          {
            "row": 45,
            "company_symbol": "INVALID",
            "error": "Invalid market cap value"
          },
          {
            "row": 123,
            "company_symbol": "TEST123",
            "error": "Missing required field: sector"
          }
        ]
      },
      "error_count": 15
    },
    
    "celery_info": {
      "task_id": "celery-task-uuid",
      "celery_status": "SUCCESS",
      "celery_meta": null
    }
  }
}
```

### **For Active Jobs**
When a job is still processing, additional estimated completion info is provided:

```json
{
  "performance": {
    "processing_time_seconds": 45.2,
    "rows_per_second": 8.85,
    "estimated_completion_seconds": 85,
    "estimated_completion_time": "1m 25s"
  }
}
```

### **Access Control**
- Users can only view jobs they created
- Organization members can view jobs from their organization
- Super admins can view all jobs

---

## 🗑️ DELETE Job

### **Endpoint**
```http
DELETE /api/v1/predictions/jobs/{job_id}
```

### **Description**
Permanently deletes a bulk upload job from the database. Jobs can be deleted in any status except when they are currently processing.

### **Restrictions**
- ✅ **Can delete**: `pending`, `queued`, `completed`, `failed` jobs
- ❌ **Cannot delete**: `processing` jobs (must cancel first or wait for completion)

### **Response Example**
```json
{
  "success": true,
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 deleted successfully",
  "deleted_job": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "job_type": "annual",
    "original_filename": "annual_data.csv"
  }
}
```

### **Error Responses**
```json
// Job currently processing
{
  "detail": "Cannot delete job that is currently processing. Please cancel the job first or wait for it to complete."
}

// Job not found
{
  "detail": "Job not found or access denied"
}
```

---

## ⏹️ CANCEL Job

### **Endpoint**
```http
POST /api/v1/predictions/jobs/{job_id}/cancel
```

### **Description**
Cancels a running bulk upload job and attempts to terminate the associated Celery background task.

### **What it does:**
1. **Validates** job can be cancelled (pending or processing status)
2. **Terminates** Celery background task (if exists)
3. **Updates** job status to `failed` with cancellation message
4. **Records** completion timestamp

### **Restrictions**
- ✅ **Can cancel**: `pending`, `processing` jobs
- ❌ **Cannot cancel**: `completed`, `failed` jobs

### **Response Example**
```json
{
  "success": true,
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 cancelled successfully",
  "cancelled_job": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "job_type": "quarterly",
    "original_filename": "quarterly_data.xlsx",
    "celery_cancelled": true
  }
}
```

### **Error Responses**
```json
// Job already completed
{
  "detail": "Cannot cancel job with status 'completed'. Only pending or processing jobs can be cancelled."
}

// Job not found
{
  "detail": "Job not found or access denied"
}
```

---

## 🔐 Security & Access Control

### **Authentication**
All endpoints require:
- Valid JWT token in `Authorization: Bearer <token>` header
- User must have at least "user" role permissions

### **Authorization Levels**
- **Personal Jobs**: Users can manage jobs they created
- **Organization Jobs**: Organization members can manage jobs from their org
- **System Jobs**: Super admins can manage all jobs

### **Data Isolation**
Jobs are automatically filtered by:
```sql
-- For organization users
WHERE organization_id = user.organization_id

-- For personal users  
WHERE user_id = current_user.id
```

---

## 📊 Usage Examples

### **1. Get Detailed Job Information**
```bash
curl -X GET "https://api.example.com/api/v1/predictions/jobs/550e8400-e29b-41d4-a716-446655440000?include_errors=true" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### **2. Monitor Active Job Progress** 
```bash
# Get job details every 5 seconds
while true; do
  curl -s -X GET "https://api.example.com/api/v1/predictions/jobs/$JOB_ID" \
    -H "Authorization: Bearer $JWT_TOKEN" | \
    jq '.job.progress.progress_percentage, .job.performance.estimated_completion_time'
  sleep 5
done
```

### **3. Cancel a Running Job**
```bash
curl -X POST "https://api.example.com/api/v1/predictions/jobs/550e8400-e29b-41d4-a716-446655440000/cancel" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### **4. Clean Up Completed Jobs**
```bash
# List completed jobs
COMPLETED_JOBS=$(curl -s -X GET "https://api.example.com/api/v1/predictions/jobs?status=completed&limit=100" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq -r '.jobs[].id')

# Delete each completed job
for job_id in $COMPLETED_JOBS; do
  curl -X DELETE "https://api.example.com/api/v1/predictions/jobs/$job_id" \
    -H "Authorization: Bearer $JWT_TOKEN"
done
```

---

## 📈 Performance Metrics

### **Available Metrics**
- **Processing Speed**: Rows per second
- **Progress Tracking**: Percentage completion  
- **Time Estimates**: Estimated completion time for active jobs
- **Error Rates**: Failed rows vs total rows
- **File Information**: Original filename and file size

### **Calculated Fields**
```python
# Progress percentage
progress_percentage = (processed_rows / total_rows) * 100

# Processing speed
rows_per_second = processed_rows / processing_time_seconds

# Estimated completion
remaining_rows = total_rows - processed_rows
estimated_seconds = remaining_rows / rows_per_second
```

---

## 🔧 Integration with Existing Endpoints

### **Complete Job Management Workflow**

1. **Start Job**
   ```http
   POST /api/v1/predictions/annual/bulk-upload-async
   ```

2. **Monitor Progress**
   ```http
   GET /api/v1/predictions/jobs/{job_id}/status  # Quick status
   GET /api/v1/predictions/jobs/{job_id}         # Detailed info
   ```

3. **Manage Jobs**
   ```http
   GET /api/v1/predictions/jobs                  # List all jobs
   POST /api/v1/predictions/jobs/{job_id}/cancel # Cancel if needed
   DELETE /api/v1/predictions/jobs/{job_id}      # Delete when done
   ```

### **Status Endpoint Comparison**

| Endpoint | Purpose | Response Size | Use Case |
|----------|---------|---------------|----------|
| `/jobs/{id}/status` | Quick status check | Small | Real-time monitoring |
| `/jobs/{id}` | Complete job details | Large | Detailed analysis |

---

## 📝 Response Schema

### **Job Details Schema**
```typescript
interface JobDetails {
  id: string
  status: "pending" | "processing" | "completed" | "failed"
  job_type: "annual" | "quarterly"
  
  file_info: {
    original_filename: string
    file_size?: number
    file_size_mb?: number
  }
  
  progress: {
    total_rows: number
    processed_rows: number
    successful_rows: number
    failed_rows: number
    progress_percentage: number
    remaining_rows: number
  }
  
  performance: {
    processing_time_seconds?: number
    rows_per_second?: number
    estimated_completion_seconds?: number
    estimated_completion_time?: string
  }
  
  timestamps: {
    created_at?: string
    started_at?: string
    completed_at?: string
    updated_at?: string
  }
  
  context: {
    user_id: string
    organization_id?: string
    created_by?: string
  }
  
  errors: {
    has_errors: boolean
    error_message?: string
    error_details?: any
    error_count?: number
  }
  
  celery_info: {
    task_id?: string
    celery_status?: string
    celery_meta?: any
  }
}
```

These comprehensive job management APIs provide complete control over the bulk upload job lifecycle, from creation through completion and cleanup.

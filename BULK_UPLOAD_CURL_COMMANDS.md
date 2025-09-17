# Bulk Upload API - cURL Commands

This document contains ready-to-use cURL commands for testing the bulk upload endpoints with your authentication token.

## 🔐 Authentication Token
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk
```

## 📋 Available Files

### Annual Files (600 companies total)
- `files/bulk_upload_files/annual_predictions_part_1.xlsx` (150 companies)
- `files/bulk_upload_files/annual_predictions_part_2.xlsx` (150 companies)
- `files/bulk_upload_files/annual_predictions_part_3.xlsx` (150 companies)
- `files/bulk_upload_files/annual_predictions_part_4.xlsx` (150 companies)

### Quarterly Files (610 companies total)
- `files/quarterly_upload_files/quarterly_predictions_part_1.xlsx` (150 companies)
- `files/quarterly_upload_files/quarterly_predictions_part_2.xlsx` (150 companies)
- `files/quarterly_upload_files/quarterly_predictions_part_3.xlsx` (150 companies)
- `files/quarterly_upload_files/quarterly_predictions_part_4.xlsx` (150 companies)
- `files/quarterly_upload_files/quarterly_test_10_records.xlsx` (10 companies - test file)

---

## 📊 Annual Bulk Upload (Async)

### Annual File 1
```bash
curl -X POST "http://localhost:8000/api/predictions/bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/bulk_upload_files/annual_predictions_part_1.xlsx" \
  -F "prediction_type=annual"
```

### Annual File 2
```bash
curl -X POST "http://localhost:8000/api/predictions/bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/bulk_upload_files/annual_predictions_part_2.xlsx" \
  -F "prediction_type=annual"
```

### Annual File 3
```bash
curl -X POST "http://localhost:8000/api/predictions/bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/bulk_upload_files/annual_predictions_part_3.xlsx" \
  -F "prediction_type=annual"
```

### Annual File 4
```bash
curl -X POST "http://localhost:8000/api/predictions/bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/bulk_upload_files/annual_predictions_part_4.xlsx" \
  -F "prediction_type=annual"
```

---

## 📈 Quarterly Bulk Upload (Async)

### Quarterly Test File (10 companies) - **Start Here**
```bash
curl -X POST "http://localhost:8000/api/predictions/quarterly-bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/quarterly_upload_files/quarterly_test_10_records.xlsx"
```

### Quarterly File 1
```bash
curl -X POST "http://localhost:8000/api/predictions/quarterly-bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/quarterly_upload_files/quarterly_predictions_part_1.xlsx"
```

### Quarterly File 2
```bash
curl -X POST "http://localhost:8000/api/predictions/quarterly-bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/quarterly_upload_files/quarterly_predictions_part_2.xlsx"
```

### Quarterly File 3
```bash
curl -X POST "http://localhost:8000/api/predictions/quarterly-bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/quarterly_upload_files/quarterly_predictions_part_3.xlsx"
```

### Quarterly File 4
```bash
curl -X POST "http://localhost:8000/api/predictions/quarterly-bulk-predict-async" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
  -F "file=@files/quarterly_upload_files/quarterly_predictions_part_4.xlsx"
```

---

## 📊 Monitor Job Status

After each upload, you'll receive a response with a `job_id`. Use this command to check the status:

```bash
curl -X GET "http://localhost:8000/api/predictions/job-status/YOUR_JOB_ID_HERE" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk"
```

### Example Response After Upload:
```json
{
  "success": true,
  "message": "Quarterly bulk prediction job submitted successfully. Processing 150 companies in background.",
  "job_id": "cea23916-6ac0-4b2c-a00a-fd8d1a3d87d0",
  "status": "PENDING",
  "filename": "quarterly_predictions_part_1.xlsx",
  "estimated_processing_time": "3.8-7.5 minutes"
}
```

### Job Status Response:
```json
{
  "success": true,
  "job_id": "cea23916-6ac0-4b2c-a00a-fd8d1a3d87d0",
  "status": "SUCCESS",
  "message": "Job completed successfully",
  "progress": null,
  "result": {
    "success": true,
    "message": "Quarterly bulk processing completed. Success: 150, Failed: 0",
    "total_processed": 150,
    "successful_predictions": 150,
    "failed_predictions": 0,
    "processing_time": 45.23
  }
}
```

---

## 🎯 Key Differences

### Annual Endpoints:
- **Endpoint:** `/api/predictions/bulk-predict-async`
- **Required Parameter:** `prediction_type=annual`
- **Features Used:** 5 annual financial ratios
- **ML Model:** Annual ML model

### Quarterly Endpoints:
- **Endpoint:** `/api/predictions/quarterly-bulk-predict-async`
- **Required Parameter:** None (dedicated endpoint)
- **Features Used:** 4 quarterly financial ratios  
- **ML Model:** Quarterly ML model

---

## 🚀 Recommended Testing Order

1. **Start with test file:**
   ```bash
   # Test quarterly endpoint with small file first
   curl -X POST "http://localhost:8000/api/predictions/quarterly-bulk-predict-async" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
     -F "file=@files/quarterly_upload_files/quarterly_test_10_records.xlsx"
   ```

2. **Then upload one large file to verify:**
   ```bash
   # Upload one quarterly file
   curl -X POST "http://localhost:8000/api/predictions/quarterly-bulk-predict-async" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkODk1MDVhYS00OWJmLTQyMjUtOTQxNy0wNDhiZTAyOTkyMzQiLCJleHAiOjE3NTgxMjk0Nzd9.KA4AonVFBkFcoVZg_qpZ_-DNpRGsGschj0fxhGc7BYk" \
     -F "file=@files/quarterly_upload_files/quarterly_predictions_part_1.xlsx"
   ```

3. **Monitor progress and then upload remaining files**

---

## 📈 System Status

- **FastAPI Server:** http://localhost:8000
- **Health Check:** `GET /health`
- **Authentication:** Bearer token required
- **File Formats:** Excel (.xlsx) files
- **Processing:** Background async jobs with Celery
- **Total Capacity:** ~1200 company predictions available

---

## 🔧 Troubleshooting

If you get authentication errors, re-login to get a fresh token:
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patil@gmail.com",
    "password": "Test123*"
  }'
```

**File not found errors:** Make sure you're running the commands from the backend directory where the `files/` folder is located.

---

*Generated on: September 17, 2025*

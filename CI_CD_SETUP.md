# 🚀 CI/CD Pipeline Setup Instructions

## 📋 **Complete CI/CD Pipeline for AccuNode Production**

### ✅ **What's Configured:**
- **Trigger**: Only `prod` branch (no main branch)
- **Images**: Keep 7 most recent versions in ECR
- **Platform**: `linux/amd64` (same as your manual builds)
- **Security**: Automatic vulnerability scanning on PRs
- **Deployment**: Fully automated to ECS Fargate
- **Rollback**: Automatic rollback on failures

## 🔐 **Required: GitHub Secrets Setup**

### **Step 1: Get Your AWS Credentials**

You're currently using IAM user: `pranit` (Account: 461962182774)

You need to add these **2 secrets** to GitHub:

### **Step 2: Add Secrets to GitHub Repository**

1. **Go to GitHub Repository Settings:**
   ```
   https://github.com/betterresumes/default-rate-backend/settings/secrets/actions
   ```

2. **Click "New repository secret" and add:**

   **Secret 1:**
   - Name: `AWS_ACCESS_KEY_ID`
   - Value: `AKIA...` (your access key ID)

   **Secret 2:**
   - Name: `AWS_SECRET_ACCESS_KEY`  
   - Value: `your-secret-access-key`

### **Step 3: Find Your AWS Credentials**

**Option A: From AWS CLI config**
```bash
cat ~/.aws/credentials
# Look for:
# [default]
# aws_access_key_id = AKIA...
# aws_secret_access_key = ...
```

**Option B: From environment variables**
```bash
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
```

**Option C: Create new credentials (if needed)**
```bash
# If you don't have the secret key, create new ones:
aws iam create-access-key --user-name pranit
```

## 🚀 **How the Pipeline Works**

### **Workflow Triggers:**

#### **1. Pull Request to `prod`:**
```
Code → PR → Security Scan → Build & Test → Feedback
```
- ✅ Security vulnerability check
- ✅ Code quality validation  
- ✅ Docker build test
- ❌ **NO deployment** (safe testing)

#### **2. Push to `prod` branch:**
```
Code → Build → Test → Deploy → Health Check → Success/Rollback
```
- ✅ Build new Docker image with unique tag
- ✅ Push to ECR with tags: `prod-<commit>`, `latest` 
- ✅ Update ECS task definitions
- ✅ Deploy API and Worker services
- ✅ Wait for deployment completion
- ✅ Verify health status
- ✅ Auto-rollback if failures

### **Image Tags Generated:**
```bash
# For commit abc123def on prod branch:
accunode:prod-abc123def    # Unique deployment tag
accunode:abc123def         # Commit SHA tag  
accunode:prod              # Branch tag
accunode:latest           # Latest production
```

### **ECR Lifecycle Management:**
- **Keeps**: 7 most recent tagged images
- **Deletes**: Older images automatically
- **Cleans**: Untagged images after 1 day
- **Cost**: ~$1-2/month for 7 images

## ✅ **Testing the Pipeline**

### **Step 1: Test with PR first**
```bash
git checkout -b test-pipeline
git add .
git commit -m "test: pipeline setup"
git push origin test-pipeline
# Create PR to prod branch → Should run security scan + build
```

### **Step 2: Deploy to production**  
```bash
git checkout prod
git merge test-pipeline
git push origin prod
# Should trigger full deployment
```

### **Step 3: Monitor deployment**
- GitHub Actions tab: See real-time progress
- ECS Console: Watch service updates
- CloudWatch Logs: Monitor application logs

## 🔄 **Rollback Options**

### **Automatic Rollback:**
- Pipeline automatically rolls back on deployment failures
- Uses previous task definition versions

### **Manual Rollback:**
```bash
# Option 1: Revert to previous commit
git revert <commit-hash>
git push origin prod

# Option 2: Use ROLLBACK_PLAN.md commands
# Option 3: ECS Console manual rollback
```

## 📊 **Benefits You Get:**

✅ **Zero Manual Work**: Push code → Automatic deployment  
✅ **Safety**: Auto-rollback + health checks  
✅ **Cost Efficient**: Only 7 recent images  
✅ **Security**: Vulnerability scanning  
✅ **Traceability**: Each deployment tied to exact commit  
✅ **Reliability**: Same platform, same process every time  

## 🎯 **Next Steps:**

1. **Add AWS secrets to GitHub** (required)
2. **Test with a PR** (recommended) 
3. **Deploy to production** (push to prod branch)
4. **Monitor first deployment** 
5. **Enjoy automated deployments!** 🚀

---

**Pipeline Status:** ✅ Ready to use (just needs GitHub secrets)  
**ECR Lifecycle:** ✅ Applied (keeps 7 images)  
**Production Safety:** ✅ Auto-rollback enabled

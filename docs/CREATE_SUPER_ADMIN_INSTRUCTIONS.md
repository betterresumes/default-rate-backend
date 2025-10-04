# 🚀 Create Super Admin in Private RDS Database

Since your RDS is private, you need to access it from within AWS. Here's the **easiest way**:

## 📋 Step-by-Step Instructions

### 1️⃣ Open AWS CloudShell
- Go to AWS Console: https://console.aws.amazon.com
- Click the CloudShell icon `>_` in the top toolbar
- Wait ~30 seconds for CloudShell to load

### 2️⃣ Copy & Paste the Script
Copy the **entire content** of `scripts/cloudshell-create-superadmin.sh` and paste it into CloudShell terminal.

### 3️⃣ Press Enter
The script will:
- Install PostgreSQL client
- Install Python dependencies  
- Create the super admin user in your RDS database
- Verify the creation

### 4️⃣ Expected Output
```
🎉 SUPER ADMIN VERIFIED:
   ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Email: admin@accunode.ai
   Username: accunode
   Role: super_admin
   Active: True

🔐 Credentials: admin@accunode.ai / SuperaAdmin123*
```

## 🔐 Super Admin Credentials
- **Email:** admin@accunode.ai
- **Password:** SuperaAdmin123*
- **Username:** accunode
- **Role:** super_admin

## ✅ After Creation
You can now use these credentials to:
1. Login to your admin APIs
2. Create tenants using super admin endpoints
3. Manage the entire system

## 🚨 Alternative: Temporary Public Access (Not Recommended)
If CloudShell doesn't work, you can temporarily make RDS public:

1. Go to RDS Console → Find `accunode-postgres`
2. Click "Modify" → Set "Public accessibility" to "Yes"
3. Update Security Group to allow your IP on port 5432
4. Wait 5-10 minutes, then run the local script
5. **Important:** Make it private again after setup!

---

💡 **CloudShell is the safest and free option!**

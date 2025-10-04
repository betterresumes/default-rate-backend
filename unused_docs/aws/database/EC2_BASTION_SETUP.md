# 🚀 EC2 Bastion Host Setup for Private RDS Access

## 🎯 What We Need To Do

Since your RDS is private, we need to create an EC2 instance **inside the same VPC** as your RDS database.

## 📋 Step-by-Step Setup

### 1️⃣ Find Your VPC Details (Manual Method)

Go to AWS Console:

**RDS Console:**
1. Go to RDS → Databases
2. Click on `accunode-postgres`  
3. Note down:
   - **VPC ID** (under Connectivity & security)
   - **Subnet group** (under Connectivity & security)

**EC2 Console:**
1. Go to EC2 → Subnets
2. Filter by your VPC ID
3. Find a **private subnet** (one where your RDS can be reached)

### 2️⃣ Automated Setup (If AWS CLI Works)

Run this to find your configuration automatically:
```bash
./scripts/find-vpc-config.sh
```

Then run the generated script:
```bash
./scripts/setup-vpc-bastion-configured.sh
```

### 3️⃣ Manual Setup (If Needed)

If automation doesn't work, manually update these values in `scripts/setup-vpc-bastion.sh`:

```bash
VPC_ID="vpc-your-actual-vpc-id"           # From RDS console
PRIVATE_SUBNET_ID="subnet-your-subnet-id" # Private subnet in same VPC
PUBLIC_SUBNET_ID="subnet-your-subnet-id"  # Public subnet (optional)
```

Then run:
```bash
./scripts/setup-vpc-bastion.sh
```

### 4️⃣ Connect and Create Super Admin

After the bastion is created:

```bash
# Connect to bastion via Session Manager (no SSH keys needed!)
aws ssm start-session --target i-xxxxxxxxxxxx

# Once connected, create super admin
python3 create_super_admin.py

# Or connect to database directly  
./connect-rds.sh
```

## 🔐 Expected Super Admin Credentials

- **Email:** admin@accunode.ai
- **Username:** accunode
- **Password:** SuperaAdmin123*
- **Role:** super_admin

## 💰 Cost

- **EC2 t3.micro:** ~$8.50/month if left running
- **Session Manager:** FREE
- **Data Transfer:** Minimal

**Cost Optimization:** Terminate the instance after creating the super admin, then launch it again only when needed.

## 🎯 Why This Approach?

✅ **Secure:** No public database access  
✅ **Free Session Manager:** No SSH keys or VPN needed  
✅ **AWS Native:** Uses AWS best practices  
✅ **Temporary:** Can be destroyed after setup

## 🚨 Alternative: Temporarily Make RDS Public

If the EC2 approach seems complex:

1. **RDS Console** → Modify `accunode-postgres`
2. **Set "Public accessibility" to "Yes"**  
3. **Update Security Group** to allow your IP
4. **Run the super admin script locally**
5. **Make RDS private again**

**Security Risk:** Database exposed to internet temporarily!

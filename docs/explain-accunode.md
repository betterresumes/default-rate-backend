# AccuNode: Complete System Architecture & User Roles

## 🎯 What AccuNode Does

AccuNode is a multi-tenant financial risk prediction platform that provides ML-based default probability analysis for companies. Each customer company gets their own isolated environment (tenant) to perform financial risk assessments.

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ACCUNODE PLATFORM                        │
│                  (Our SaaS Service)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │ SUPER ADMIN   │ ← AccuNode Team (Platform Owners)
                    │ (Our Team)    │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐  ┌────────▼────────┐  ┌──────▼──────┐
│ TENANT 1      │  │ TENANT 2        │  │ TENANT 3    │
│ (HDFC Bank)   │  │ (Goldman Sachs) │  │ (JP Morgan) │
└───────┬───────┘  └────────┬────────┘  └──────┬──────┘
        │                   │                   │
    ┌───▼───┐          ┌────▼────┐          ┌───▼───┐
    │ORG 1  │          │ ORG 1   │          │ ORG 1 │
    │ORG 2  │          │ ORG 2   │          │ ORG 2 │
    │ORG 3  │          │ ORG 3   │          │ ORG 3 │
    └───────┘          └─────────┘          └───────┘
```

### Key Concepts:

**🔐 Complete Tenant Isolation:** HDFC Bank ↔️ Goldman Sachs (No data sharing ever)

**🏢 Tenant = One Customer Company:** 1 Company = 1 Tenant

**🎯 Analysis Happens in Organizations:** Departments within each company

## 📋 Complete Business Flow Process

### 🚀 How New Customers Get Onboarded

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 1. INITIAL  │    │ 2. INTRO    │    │ 3. SALES &  │    │ 4. TECHNICAL│    │ 5. HANDOVER │    │ 6. ORG SETUP│
│ CONTACT     │───▶│ CALL        │───▶│ FINAL CALL  │───▶│ SETUP       │───▶│ CREDENTIALS │───▶│ & ANALYSIS  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────-┐
│• Customer   │    │• Product    │    │• Business   │    │• Super Admin│    │• Login      │    │• Tenant Admin│
│  emails us  │    │  demo       │    │  discussion │    │  creates    │    │  credentials│    │  creates orgs│
│• Contact    │    │• Technical  │    │• Pricing    │    │  tenant     │    │  shared     │    │• Adds users  │
│  via website│    │  overview   │    │• Agreement  │    │• Database   │    │• Account    │    │• ML analysis │
│• Sales      │    │• Use cases  │    │• Contract   │    │  setup      │    │  setup      │    │  begins      │
│  inquiry    │    │• Q&A        │    │  signed     │    │• Orgs setup │    │  guidance   │    │  in orgs     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────-┘

Simple Flow:
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Customer Contact → Demo Call → Sales Agreement → AccuNode Setup → Customer Access → Organization Operations |
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Step-by-Step Process:

**1. Initial Contact** 📧
- Customer (e.g., HDFC Bank) emails us or contacts via website
- Sales inquiry submitted through contact form
- AccuNode Sales team receives notification
- Initial response sent within 24 hours

**2. Intro Call Setup** 📞
- AccuNode Sales schedules intro call with customer
- Product demonstration and technical overview
- Customer explains their use cases and requirements
- Q&A session about features and capabilities

**3. Sales & Final Call** �
- Business discussion about pricing and agreement
- Contract terms and service details finalized
- Customer signs service agreement
- Payment and onboarding process initiated

**4. Technical Setup** ⚙️
- **AccuNode Super Admin handles complete setup:**
  - Runs: `python3 scripts/setup_tenant.py`
  - Creates tenant for customer (e.g., HDFC Bank)
  - Sets up database schema and isolation
  - Creates initial organizations structure

**5. Handover Credentials** 🔑
- **Super Admin provides login credentials directly:**
  - Tenant Admin account details
  - Organization Admin accounts (if pre-created)
  - Login URL and setup instructions
  - Basic usage guidance document

**6. Organization Setup & Analysis** 📊
- **Tenant Admin takes over and:**
  - Creates additional organizations as needed
  - Adds users to appropriate organizations
  - Assigns Organization Admins
  - **All ML analysis happens within individual orgs**
  - Teams start generating predictions and risk assessments

#### Key Roles in Process:
- **Customer**: Initiates contact, provides requirements, uses system
- **AccuNode Super Admin**: Does ALL technical setup and provides access
- **Tenant Admin**: Customer's main contact, manages organizations
- **Organization Teams**: Perform daily ML predictions and analysis

## 👥 User Role Hierarchy & Permissions

```
                    ┌─────────────────┐
                    │   SUPER ADMIN   │ ← AccuNode Platform Team
                    │  (Our Platform) │
                    └────────┬────────┘
                             │ Creates & Manages
                             ▼
                    ┌─────────────────┐
                    │  TENANT ADMIN   │ ← HDFC Bank Executive
                    │ (Company Mgmt)  │
                    └────────┬────────┘
                             │ Creates & Manages
                             ▼
                    ┌─────────────────┐
                    │  ORG ADMIN      │ ← Department Head
                    │ (Dept Manager)  │
                    └────────┬────────┘
                             │ Manages Team
                             ▼
          ┌─────────────────┬─────────────────┐
          │   ORG MEMBER    │   ORG MEMBER    │ ← Analysts
          │   (Analyst)     │   (Analyst)     │
          └─────────────────┴─────────────────┘
```

### 🔐 Role Permissions Matrix

| Permission | Super Admin | Tenant Admin | Org Admin | Org Member | User |
|------------|-------------|--------------|-----------|------------|------|
| Create Tenants | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage All Tenants | ✅ | ❌ | ❌ | ❌ | ❌ |
| Create Organizations | ✅ | ✅ | ❌ | ❌ | ❌ |
| Cross-Org Analysis | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage Org Members | ✅ | ✅ | ✅ | ❌ | ❌ |
| ML Predictions | ✅ | ✅* | ✅ | ✅ | ✅ |
| View Org Data | ✅ | ✅* | ✅ | ✅ | ❌ |

*Tenant Admin can access ANY organization within their tenant

### 🎯 Detailed Role Definitions

#### 1. **Super Admin** (Platform Owner)
- **Who:** AccuNode development/support team
- **Purpose:** Platform management and customer onboarding
- **Key Actions:**
  - Run `python3 scripts/setup_tenant.py` for new customers
  - Create tenant infrastructure
  - Emergency system access
  - Cross-tenant system maintenance

#### 2. **Tenant Admin** (Customer Company Executive)
- **Who:** Senior executive at customer company (e.g., CTO at HDFC Bank)
- **Purpose:** Company-wide tenant management (NOT daily analysis)
- **Key Actions:**
  - Create organizations within their tenant
  - Assign organization administrators
  - Access any organization's data within their company
  - Manage company-wide settings
- **Important:** This is a management role, not an analyst role

#### 3. **Organization Admin** (Department Manager)
- **Who:** Department head or team lead
- **Purpose:** Manage specific business unit/department
- **Key Actions:**
  - Add/remove organization members
  - Manage department's ML analysis projects
  - Oversee team's prediction workflows
  - Department-level reporting

#### 4. **Organization Member** (Analyst)
- **Who:** Day-to-day analysts and researchers
- **Purpose:** Perform actual ML predictions and analysis
- **Key Actions:**
  - Create company profiles
  - Generate annual/quarterly default predictions
  - Analyze financial ratios
  - Build prediction datasets

#### 5. **User** (Account Only)
- **Who:** Someone with basic account but no organizational access
- **Purpose:** Placeholder until assigned to organization

## 💼 Real-World Implementation Example

### 🏦 HDFC Bank Case Study

```
Step 1: Initial Setup
┌─────────────────────────────────────────┐
│ AccuNode Super Admin                    │
│ Runs: python3 scripts/setup_tenant.py  │
│ Creates: HDFC Bank Tenant               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ HDFC Bank Tenant Admin Account          │
│ Email: admin@hdfcbank.com               │
│ Password: [Generated]                   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
Step 2: Internal Organization Setup
┌─────────────────────────────────────────┐
│ Tenant Admin Creates Organizations:     │
│ • Investment Banking                    │
│ • Risk Management                      │
│ • Corporate Banking                    │
│ • Retail Banking                       │
└─────────────────┬───────────────────────┘
                  │
                  ▼
Step 3: Department-Level Management
┌─────────────────┬───────────────────┬────────────────---------┐
│ Investment Banking  │ Risk Management    │ Corporate Banking  │
│ Org Admin: John     │ Org Admin: Sarah   │ Org Admin: Mike    │
│ Members: 5 analysts │ Members: 3 analysts│ Members: 7 analysts│
└─────────────────┴───────────────────┴─────────────────--------┘
```

### 🔄 Daily Workflow

```
Morning: Analyst Work
┌─────────────────────────────────────────┐
│ Investment Banking Analyst              │
│ • Adds new company: Reliance Industries │
│ • Inputs financial ratios               │
│ • Generates annual prediction: 3.5%     │
│ • Risk Level: MEDIUM                    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
Afternoon: Manager Review
┌─────────────────────────────────────────┐
│ Investment Banking Org Admin            │
│ • Reviews all team predictions          │
│ • Validates Reliance analysis           │
│ • Approves for client presentation      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
Evening: Executive Overview
┌─────────────────────────────────────────┐
│ HDFC Tenant Admin (CTO)                 │
│ • Views predictions across all depts    │
│ • Sees Investment Banking: 25 companies │
│ • Sees Risk Management: 15 companies    │
│ • Makes strategic decisions             │
└─────────────────────────────────────────┘
```

## 🔒 Data Access & Security Model

### 🏢 Tenant Isolation

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   HDFC BANK      │  │  GOLDMAN SACHS   │  │   JP MORGAN      │
│     TENANT       │  │     TENANT       │  │     TENANT       │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ • Database Schema│  │ • Database Schema│  │ • Database Schema│
│ • User Accounts  │  │ • User Accounts  │  │ • User Accounts  │
│ • ML Predictions │  │ • ML Predictions │  │ • ML Predictions │
│ • Company Data   │  │ • Company Data   │  │ • Company Data   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        🔒                     🔒                     🔒
   NO CROSS-ACCESS         NO CROSS-ACCESS         NO CROSS-ACCESS
```

### 🎯 Organization-Level Access Control

Within HDFC Bank Tenant:
```
┌─────────────────────────────────────────────────────────────┐
│                     HDFC BANK TENANT                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Investment      │ Risk            │ Corporate               │
│ Banking Org     │ Management Org  │ Banking Org             │
├─────────────────┼─────────────────┼─────────────────────────┤
│ • Tech Companies│ • Market Risk   │ • SME Companies         │
│ • IPO Analysis  │ • Credit Risk   │ • Commercial Loans      │
│ • Private Equity│ • Portfolio Risk│ • Trade Finance         │
└─────────────────┴─────────────────┴─────────────────────────┘
        │                 │                     │
    ┌───▼───-┐         ┌───▼──-─┐             ┌───▼───-┐
    │ 5 Users│         │ 3 Users│             │ 7 Users│
    └───────-┘         └───────-┘             └───────-┘
```

**Access Rules:**
- Investment Banking users ❌ CANNOT see Risk Management data
- Risk Management users ❌ CANNOT see Corporate Banking data  
- Tenant Admin ✅ CAN access ALL organization data
- Organization Admin ✅ CAN access only their organization
- Organization Member ✅ CAN access only their organization

## 🛠️ Technical Implementation Details

### 🚀 Tenant Setup Script Usage

```bash
# Command run by Super Admin
python3 scripts/setup_tenant.py

# Script creates:
# 1. New database schema for tenant
# 2. Tenant admin user account
```

This system ensures complete isolation between customer companies while allowing flexible internal organization management for each tenant.

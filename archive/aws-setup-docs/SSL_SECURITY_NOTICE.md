# SSL Certificates - Security Notice

## 🔒 SSL Certificates Location

SSL certificates have been moved to a secure location outside the git repository for security reasons.

### Current Location:
```
~/secure-certificates/accunode/
├── cert.pem
└── private-key.pem
```

## ⚠️ Security Guidelines

### DO NOT:
- ❌ Commit SSL certificates to git
- ❌ Include private keys in any repository
- ❌ Share certificates via email or chat
- ❌ Store certificates in code directories

### DO:
- ✅ Store certificates in secure, non-git directories
- ✅ Use environment variables for certificate paths
- ✅ Rotate certificates regularly
- ✅ Use AWS Certificate Manager for production

## 🚀 Production Recommendation

For production deployments, consider using:
1. **AWS Certificate Manager (ACM)** - Managed SSL certificates
2. **Let's Encrypt** - Free automated certificates
3. **AWS Secrets Manager** - Secure certificate storage

## 🔧 Usage in Deployment

When referencing certificates in deployment scripts:
```bash
# Use environment variable or absolute path
CERT_PATH="~/secure-certificates/accunode/cert.pem"
KEY_PATH="~/secure-certificates/accunode/private-key.pem"
```

## 📝 Note

These certificates are now excluded from git via `.gitignore` patterns:
- `*.pem`
- `*.crt`  
- `*.key`
- `ssl/`
- `certificates/`

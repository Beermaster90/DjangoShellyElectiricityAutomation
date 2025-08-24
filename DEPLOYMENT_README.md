# Django Deployment Scripts Documentation

This directory contains several deployment scripts for the Shelly Django application with different use cases.

## Scripts Overview

### 1. `Update_shelly_on_server.sh` 
**Purpose**: Server deployment script for production Linux environments
- **Target**: Remote Linux servers
- **Port**: 35789
- **Security**: Production-ready with configurable HTTPS
- **Database**: Docker volume for persistence
- **Tar Path**: Fixed location `/home/megaman/shelly_django.tar`

### 1b. `Update_shelly_on_server_auto.sh`
**Purpose**: Server deployment with automatic tar file detection
- **Target**: Remote Linux servers  
- **Port**: 35789
- **Security**: Production-ready with configurable HTTPS
- **Database**: Docker volume for persistence
- **Tar Path**: Auto-detects from multiple common locations

### 2. `deploy_local.sh`
**Purpose**: Local testing deployment for Unix/Linux/macOS
- **Target**: Local development/testing
- **Port**: 8000  
- **Security**: HTTP mode with security features
- **Database**: Local directory mount

### 3. `deploy_local.ps1`
**Purpose**: Local testing deployment for Windows PowerShell
- **Target**: Local Windows development
- **Port**: 8000
- **Security**: Configurable via parameters
- **Database**: Local directory mount

## Quick Start Guide

### 1. Build Docker Image
```bash
# Windows
.\create_docker_image.cmd

# Linux/macOS
chmod +x create_docker_image.cmd && ./create_docker_image.cmd
```

### 2. Generate Secure Secret Key
```bash
python generate_secret_key.py
```

### 3. Local Deployment

#### Windows PowerShell:
```powershell
# Basic deployment
.\deploy_local.ps1

# With custom secret key
.\deploy_local.ps1 -SecretKey "your-50-character-secure-key-here"

# HTTPS mode
.\deploy_local.ps1 -UseHttps True -SecretKey "your-key"
```

#### Linux/macOS:
```bash
chmod +x deploy_local.sh
./deploy_local.sh
```

### 4. Server Deployment

#### Option A: Standard Script (Fixed Path)
```bash
# 1. Upload tar file to specific location
scp shelly_django.tar user@server:/home/megaman/

# 2. Edit script configuration
# Update DJANGO_SECRET_KEY, ALLOWED_HOSTS in Update_shelly_on_server.sh

# 3. Deploy
chmod +x Update_shelly_on_server.sh
./Update_shelly_on_server.sh
```

#### Option B: Auto-Find Script (Flexible)
```bash
# 1. Upload tar file to any common location:
# - /home/megaman/shelly_django.tar
# - /home/$USER/shelly_django.tar  
# - ./shelly_django.tar
# - /tmp/shelly_django.tar

# 2. Deploy with auto-detection
chmod +x Update_shelly_on_server_auto.sh
./Update_shelly_on_server_auto.sh
```

## Configuration Options

### Environment Variables Used
- `DEBUG`: Enable/disable debug mode (True/False)
- `DJANGO_SECRET_KEY`: 50-character cryptographically secure key
- `USE_HTTPS`: Enable HTTPS security features (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames
- `SECURE_HSTS_SECONDS`: HSTS max-age value for HTTPS
- `DJANGO_SQLITE_PATH`: Database file path

### HTTP vs HTTPS Mode

#### HTTP Mode (Default)
- ✅ Basic security headers
- ✅ Secure session cookies (HttpOnly)
- ⚠️ Some security warnings (expected)
- 🔧 Good for local testing

#### HTTPS Mode (Production)
- ✅ Full security headers
- ✅ SSL redirect
- ✅ HSTS (HTTP Strict Transport Security)
- ✅ Secure cookies
- ✅ Zero security warnings
- 🔒 Required for production

## Security Checklist

### Before Deployment:
- [ ] Generate secure secret key (`python generate_secret_key.py`)
- [ ] Update `DJANGO_SECRET_KEY` in deployment script
- [ ] Configure proper `ALLOWED_HOSTS` for your domain
- [ ] Set `DEBUG=False` for production
- [ ] Enable `USE_HTTPS=True` for production with SSL certificates
- [ ] Test security with: `docker exec container python manage.py check --deploy`

### Production Security Features:
- ✅ Non-root container execution
- ✅ Minimal Docker image (python:slim)
- ✅ Security headers (XSS, CSRF protection)
- ✅ HTTPS enforcement (when enabled)
- ✅ Secure session handling
- ✅ Database volume separation

## Troubleshooting

### Common Issues:

1. **Container won't start**
   ```bash
   docker logs container_name
   ```

2. **Security warnings**
   ```bash
   docker exec container python manage.py check --deploy
   ```

3. **Database issues**
   ```bash
   docker exec container python manage.py showmigrations
   docker exec container python manage.py migrate
   ```

4. **Tar file not found**
   ```bash
   # Check if file exists
   ls -la /home/megaman/shelly_django.tar
   
   # Use auto-detection script
   ./Update_shelly_on_server_auto.sh
   
   # Or upload to correct location
   scp shelly_django.tar user@server:/home/megaman/
   ```

5. **Permission issues**
   ```bash
   # Linux/macOS
   sudo chown -R $USER:$USER ./data
   chmod +x Update_shelly_on_server.sh
   
   # Windows (Run as Administrator)
   icacls .\data /grant Everyone:F /T
   ```

### Log Locations:
- **Container logs**: `docker logs shelly_django_container`
- **Django logs**: Inside container at `/app/logs/`
- **Database**: Volume mount at `./data/db.sqlite3`

## Port Mappings

| Script | Host Port | Container Port | Purpose |
|--------|-----------|----------------|---------|
| `Update_shelly_on_server.sh` | 35789 | 8000 | Production server |
| `deploy_local.sh` | 8000 | 8000 | Local testing |
| `deploy_local.ps1` | 8000 | 8000 | Windows local testing |

## File Structure After Deployment

```
project_root/
├── data/                          # Database storage
│   └── db.sqlite3                # SQLite database
├── deploy_local.sh               # Local Unix deployment
├── deploy_local.ps1              # Local Windows deployment  
├── Update_shelly_on_server.sh    # Server deployment
├── shelly_django.tar             # Docker image (after build)
├── docker-compose.yml            # Development compose
├── docker-compose.prod.yml       # Production compose
└── generate_secret_key.py        # Security key generator
```

## Best Practices

1. **Never commit secret keys** to version control
2. **Use HTTPS in production** with proper SSL certificates
3. **Regularly update dependencies** and rebuild images
4. **Monitor container resources** and logs
5. **Backup database** regularly (`./data/db.sqlite3`)
6. **Test deployments** in staging before production
7. **Use proper domain names** in `ALLOWED_HOSTS`

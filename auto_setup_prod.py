#!/usr/bin/env python3
# auto_setup_prod.py
"""
Complete Whatspy Production Setup Script for Ubuntu Server
- System dependencies installation
- Python environment setup
- Database setup and migration
- Creates admin user
- Production service configuration
- SSL/TLS setup (optional)
- Firewall configuration
- Service management setup

Run with: sudo python3 auto_setup_prod.py
"""
import os
import sys
import subprocess
import shutil
import pwd
import grp
from pathlib import Path
import json
import socket

# Colors for output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}🚀 {text}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.END}\n")

def print_step(step, text):
    print(f"{Colors.BLUE}{Colors.BOLD}{step} {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}   ✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}   ❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}   ⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.WHITE}   ℹ️  {text}{Colors.END}")

def run_command(cmd, check=True, capture_output=False):
    """Run shell command with error handling"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, check=check, 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=check)
            return True
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {cmd}")
        print_error(f"Error: {e}")
        return False

def check_root():
    """Check if running as root"""
    if os.geteuid() != 0:
        print_error("This script must be run as root (use sudo)")
        sys.exit(1)

def get_system_info():
    """Get system information"""
    try:
        # Get Ubuntu version
        version = run_command("lsb_release -rs", capture_output=True)
        codename = run_command("lsb_release -cs", capture_output=True)
        
        # Get system resources
        memory = run_command("free -h | grep '^Mem:' | awk '{print $2}'", capture_output=True)
        cpu_cores = run_command("nproc", capture_output=True)
        disk_space = run_command("df -h / | tail -1 | awk '{print $4}'", capture_output=True)
        
        return {
            'version': version,
            'codename': codename,
            'memory': memory,
            'cpu_cores': cpu_cores,
            'disk_space': disk_space
        }
    except:
        return None

def install_system_dependencies():
    """Install required system packages"""
    print_step("1️⃣", "Installing system dependencies...")
    
    packages = [
        'python3',
        'python3-pip',
        'python3-venv',
        'python3-dev',
        'postgresql',
        'postgresql-contrib',
        'postgresql-server-dev-all',
        'nginx',
        'supervisor',
        'ufw',
        'curl',
        'wget',
        'git',
        'build-essential',
        'libssl-dev',
        'libffi-dev',
        'redis-server',
        'certbot',
        'python3-certbot-nginx'
    ]
    
    # Update package list
    print_info("Updating package list...")
    if not run_command("apt update"):
        return False
    
    # Install packages
    print_info("Installing packages...")
    package_list = ' '.join(packages)
    if not run_command(f"apt install -y {package_list}"):
        return False
    
    print_success("System dependencies installed")
    return True

def setup_postgresql():
    """Setup PostgreSQL database"""
    print_step("2️⃣", "Setting up PostgreSQL...")
    
    # Start PostgreSQL service
    run_command("systemctl start postgresql")
    run_command("systemctl enable postgresql")
    
    # Create database and user
    db_name = "whatspy_prod"
    db_user = "whatspy_user"
    db_password = "whatspy_secure_password_2024"
    
    # Create database user and database
    commands = [
        f"sudo -u postgres createuser --createdb {db_user}",
        f"sudo -u postgres createdb {db_name} --owner={db_user}",
        f"sudo -u postgres psql -c \"ALTER USER {db_user} PASSWORD '{db_password}';\"",
        f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};\""
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            print_warning(f"Command may have failed (might be expected): {cmd}")
    
    print_success("PostgreSQL setup completed")
    return db_name, db_user, db_password

def create_app_user():
    """Create application user"""
    print_step("3️⃣", "Creating application user...")
    
    app_user = "whatspy"
    app_home = "/opt/whatspy"
    
    # Create user if doesn't exist
    try:
        pwd.getpwnam(app_user)
        print_info(f"User {app_user} already exists")
    except KeyError:
        run_command(f"useradd -r -s /bin/bash -d {app_home} {app_user}")
        print_success(f"Created user {app_user}")
    
    # Create home directory
    os.makedirs(app_home, exist_ok=True)
    run_command(f"chown -R {app_user}:{app_user} {app_home}")
    
    return app_user, app_home

def setup_application(app_user, app_home, db_name, db_user, db_password):
    """Setup application files and environment"""
    print_step("4️⃣", "Setting up application...")
    
    current_dir = os.getcwd()
    app_dir = f"{app_home}/app"
    
    # Copy application files
    print_info("Copying application files...")
    if os.path.exists(app_dir):
        run_command(f"rm -rf {app_dir}")
    
    run_command(f"cp -r {current_dir} {app_dir}")
    run_command(f"chown -R {app_user}:{app_user} {app_dir}")
    
    # Create virtual environment
    print_info("Creating Python virtual environment...")
    venv_path = f"{app_home}/venv"
    run_command(f"sudo -u {app_user} python3 -m venv {venv_path}")
    
    # Install Python dependencies
    print_info("Installing Python dependencies...")
    pip_cmd = f"{venv_path}/bin/pip"
    run_command(f"sudo -u {app_user} {pip_cmd} install --upgrade pip")
    run_command(f"sudo -u {app_user} {pip_cmd} install -r {app_dir}/requirements_prod.txt")
    
    # Create production .env file
    print_info("Creating production environment file...")
    env_content = f"""# Production Environment Configuration
DATABASE_URL=postgresql://{db_user}:{db_password}@localhost/{db_name}
SECRET_KEY=your-super-secret-key-change-this-in-production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
JWT_SECRET_KEY=your-jwt-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# WhatsApp Configuration
WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your-webhook-verify-token

# Production Settings
ENVIRONMENT=production
DEBUG=False
HOST=0.0.0.0
PORT=8000

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/whatspy/app.log
"""
    
    env_file = f"{app_dir}/.env"
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    run_command(f"chown {app_user}:{app_user} {env_file}")
    run_command(f"chmod 600 {env_file}")
    
    print_success("Application setup completed")
    return app_dir, venv_path

def setup_database_schema(app_user, app_dir, venv_path):
    """Setup database schema and create admin user"""
    print_step("5️⃣", "Setting up database schema...")
    
    # Add current directory to Python path and run setup
    python_cmd = f"{venv_path}/bin/python"
    
    # Change to app directory and run database setup
    setup_script = f"""
import sys
sys.path.insert(0, '{app_dir}')
os.chdir('{app_dir}')

from app.db.session import get_db_session, test_db_connection, engine
from app.db.base import Base
from app.core.security import create_admin_user, hash_password
from app.core.config import ADMIN_USERNAME, ADMIN_PASSWORD
from app.models.user import AdminUser

# Test database connection
if not test_db_connection():
    print("Database connection failed!")
    sys.exit(1)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create admin user
with get_db_session() as db:
    existing = db.query(AdminUser).filter(AdminUser.username == ADMIN_USERNAME).first()
    if not existing:
        user = create_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, db)
        if user:
            print(f"Admin user '{ADMIN_USERNAME}' created successfully")
        else:
            print("Failed to create admin user")
            sys.exit(1)
    else:
        print(f"Admin user '{ADMIN_USERNAME}' already exists")

print("Database setup completed successfully")
"""
    
    # Write and execute setup script
    setup_file = f"{app_dir}/temp_setup.py"
    with open(setup_file, 'w') as f:
        f.write(f"import os\n{setup_script}")
    
    run_command(f"sudo -u {app_user} {python_cmd} {setup_file}")
    os.remove(setup_file)
    
    print_success("Database schema setup completed")

def create_systemd_service(app_user, app_dir, venv_path):
    """Create systemd service for the application"""
    print_step("6️⃣", "Creating systemd service...")
    
    service_content = f"""[Unit]
Description=Whatspy WhatsApp Management System
After=network.target postgresql.service redis.service
Requires=postgresql.service

[Service]
Type=exec
User={app_user}
Group={app_user}
WorkingDirectory={app_dir}
Environment=PATH={venv_path}/bin
ExecStart={venv_path}/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths={app_dir} /var/log/whatspy

[Install]
WantedBy=multi-user.target
"""
    
    service_file = "/etc/systemd/system/whatspy.service"
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    # Create log directory
    os.makedirs("/var/log/whatspy", exist_ok=True)
    run_command(f"chown {app_user}:{app_user} /var/log/whatspy")
    
    # Reload systemd and enable service
    run_command("systemctl daemon-reload")
    run_command("systemctl enable whatspy")
    
    print_success("Systemd service created")

def setup_nginx(domain=None):
    """Setup Nginx reverse proxy"""
    print_step("7️⃣", "Setting up Nginx...")
    
    server_name = domain if domain else "localhost"
    
    nginx_config = f"""server {{
    listen 80;
    server_name {server_name};
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    location / {{
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
    
    # Static files (if any)
    location /static/ {{
        alias /opt/whatspy/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
    
    # Health check endpoint
    location /healthz {{
        proxy_pass http://127.0.0.1:8000/healthz;
        access_log off;
    }}
}}
"""
    
    config_file = f"/etc/nginx/sites-available/whatspy"
    with open(config_file, 'w') as f:
        f.write(nginx_config)
    
    # Enable site
    symlink = "/etc/nginx/sites-enabled/whatspy"
    if os.path.exists(symlink):
        os.remove(symlink)
    os.symlink(config_file, symlink)
    
    # Remove default site
    default_enabled = "/etc/nginx/sites-enabled/default"
    if os.path.exists(default_enabled):
        os.remove(default_enabled)
    
    # Test and reload nginx
    if run_command("nginx -t"):
        run_command("systemctl reload nginx")
        run_command("systemctl enable nginx")
        print_success("Nginx configured successfully")
    else:
        print_error("Nginx configuration test failed")
        return False
    
    return True

def setup_firewall():
    """Setup UFW firewall"""
    print_step("8️⃣", "Setting up firewall...")
    
    # Reset UFW
    run_command("ufw --force reset")
    
    # Default policies
    run_command("ufw default deny incoming")
    run_command("ufw default allow outgoing")
    
    # Allow SSH (be careful!)
    run_command("ufw allow ssh")
    
    # Allow HTTP and HTTPS
    run_command("ufw allow 'Nginx Full'")
    
    # Allow PostgreSQL locally only
    run_command("ufw allow from 127.0.0.1 to any port 5432")
    
    # Allow Redis locally only
    run_command("ufw allow from 127.0.0.1 to any port 6379")
    
    # Enable firewall
    run_command("ufw --force enable")
    
    print_success("Firewall configured")

def setup_ssl_certificate(domain):
    """Setup SSL certificate with Let's Encrypt"""
    if not domain or domain == "localhost":
        print_warning("Skipping SSL setup (no domain provided)")
        return
    
    print_step("9️⃣", "Setting up SSL certificate...")
    
    # Get SSL certificate
    cmd = f"certbot --nginx -d {domain} --non-interactive --agree-tos --email admin@{domain}"
    if run_command(cmd):
        print_success("SSL certificate installed")
        
        # Setup auto-renewal
        run_command("systemctl enable certbot.timer")
        print_success("SSL auto-renewal enabled")
    else:
        print_warning("SSL certificate setup failed")

def start_services():
    """Start all services"""
    print_step("🔟", "Starting services...")
    
    services = [
        "postgresql",
        "redis-server", 
        "nginx",
        "whatspy"
    ]
    
    for service in services:
        if run_command(f"systemctl start {service}"):
            print_success(f"Started {service}")
        else:
            print_error(f"Failed to start {service}")

def print_final_info(domain=None):
    """Print final setup information"""
    print_header("SETUP COMPLETED SUCCESSFULLY!")
    
    server_url = f"https://{domain}" if domain and domain != "localhost" else "http://localhost"
    
    print(f"{Colors.GREEN}📌 Admin Login Credentials:{Colors.END}")
    print(f"   Username: admin")
    print(f"   Password: admin123")
    print(f"   {Colors.RED}🔒 IMPORTANT: Change password after first login!{Colors.END}")
    
    print(f"\n{Colors.BLUE}🌐 Access Points:{Colors.END}")
    print(f"   Login:         {server_url}/login")
    print(f"   Chat UI:       {server_url}/chat")
    print(f"   Dashboard:     {server_url}/dashboard")
    print(f"   API Docs:      {server_url}/docs")
    print(f"   Health Check:  {server_url}/healthz")
    
    print(f"\n{Colors.YELLOW}🔧 Service Management:{Colors.END}")
    print(f"   Start:    sudo systemctl start whatspy")
    print(f"   Stop:     sudo systemctl stop whatspy")
    print(f"   Restart:  sudo systemctl restart whatspy")
    print(f"   Status:   sudo systemctl status whatspy")
    print(f"   Logs:     sudo journalctl -u whatspy -f")
    
    print(f"\n{Colors.MAGENTA}📁 Important Paths:{Colors.END}")
    print(f"   App Directory:    /opt/whatspy/app")
    print(f"   Config File:      /opt/whatspy/app/.env")
    print(f"   Log Files:        /var/log/whatspy/")
    print(f"   Service File:     /etc/systemd/system/whatspy.service")
    print(f"   Nginx Config:     /etc/nginx/sites-available/whatspy")
    
    print(f"\n{Colors.CYAN}⚠️  Next Steps:{Colors.END}")
    print(f"   1. Update WhatsApp API credentials in /opt/whatspy/app/.env")
    print(f"   2. Change admin password after first login")
    print(f"   3. Configure domain name if needed")
    print(f"   4. Set up monitoring and backups")
    print(f"   5. Review firewall rules")

def main():
    """Main setup function"""
    print_header("WHATSPY PRODUCTION SETUP FOR UBUNTU")
    
    # Check if running as root
    check_root()
    
    # Get system info
    sys_info = get_system_info()
    if sys_info:
        print_info(f"Ubuntu {sys_info['version']} ({sys_info['codename']})")
        print_info(f"Memory: {sys_info['memory']}, CPU Cores: {sys_info['cpu_cores']}, Disk: {sys_info['disk_space']}")
    
    # Ask for domain name
    domain = input(f"\n{Colors.YELLOW}Enter your domain name (or press Enter for localhost): {Colors.END}").strip()
    if not domain:
        domain = "localhost"
    
    try:
        # Step 1: Install system dependencies
        if not install_system_dependencies():
            sys.exit(1)
        
        # Step 2: Setup PostgreSQL
        db_name, db_user, db_password = setup_postgresql()
        
        # Step 3: Create application user
        app_user, app_home = create_app_user()
        
        # Step 4: Setup application
        app_dir, venv_path = setup_application(app_user, app_home, db_name, db_user, db_password)
        
        # Step 5: Setup database schema
        setup_database_schema(app_user, app_dir, venv_path)
        
        # Step 6: Create systemd service
        create_systemd_service(app_user, app_dir, venv_path)
        
        # Step 7: Setup Nginx
        setup_nginx(domain)
        
        # Step 8: Setup firewall
        setup_firewall()
        
        # Step 9: Setup SSL (if domain provided)
        if domain != "localhost":
            setup_ssl_certificate(domain)
        
        # Step 10: Start services
        start_services()
        
        # Print final information
        print_final_info(domain)
        
    except KeyboardInterrupt:
        print_error("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
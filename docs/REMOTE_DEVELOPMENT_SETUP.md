# Remote Development Setup - Edit Code Locally, Deploy to EC2

Yes, you can absolutely use your local IDE (VS Code, Cursor, etc.) to edit code and sync it to your AWS EC2 server. Here are the best methods:

---

## Method 1: VS Code / Cursor Remote SSH Extension (Recommended)

This is the **best method** - it lets you edit files directly on the server as if they were local.

### Setup Steps:

1. **Install Remote SSH Extension**
   - In VS Code/Cursor: Extensions → Search "Remote - SSH"
   - Install the extension

2. **Configure SSH Connection**
   - Press `F1` or `Ctrl+Shift+P`
   - Type: "Remote-SSH: Open SSH Configuration File"
   - Select: `C:\Users\tyung\.ssh\config` (Windows)
   - Add:
     ```
     Host hrsp-ec2
         HostName <YOUR_EC2_PUBLIC_IP>
         User ubuntu
         IdentityFile C:\Users\tyung\path\to\your-key.pem
         ForwardAgent yes
     ```

3. **Connect to Server**
   - Press `F1` → "Remote-SSH: Connect to Host"
   - Select "hrsp-ec2"
   - VS Code/Cursor will connect and open a new window
   - You can now browse and edit files directly on the server!

4. **Install Extensions on Remote**
   - Once connected, install Python, Node.js extensions on the remote server
   - Extensions work seamlessly on remote

### Advantages:
- ✅ Edit files directly on server
- ✅ Terminal access built-in
- ✅ All IDE features work (IntelliSense, debugging, etc.)
- ✅ No file syncing needed
- ✅ Can run commands directly on server

### Disadvantages:
- ⚠️ Requires stable internet connection
- ⚠️ Slightly slower than local editing

---

## Method 2: Git Workflow (Best for Production)

Use Git to push changes from local, then pull on server.

### Setup Steps:

1. **On Your Local Machine**
   ```bash
   # Make changes in your IDE
   git add .
   git commit -m "Your changes"
   git push origin cursor-v2
   ```

2. **On EC2 Server**
   ```bash
   cd /home/ubuntu/apps/AGENT
   git pull origin cursor-v2
   
   # Restart services if needed
   sudo systemctl restart hrsp-backend
   sudo systemctl restart hrsp-frontend
   ```

3. **Optional: Auto-Deploy Script**
   Create `/home/ubuntu/deploy.sh`:
   ```bash
   #!/bin/bash
   cd /home/ubuntu/apps/AGENT
   git pull origin cursor-v2
   
   # Backend
   cd backend
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart hrsp-backend
   
   # Frontend
   cd ..
   npm install
   npm run build
   sudo systemctl restart hrsp-frontend
   
   echo "Deployment complete!"
   ```
   
   Make executable:
   ```bash
   chmod +x /home/ubuntu/deploy.sh
   ```

### Advantages:
- ✅ Version control
- ✅ Easy rollback
- ✅ Works with CI/CD
- ✅ Professional workflow

### Disadvantages:
- ⚠️ Need to commit and push for each change
- ⚠️ Two-step process (edit → push → pull)

---

## Method 3: SFTP/Sync Extension (Quick Sync)

Use VS Code SFTP extension to sync files automatically.

### Setup Steps:

1. **Install SFTP Extension**
   - Extensions → Search "SFTP"
   - Install "SFTP" by Natizyskunk

2. **Create Config File**
   - In your project root, create `.vscode/sftp.json`:
   ```json
   {
       "name": "HRSP EC2",
       "host": "<YOUR_EC2_PUBLIC_IP>",
       "protocol": "sftp",
       "port": 22,
       "username": "ubuntu",
       "privateKeyPath": "C:\\Users\\tyung\\path\\to\\your-key.pem",
       "remotePath": "/home/ubuntu/apps/AGENT",
       "uploadOnSave": true,
       "useTempFile": false,
       "openSsh": false,
       "ignore": [
           "**/.vscode/**",
           "**/node_modules/**",
           "**/venv/**",
           "**/.git/**",
           "**/__pycache__/**",
           "**/.next/**"
       ]
   }
   ```

3. **Use It**
   - Right-click file/folder → "Upload"
   - Or enable "uploadOnSave" to auto-sync

### Advantages:
- ✅ Quick file sync
- ✅ Can auto-upload on save
- ✅ Works with any IDE

### Disadvantages:
- ⚠️ No terminal access
- ⚠️ Can overwrite files if not careful
- ⚠️ Doesn't handle dependencies well

---

## Method 4: rsync Script (Advanced)

Use rsync to sync files efficiently.

### Setup Steps:

1. **Create Sync Script** (`sync-to-ec2.bat` on Windows or `sync-to-ec2.sh` on Mac/Linux)
   
   **Windows (PowerShell):**
   ```powershell
   # sync-to-ec2.ps1
   $EC2_IP = "YOUR_EC2_PUBLIC_IP"
   $KEY_PATH = "C:\Users\tyung\path\to\your-key.pem"
   $LOCAL_PATH = "C:\Users\tyung\AGENT"
   $REMOTE_PATH = "/home/ubuntu/apps/AGENT"
   
   # Sync files (exclude node_modules, venv, etc.)
   rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '.next' --exclude '__pycache__' --exclude '.git' -e "ssh -i $KEY_PATH" $LOCAL_PATH ubuntu@${EC2_IP}:$REMOTE_PATH
   
   Write-Host "Sync complete!"
   ```
   
   **Mac/Linux:**
   ```bash
   #!/bin/bash
   EC2_IP="YOUR_EC2_PUBLIC_IP"
   KEY_PATH="$HOME/path/to/your-key.pem"
   LOCAL_PATH="$HOME/AGENT"
   REMOTE_PATH="/home/ubuntu/apps/AGENT"
   
   rsync -avz --exclude 'node_modules' --exclude 'venv' --exclude '.next' --exclude '__pycache__' --exclude '.git' -e "ssh -i $KEY_PATH" $LOCAL_PATH ubuntu@${EC2_IP}:$REMOTE_PATH
   
   echo "Sync complete!"
   ```

2. **Run Script**
   ```bash
   # After making changes locally
   ./sync-to-ec2.sh
   ```

### Advantages:
- ✅ Efficient (only syncs changed files)
- ✅ Fast
- ✅ Can exclude unnecessary files

### Disadvantages:
- ⚠️ Manual step required
- ⚠️ Need to install rsync on Windows (or use WSL)

---

## Method 5: Hybrid Approach (Recommended for Development)

**Best of both worlds:**

1. **Development:** Use Remote SSH (Method 1) for quick edits and testing
2. **Production:** Use Git (Method 2) for version control and deployments

### Workflow:

```
Local Development:
├── Edit code in VS Code/Cursor (Remote SSH)
├── Test on server directly
├── Commit changes to Git
└── Push to repository

Production Deployment:
├── Pull latest from Git on server
├── Install dependencies
├── Build frontend
└── Restart services
```

---

## Recommended Setup for Your Use Case

### For Active Development:
**Use Remote SSH (Method 1)**
- Edit files directly on server
- Test immediately
- No syncing needed

### For Stable Deployments:
**Use Git (Method 2)**
- Version control
- Easy rollback
- Professional workflow

---

## Quick Setup: Remote SSH in Cursor/VS Code

1. **Install Extension:**
   - Open Extensions (Ctrl+Shift+X)
   - Search: "Remote - SSH"
   - Install

2. **Connect:**
   - Press `Ctrl+Shift+P`
   - Type: "Remote-SSH: Connect to Host"
   - Enter: `ubuntu@<YOUR_EC2_IP>`
   - Select your `.pem` key file
   - Done! You're now editing on the server

3. **Open Project:**
   - File → Open Folder
   - Navigate to: `/home/ubuntu/apps/AGENT`
   - Start coding!

---

## Tips

1. **Keep .env files local**
   - Don't sync `.env` files
   - Configure separately on server

2. **Use .gitignore**
   - Exclude `node_modules`, `venv`, `.next`, etc.

3. **Test before deploying**
   - Use Remote SSH to test on server
   - Then commit and deploy

4. **Backup before major changes**
   ```bash
   # On server
   cp -r /home/ubuntu/apps/AGENT /home/ubuntu/apps/AGENT_backup
   ```

---

## Troubleshooting

### Remote SSH Connection Issues:
- Check security group allows SSH (port 22)
- Verify key file permissions: `chmod 400 your-key.pem`
- Check EC2 instance is running

### File Sync Issues:
- Check file permissions on server
- Verify SSH key is correct
- Check disk space: `df -h`

### Extension Issues:
- Install extensions on remote server (not just local)
- Reload window after connecting

---

**Bottom Line:** Yes, you can absolutely use your local IDE! Remote SSH is the easiest way to edit code on the server directly. 🚀


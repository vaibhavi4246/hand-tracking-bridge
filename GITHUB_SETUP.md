# GitHub Setup & Push Guide

Complete instructions for pushing this project to GitHub.

## Step 1: Initialize Git Repository (If Not Already Done)

```bash
cd C:\Users\ASUS\Downloads\Mediapipe
git init
```

## Step 2: Verify .gitignore

The `.gitignore` file is already created and configured to exclude:
- Python cache files
- Virtual environments
- IDE files
- Logs
- OS files

All good! ✓

## Step 3: Stage Files for Commit

```bash
# Add all files
git add .

# Verify what will be committed
git status
```

You should see files like:
- hand_tracker.py
- run.py
- config.py
- requirements.txt
- *.md files
- .gitignore

Files NOT committed (ignored):
- venv/
- __pycache__/
- .vscode/
- *.pyc

## Step 4: Make Initial Commit

```bash
git commit -m "Initial commit: Hand Tracking Bridge for TouchDesigner

- Real-time hand detection via MediaPipe
- OSC protocol output to TouchDesigner
- 30 FPS performance with EMA smoothing
- Complete documentation and examples
- Setup verification tools included"
```

## Step 5: Create GitHub Repository

### Option A: Via GitHub Website

1. Go to https://github.com/new
2. **Repository name:** `hand-tracking-bridge` or `mediapipe-touchdesigner`
3. **Description:** Real-time hand tracking bridge between MediaPipe and TouchDesigner via OSC
4. **Visibility:** Public (to share) or Private (for personal use)
5. **Initialize with:** DON'T initialize (we already have files)
6. Click **Create repository**

### Option B: Via GitHub CLI

```bash
# Install GitHub CLI first from https://cli.github.com/
# Then:
gh repo create hand-tracking-bridge --public --source=. --remote=origin --push
```

## Step 6: Connect Local Repository to GitHub

After creating the repo on GitHub, copy the repository URL, then:

```bash
# Add remote (replace with your actual repo URL)
git remote add origin https://github.com/YOUR_USERNAME/hand-tracking-bridge.git

# Verify remote is set
git remote -v
```

## Step 7: Push to GitHub

```bash
# Push main branch
git branch -M main
git push -u origin main
```

Done! Your code is now on GitHub! ✓

---

## Common Git Commands for Future Updates

### Update existing code

```bash
# Check what changed
git status

# Stage changes
git add .

# Commit
git commit -m "Your commit message"

# Push
git push
```

### Create a new branch (for features)

```bash
git checkout -b feature/hand-gesture-classification
# ... make changes ...
git add .
git commit -m "Add hand gesture classification"
git push -u origin feature/hand-gesture-classification
```

### View commit history

```bash
git log --oneline
```

---

## GitHub Repository Structure

Your repository will have this structure:

```
hand-tracking-bridge/
├── hand_tracker.py         # Main application
├── run.py                 # Launcher
├── config.py              # Configuration
├── setup_check.py         # Setup verification
├── test_diagnostics.py    # System tests
├── test_camera.py         # Camera test
├── requirements.txt       # Dependencies
├── .gitignore            # Git exclusions
│
├── README.md             # Project overview
├── QUICKSTART.md         # 5-minute guide
├── START_HERE.md         # Getting started
├── PLAN.md              # Complete project plan
├── PROJECT_OVERVIEW.md   # Architecture docs
├── TOUCHDESIGNER_EXAMPLES.md  # TD examples
│
└── GITHUB_SETUP.md      # This file
```

---

## Add GitHub Topics (Optional)

On GitHub, in repository settings, add topics:
- `mediapipe`
- `touchdesigner`
- `hand-tracking`
- `osc`
- `computer-vision`
- `gesture-recognition`

This helps others discover your project!

---

## Create a GitHub Release (Optional)

Once pushed, create a release:

```bash
git tag -a v1.0.0 -m "Initial release: Hand Tracking Bridge v1.0"
git push origin v1.0.0
```

Then on GitHub:
1. Go to Releases
2. Draft new release
3. Select tag: v1.0.0
4. Title: "Hand Tracking Bridge v1.0"
5. Description: Features, setup, usage
6. Publish!

---

## Share With Others

Once on GitHub, you can share:

**Repository URL:** 
```
https://github.com/YOUR_USERNAME/hand-tracking-bridge
```

**Clone command (for others):**
```bash
git clone https://github.com/YOUR_USERNAME/hand-tracking-bridge.git
cd hand-tracking-bridge
pip install -r requirements.txt
python run.py
```

---

## Next Steps After Push

1. **Add Issues** (bugs, features you want)
2. **Add Discussions** (for community questions)
3. **Create Wiki** (extended documentation)
4. **Set up Actions** (automatic testing)
5. **Request collaborators** if working with others

---

## Troubleshooting

### Error: "fatal: not a git repository"

```bash
cd C:\Users\ASUS\Downloads\Mediapipe
git init
```

### Error: "Git not installed"

Download from: https://git-scm.com/download/win

### Error: "refusing to merge unrelated histories"

```bash
git pull origin main --allow-unrelated-histories
```

### Need to change remote URL

```bash
git remote set-url origin NEW_URL
```

---

## Questions?

For more GitHub help:
- Official guide: https://docs.github.com/en/get-started
- Git tutorial: https://git-scm.com/book/en/v2
- GitHub Desktop (GUI): https://desktop.github.com/

---

**Ready to push? Follow the steps above! 🚀**

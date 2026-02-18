# GitHub setup for armorfaye

Git is already initialized and the initial commit is done. To create the GitHub repo **MathFellowAttendance** under the **armorfaye** account and push:

## Option A: Using GitHub CLI (if installed)

```bash
# Install gh if needed: brew install gh
gh auth login   # log in as armorfaye
gh repo create MathFellowAttendance --public --source=. --remote=origin --push
```

If you want the repo under a different user/org, use:

```bash
gh repo create armorfaye/MathFellowAttendance --public --source=. --remote=origin --push
```

## Option B: Create repo on GitHub, then push

1. Log in to [GitHub](https://github.com) as **armorfaye**.
2. Click **New repository**.
3. Set **Repository name** to **MathFellowAttendance**.
4. Choose **Public**, do *not* initialize with a README (we already have one).
5. Create the repository.
6. In this project folder, add the remote and push:

```bash
cd /Users/jerryliu/MathFellowAttendance
git remote add origin https://github.com/armorfaye/MathFellowAttendance.git
git branch -M main
git push -u origin main
```

If you use SSH:

```bash
git remote add origin git@github.com:armorfaye/MathFellowAttendance.git
git branch -M main
git push -u origin main
```

After this, the project will be at **https://github.com/armorfaye/MathFellowAttendance**.

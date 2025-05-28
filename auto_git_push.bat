@echo off
cd C:\Users\CMDHR2804\Star11

git config user.name "github-actions"
git config user.email "github-actions@github.com"

git pull origin main --rebase
IF ERRORLEVEL 1 git rebase --abort

git add .
git commit -m "Daily auto update"
git push origin main

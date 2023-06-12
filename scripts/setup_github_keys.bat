@echo off
setlocal enabledelayedexpansion

REM Step 1: Start the SSH agent
echo Starting SSH agent...
ssh-agent > agent.env

REM Step 2: Load the environment variables from agent.env
for /f "usebackq tokens=1,2 delims==;" %%a in ("agent.env") do (
  if "%%a"=="set SSH_AUTH_SOCK" (
    set SSH_AUTH_SOCK=%%b
  )
  if "%%a"=="set SSH_AGENT_PID" (
    set SSH_AGENT_PID=%%b
  )
)

REM Step 3: Add the private key to the SSH agent
echo Adding private key to SSH agent...
ssh-add .ssh/github

echo SSH key setup completed.

endlocal

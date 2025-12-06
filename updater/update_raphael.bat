@echo off
cd d %~dp0..

echo [13] git pull raphael-rs...
cd raphaelraphael-rsraphael-rs
git pull

echo [23] cargo build --release...
cargo build --release
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ 빌드 실패
    exit b 1
)

echo [33] exe & data 동기화...
copy Y targetreleaseraphael-cli.exe ....raphael-cli.exe

echo 완료!
exit b 0

# 修复 Koyeb DNS 污染 - 一键脚本（需要管理员权限）
# 原理：把 koyeb 相关域名直接指向真实 IP，绕过被污染的 DNS

$hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
$entries = @(
    @{ip="34.76.79.153";   domain="koyeb.com"},
    @{ip="34.76.79.153";   domain="app.koyeb.com"},
    @{ip="172.66.172.174"; domain="www.koyeb.com"}
)

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ 需要管理员权限！请右键 PowerShell -> 以管理员身份运行" -ForegroundColor Red
    exit 1
}

# 先备份
Copy-Item $hostsPath "$hostsPath.bak_$(Get-Date -Format yyyyMMdd_HHmmss)" -Force
Write-Host "✅ 已备份原 hosts 文件" -ForegroundColor Green

# 读取现有内容
$hostsContent = Get-Content $hostsPath -Raw -ErrorAction SilentlyContinue
if (-not $hostsContent) { $hostsContent = "" }

# 添加标记区块
$marker = "# ===== Koyeb DNS 修复 (自动添加) ====="
$endMarker = "# ===== Koyeb DNS 修复 结束 ====="

# 移除旧的标记区块
if ($hostsContent -match "(?s)$marker.*?$endMarker") {
    $hostsContent = $hostsContent -replace "(?s)\r?\n?$marker.*?$endMarker\r?\n?", ""
}

# 构建新区块
$newBlock = $marker + "`r`n"
foreach ($e in $entries) {
    $newBlock += "$($e.ip) $($e.domain)`r`n"
}
$newBlock += $endMarker + "`r`n"

# 追加
$newContent = $hostsContent.TrimEnd() + "`r`n`r`n" + $newBlock
Set-Content -Path $hostsPath -Value $newContent -Encoding ASCII -NoNewline
Add-Content -Path $hostsPath -Value ""

Write-Host "✅ 已写入 hosts 修复，添加内容：" -ForegroundColor Green
foreach ($e in $entries) {
    Write-Host "   $($e.ip)  $($e.domain)" -ForegroundColor Cyan
}

# 刷新 DNS 缓存
ipconfig /flushdns | Out-Null
Write-Host "✅ 已刷新 DNS 缓存" -ForegroundColor Green

Write-Host "`n现在打开浏览器访问 https://app.koyeb.com 应该可以正常打开了" -ForegroundColor Yellow
Write-Host "（如果还不行，重启一下浏览器再试）" -ForegroundColor Yellow

Write-Host "`n撤销修复：删除 $hostsPath 中的 'Koyeb DNS 修复' 区块即可" -ForegroundColor Gray

$targets = @(
    [PSCustomObject]@{Name="Koyeb";        IP="34.76.79.153";   Domain="app.koyeb.com"}
    [PSCustomObject]@{Name="HuggingFace";  IP="108.138.246.71"; Domain="huggingface.co"}
    [PSCustomObject]@{Name="Cloudflare";   IP="104.18.9.122";   Domain="pages.cloudflare.com"}
    [PSCustomObject]@{Name="Render";       IP="216.24.57.1";    Domain="render.com"}
    [PSCustomObject]@{Name="Railway";      IP="104.18.11.246";  Domain="railway.app"}
    [PSCustomObject]@{Name="Zeabur";       IP="138.199.9.104";  Domain="zeabur.com"}
    [PSCustomObject]@{Name="Vercel";       IP="76.76.21.21";    Domain="vercel.com"}
    [PSCustomObject]@{Name="GitHub";       IP="140.82.114.3";   Domain="github.com"}
    [PSCustomObject]@{Name="Gitee";        IP="180.97.125.228"; Domain="gitee.com"}
    [PSCustomObject]@{Name="CF Workers";   IP="104.16.0.1";     Domain="workers.cloudflare.com"}
)

foreach ($t in $targets) {
    try {
        $r = Invoke-WebRequest "https://$($t.Domain)/" -TimeoutSec 8 -UseBasicParsing
        "{0,-20} ({1}) : OK (HTTP {2})" -f $t.Name, $t.Domain, $r.StatusCode
    } catch {
        $msg = $_.Exception.Message
        if ($msg.Length -gt 60) { $msg = $msg.Substring(0,60) }
        "{0,-20} ({1}) : FAIL ({2})" -f $t.Name, $t.Domain, $msg
    }
}

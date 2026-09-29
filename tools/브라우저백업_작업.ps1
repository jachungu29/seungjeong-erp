<#
================================================================
 승정 ERP - 브라우저 데이터 원본 백업  (브라우저백업_작업.ps1)
   * 보통은 tools\브라우저백업.bat 을 더블클릭해서 실행합니다.
   * Edge / Chrome / 웨일 / 브레이브 / Claude 앱 / Firefox 저장소에서
     ERP 관련 부분(localStorage, IndexedDB, 서비스워커 캐시)을 "복사만" 합니다.
     (ERP 주소 = file://, GitHub Pages, localhost/127.0.0.1, 사내 LAN/NAS 주소)
   * HTTP 디스크 캐시(Cache\Cache_Data)는 옛 Supabase 응답 흔적이 있을 때만 복사합니다.
   * 다운로드/바탕화면/문서/OneDrive/C:\MES 에 있는 ERP 내보내기 파일과, ERP 가 파일 핸들로
     연결해 둔 파일은 결과 폴더의 '연결파일' 아래로 복사합니다 (원본은 읽기만 함).
   * 브라우저 폴더는 읽기만 합니다. 지우기/이름 바꾸기/쓰기/초기화 절대 없음.
     브라우저를 켜거나 끄지도 않습니다. (켜져 있어도 복사는 됩니다)
   * 결과 폴더
       저장소 안에서 실행 : <저장소>\_private\백업\브라우저원본_<PC이름>_<날짜-시각>
       그 밖의 위치       : 이 파일 옆 승정ERP_브라우저백업\브라우저원본_...
       -OutRoot <폴더>    : 지정한 폴더 아래
   * 복사본 분석 : python tools\브라우저백업_분석.py <결과폴더>
   * 공개 저장소입니다. 이 파일에 서버 주소, 계정, 키 같은 비밀 정보를 적지 마세요.
   * Windows PowerShell 5.1 용. 반드시 "UTF-8 (BOM 포함)" 으로 저장하세요.
     (BOM 이 없으면 PowerShell 5.1 이 한글을 깨뜨립니다)
================================================================
#>
[CmdletBinding()]
param(
    [string]$OutRoot,
    [switch]$NoPause,      # .bat 전용 옵션 (여기서는 쓰지 않음)
    [switch]$NoExplorer    # 끝나고 탐색기 창을 열지 않음
)

$ErrorActionPreference = 'Continue'
# 출력이 파일/파이프로 넘어갈 때도 한글이 깨지지 않게 UTF-8 로 내보냄 (콘솔 창은 원래 정상)
try { if ([Console]::IsOutputRedirected) { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } } catch { }

# ================================================================ 설정값
$Inv       = [System.Globalization.CultureInfo]::InvariantCulture
$Latin1    = [System.Text.Encoding]::GetEncoding(28591)   # 바이트 1개 = 글자 1개 (바이트 검색용)
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
# ERP 관련 여부를 가르는 글자 (영문, 대소문자 무시). sj-erp = ERP 서비스워커 캐시 이름
$ErpPatterns = @('jachungu29', 'seungjeong', 'localhost', '127.0.0.1', 'file://', 'supabase', 'sj-erp')
# 사내 LAN / NAS 주소 (사설 IP, *.local, 시놀로지 QuickConnect·DDNS). ERP 를 NAS·사내 서버 주소로 연 적이 있으면
# 그 데이터도 복사. 공개 저장소이므로 실제 주소는 적지 않고 일반 규칙만 둠
$LanHostRx   = '(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:local|lan|home\.arpa|quickconnect\.to|synology\.me|myds\.me|diskstation\.me|i234\.me))'
$LanOriginRx = '(?i)https?://' + $LanHostRx + '(?![a-z0-9.-])'
# 복사할 IndexedDB 폴더: file:// / github.io / 로컬 개발서버 / 사내 LAN·NAS
$IdbDirRegex = '^(?<o>file__0|https?_jachungu29\.github\.io_\d+|https?_localhost_\d+|https?_127\.0\.0\.1_\d+|https?_' + $LanHostRx + '_\d+)\.indexeddb\.(?<k>leveldb|blob)$'
# Firefox storage\default 아래 복사할 폴더
$FfDirRegex  = '^(file\+\+|https?\+\+\+jachungu29\.github\.io|https?\+\+\+localhost|https?\+\+\+127\.0\.0\.1|https?\+\+\+' + $LanHostRx + '(?=\+|\^|$))'
# 출처를 모르는 WebStorage 묶음 안의 캐시가 이보다 크면 건너뜀
$UnknownCacheLimit = 300MB
# HTTP 디스크 캐시(Cache\Cache_Data): 이 글자가 있으면(옛 Supabase 응답 흔적) 복사. 이보다 크면 목록·작은 항목만
$HttpNeedles    = @('.supabase.co/', '/rest/v1/', '/storage/v1/')
$HttpCacheLimit = 1GB
# ERP 가 브라우저 밖에 저장한 파일 (내보내기 JSON, 데이터 포함 HTML, 파일 핸들로 연결한 DB 파일)
$LinkedNamePatterns = @('SEUNGJEONG_ERP_*.json', '승정ERP_*.json', '승정ERP_데이터포함_*.html', 'seungjeong_erp_db*.json')
$LinkedMaxDepth   = 4
$LinkedFileLimit  = 1GB
$LinkedTotalLimit = 4GB
$LinkedDirLimit   = 30000

$script:LogLines   = New-Object System.Collections.Generic.List[string]
$script:Signatures = @{}
$script:RunDir     = $null
$script:RunDirLP   = $null
# 브라우저 밖 ERP 파일(연결파일) 관련
$script:Linked        = New-Object System.Collections.Generic.List[object]   # 복사한 것
$script:LinkedSkipped = New-Object System.Collections.Generic.List[object]   # 못/안 한 것
$script:LinkedSeen    = @{}
$script:LinkedBytes   = [long]0
$script:LinkedRefs    = New-Object System.Collections.Generic.List[object]   # IndexedDB 안에서 찾은 파일 경로
$script:LinkedRefKeys = @{}
$script:SweepVisited  = @{}
$script:SweepTruncated = $false

# ================================================================ 보조 기능
function Write-Log([string]$Msg) {
    $script:LogLines.Add(((Get-Date).ToString('HH:mm:ss', $Inv) + '  ' + $Msg))
}
function Say([string]$Msg, [string]$Color) {
    if ($Color) { Write-Host $Msg -ForegroundColor $Color } else { Write-Host $Msg }
    Write-Log $Msg
}
function Get-KoName([string]$N) {
    # 화면에 보이는 브라우저·프로필 이름을 한국어로 (폴더 이름·목록 파일은 그대로)
    $map = @{ 'Edge' = '엣지'; 'Chrome' = '크롬'; 'Whale' = '웨일'; 'Brave' = '브레이브'; 'Claude' = '클로드 앱'; 'Claude-Store' = '클로드 앱(스토어)'; 'Firefox' = '파이어폭스'; 'Default' = '기본 프로필' }
    if ($map.ContainsKey($N)) { return $map[$N] }
    if ($N -like 'Profile *') { return ('프로필 ' + $N.Substring(8)) }
    return $N
}
function Format-Size([double]$B) {
    if ($B -ge 1GB) { return ('{0:N2}GB' -f ($B / 1GB)) }
    if ($B -ge 1MB) { return ('{0:N1}MB' -f ($B / 1MB)) }
    if ($B -ge 1KB) { return ('{0:N0}KB' -f ($B / 1KB)) }
    return ('{0}B' -f [long]$B)
}
function Get-InnerEx($Ex) {
    while ($Ex.InnerException) { $Ex = $Ex.InnerException }
    return $Ex
}
# 긴 경로(260자 초과)도 다루도록 \\?\ 형식으로 바꿈
function Get-LP([string]$P) {
    if ($P.StartsWith('\\?\')) { return $P }
    try { $P = [System.IO.Path]::GetFullPath($P) } catch { }
    if ($P.Length -gt 3) { $P = $P.TrimEnd('\') }
    if ($P.StartsWith('\\')) { return '\\?\UNC\' + $P.Substring(2) }
    return '\\?\' + $P
}
function Strip-LP([string]$P) {
    if ($P.StartsWith('\\?\UNC\')) { return '\\' + $P.Substring(8) }
    if ($P.StartsWith('\\?\')) { return $P.Substring(4) }
    return $P
}
function Test-Dir([string]$P) {
    try { return [System.IO.Directory]::Exists((Get-LP $P)) } catch { return $false }
}
function Test-Under([string]$Child, [string]$Parent) {
    if (-not $Child -or -not $Parent) { return $false }
    $c = $Child.TrimEnd('\') + '\'
    $p = $Parent.TrimEnd('\') + '\'
    return $c.StartsWith($p, [System.StringComparison]::OrdinalIgnoreCase)
}
function Join-Rel([string]$A, [string]$B) {
    if ($A -and $B) { return $A + '\' + $B }
    if ($A) { return $A }
    return $B
}
function Get-LocalStamp([datetime]$Utc) {
    return $Utc.ToLocalTime().ToString("yyyy-MM-dd'T'HH:mm:ss", $Inv)
}
# 폴더 이름이 너무 길면(Claude 앱 파티션 등) 짧게 줄임 - 원래 이름은 manifest 의 name 에 남김
function Get-ShortName([string]$N) {
    $safe = $N -replace '[^\w\.\- ]', '_'
    if ($safe.Length -le 40) { return $safe }
    $sha = [System.Security.Cryptography.SHA1]::Create()
    $h = [System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($N))).Replace('-', '').ToLowerInvariant()
    return $safe.Substring(0, 30) + '~' + $h.Substring(0, 8)
}

# 하위 폴더 목록 (연결 지점/심볼릭 링크는 따라가지 않음)
function Get-SubDirs([string]$Dir) {
    $out = New-Object System.Collections.Generic.List[object]
    $lp = Get-LP $Dir
    try {
        if ([System.IO.Directory]::Exists($lp)) {
            foreach ($s in (New-Object System.IO.DirectoryInfo($lp)).GetDirectories()) {
                if (($s.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) {
                    $out.Add([pscustomobject]@{ Name = $s.Name; Full = ($lp + '\' + $s.Name) })
                }
            }
        }
    } catch { Write-Log ('폴더 목록 읽기 실패: ' + (Strip-LP $lp) + ' / ' + (Get-InnerEx $_.Exception).Message) }
    return $out.ToArray()
}

# 폴더 안 파일 목록 (하위 폴더 포함, -DirectOnly 면 바로 아래 파일만)
function Get-TreeFiles {
    param([string]$Dir, [switch]$DirectOnly)
    $files = New-Object System.Collections.Generic.List[object]
    $errs  = New-Object System.Collections.Generic.List[object]
    $rootLP = Get-LP $Dir
    if (-not [System.IO.Directory]::Exists($rootLP)) { return @{ Files = $files; Errors = $errs } }
    $stack = New-Object System.Collections.Generic.Stack[string]
    $stack.Push($rootLP)
    while ($stack.Count -gt 0) {
        $d = $stack.Pop()
        $rp = ''
        if ($d.Length -gt $rootLP.Length) { $rp = $d.Substring($rootLP.Length + 1) }
        try {
            $di = New-Object System.IO.DirectoryInfo($d)
            foreach ($f in $di.GetFiles()) {
                $rel = $f.Name
                if ($rp) { $rel = $rp + '\' + $f.Name }
                $files.Add([pscustomobject]@{ Rel = $rel; Name = $f.Name; Full = ($d + '\' + $f.Name); Length = [long]$f.Length; MTime = $f.LastWriteTimeUtc })
            }
            if (-not $DirectOnly) {
                foreach ($s in $di.GetDirectories()) {
                    if (($s.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) { $stack.Push($d + '\' + $s.Name) }
                }
            }
        } catch {
            $errs.Add([pscustomobject]@{ Rel = $rp; Error = (Get-InnerEx $_.Exception).Message })
        }
    }
    return @{ Files = $files; Errors = $errs }
}
function Get-DirBytes([string]$Dir) {
    $sum = [long]0
    foreach ($f in (Get-TreeFiles -Dir $Dir).Files) { $sum += $f.Length }
    return $sum
}

# 파일 내용을 글자로 읽기 (바이트 검색용). 브라우저가 파일을 열고 있어도 읽을 수 있게 공유 모드로 엶
function Read-Latin1([string]$Path, [long]$Max) {
    $fs = $null
    try {
        $fs = [System.IO.FileStream]::new((Get-LP $Path), [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]'ReadWrite, Delete')
        $n = [int][Math]::Min([long]$fs.Length, $Max)
        if ($n -le 0) { return '' }
        $buf = New-Object byte[] $n
        $off = 0
        while ($off -lt $n) {
            $r = $fs.Read($buf, $off, $n - $off)
            if ($r -le 0) { break }
            $off += $r
        }
        return $Latin1.GetString($buf, 0, $off)
    } catch {
        return ''
    } finally {
        if ($fs) { $fs.Dispose() }
    }
}
# 폴더 바로 아래 파일들(예: CacheStorage 의 index.txt) 내용을 모아서 반환
function Get-DirectText([string]$Dir) {
    $sb = New-Object System.Text.StringBuilder
    foreach ($f in (Get-TreeFiles -Dir $Dir -DirectOnly).Files) { [void]$sb.Append((Read-Latin1 $f.Full 4MB)) }
    return $sb.ToString()
}
function Find-ErpPattern([string]$Text) {
    if (-not $Text) { return $null }
    foreach ($p in $ErpPatterns) {
        if ($Text.IndexOf($p, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { return $p }
    }
    if ([regex]::IsMatch($Text, $LanOriginRx)) { return 'LAN/NAS 주소' }
    return $null
}
# 큰 파일도 4MB 씩 나눠 읽으며 글자(ASCII) 찾기 - 처음 찾은 글자를 반환, 없으면 $null
function Find-InFile([string]$Path, [string[]]$Needles) {
    $fs = $null
    try {
        $fs = [System.IO.FileStream]::new((Get-LP $Path), [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]'ReadWrite, Delete', 1048576)
        $chunk = 4MB; $keep = 256
        $buf = New-Object byte[] ($chunk + $keep)
        $carry = 0
        while ($true) {
            $r = $fs.Read($buf, $carry, $chunk)
            if ($r -le 0) { break }
            $n = $carry + $r
            $s = $Latin1.GetString($buf, 0, $n)
            foreach ($nd in $Needles) {
                if ($s.IndexOf($nd, [System.StringComparison]::Ordinal) -ge 0) { return $nd }
            }
            $carry = [Math]::Min($keep, $n)
            [Array]::Copy($buf, $n - $carry, $buf, 0, $carry)
        }
    } catch {
    } finally {
        if ($fs) { $fs.Dispose() }
    }
    return $null
}
# 화면 표시용: 192.168.a.b:5000 -> 192.168.*.*:5000, a-b.my-id.direct.quickconnect.to -> a***.quickconnect.to
#   (공용 꼬리만 남기고 장비 이름·QuickConnect ID 는 가림)
function Get-MaskedHost([string]$HostPort) {
    $h = $HostPort.ToLowerInvariant(); $port = ''
    $m = [regex]::Match($h, '^(.*?):(\d+)$')
    if ($m.Success) { $h = $m.Groups[1].Value; $port = ':' + $m.Groups[2].Value }
    $ip = [regex]::Match($h, '^(\d+)\.(\d+)\.\d+\.\d+$')
    if ($ip.Success) {
        if ($ip.Groups[1].Value -eq '10') { return '10.*.*.*' + $port }
        return $ip.Groups[1].Value + '.' + $ip.Groups[2].Value + '.*.*' + $port
    }
    foreach ($sfx in @('home.arpa', 'quickconnect.to', 'synology.me', 'myds.me', 'diskstation.me', 'i234.me', 'local', 'lan')) {
        if ($h.EndsWith('.' + $sfx)) { return $h.Substring(0, 1) + '***.' + $sfx + $port }
    }
    $dot = $h.LastIndexOf('.')
    if ($dot -gt 0) { return $h.Substring(0, 1) + '***' + $h.Substring($dot) + $port }
    return '***' + $port
}
# 화면 표시용: 사용자 폴더와 OneDrive 조직 이름을 가림
function Get-MaskedPath([string]$P) {
    $s = [regex]::Replace($P, '(?i)^[a-z]:\\users\\[^\\]+', '%USERPROFILE%')
    return [regex]::Replace($s, '(?i)(OneDrive - )[^\\]+', '$1…')
}
function Get-OriginText([string]$Text) {
    if (-not $Text) { return $null }
    $m = [regex]::Match($Text, '(?:https?|file|chrome-extension)://[\x21-\x7e]*?/')
    if ($m.Success) { return $m.Value }
    return $null
}

# 복사 1건: 원본은 공유 읽기로만 열고, 임시 이름으로 받은 뒤 완성되면 제 이름으로 바꿈 (출력 폴더 안에서만)
function Copy-FileShared([string]$Src, [string]$Dst, [datetime]$MTimeUtc) {
    $dstLP = Get-LP $Dst
    [void][System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($dstLP))
    $tmp = $dstLP + '.sjpart'
    $in = $null; $out = $null; $n = [long]0; $ok = $false
    try {
        $in  = [System.IO.FileStream]::new((Get-LP $Src), [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]'ReadWrite, Delete', 1048576)
        $out = [System.IO.FileStream]::new($tmp, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None, 1048576)
        $in.CopyTo($out, 1048576)
        $n = $out.Length
        $ok = $true
    } finally {
        if ($out) { $out.Dispose() }
        if ($in) { $in.Dispose() }
        if (-not $ok) { try { [System.IO.File]::Delete($tmp) } catch { } }
    }
    if ([System.IO.File]::Exists($dstLP)) { [System.IO.File]::Delete($dstLP) }
    [System.IO.File]::Move($tmp, $dstLP)
    try { [System.IO.File]::SetLastWriteTimeUtc($dstLP, $MTimeUtc) } catch { }
    return $n
}

# 폴더 통째 복사. 브라우저가 켜져 있으면 복사 중에도 파일이 바뀌므로 한 번 더 훑어서 새로 생긴/바뀐 파일을 다시 받음
function Copy-Tree {
    param($Rec, [string]$SrcDir, [string]$RelBase, [switch]$DirectOnly, [string]$NameLike = '*')
    $outBase = $script:RunDirLP + '\' + $Rec.dir
    $done = @{}; $entries = @{}; $fails = @{}; $gone = @{}
    $added = 0
    for ($pass = 1; $pass -le 2; $pass++) {
        $t = Get-TreeFiles -Dir $SrcDir -DirectOnly:$DirectOnly
        if ($pass -eq 1) {
            foreach ($e in $t.Errors) {
                $Rec.failed.Add([pscustomobject]@{ relPath = (Join-Rel $RelBase $e.Rel); error = ('폴더 읽기 실패: ' + $e.Error) })
            }
        }
        foreach ($f in $t.Files) {
            if ($f.Name -eq 'LOCK') { continue }              # 브라우저 잠금 파일 - 복사 불가/불필요
            if ($f.Name -like '*.sjpart') { continue }
            if ($f.Name -notlike $NameLike) { continue }
            $k = $f.Rel.ToLowerInvariant()
            if ($done.ContainsKey($k) -and $done[$k] -eq $f.MTime.Ticks) { continue }
            $rel = Join-Rel $RelBase $f.Rel
            try {
                $n = Copy-FileShared $f.Full ($outBase + '\' + $rel) $f.MTime
                $done[$k] = $f.MTime.Ticks
                if ($entries.ContainsKey($k)) {
                    $entries[$k].bytes = $n
                    $entries[$k].modifiedLocal = (Get-LocalStamp $f.MTime)
                } else {
                    $en = [pscustomobject]@{ relPath = $rel; bytes = $n; modifiedLocal = (Get-LocalStamp $f.MTime) }
                    $entries[$k] = $en
                    $Rec.copied.Add($en)
                    $added++
                }
                $fails.Remove($k); $gone.Remove($k)
            } catch {
                $ex = Get-InnerEx $_.Exception
                if ($entries.ContainsKey($k)) {
                    Write-Log ('  다시 받기 실패(먼저 받은 복사본 유지): ' + $rel + ' / ' + $ex.Message)
                } elseif ($ex -is [System.IO.FileNotFoundException] -or $ex -is [System.IO.DirectoryNotFoundException]) {
                    $gone[$k] = $rel
                } else {
                    $fails[$k] = [pscustomobject]@{ relPath = $rel; error = $ex.Message }
                }
            }
        }
    }
    foreach ($v in $fails.Values) { $Rec.failed.Add($v); Write-Log ('  실패 ' + $v.relPath + ' / ' + $v.error) }
    foreach ($v in $gone.Values) {
        $Rec.skipped.Add([pscustomobject]@{ relPath = $v; reason = '복사 도중 브라우저가 정리한 파일 (정상)'; bytes = 0 })
    }
    return $added
}

function Add-Skip($Rec, [string]$Rel, [string]$Reason, [long]$Bytes) {
    $Rec.skipped.Add([pscustomobject]@{ relPath = $Rel; reason = $Reason; bytes = $Bytes })
    Write-Log ('  건너뜀 ' + $Rel + ' (' + (Format-Size $Bytes) + ') - ' + $Reason)
}

function New-Record([string]$Name, [string]$Dir, [string]$Source) {
    return [pscustomobject]@{
        name        = $Name
        dir         = $Dir
        source      = $Source
        duplicateOf = $null
        copied      = New-Object System.Collections.Generic.List[object]
        skipped     = New-Object System.Collections.Generic.List[object]
        failed      = New-Object System.Collections.Generic.List[object]
        buckets     = New-Object System.Collections.Generic.List[object]
        hints       = [pscustomobject]@{
            fileIdb      = $false
            githubIdb    = $false
            localhostIdb = New-Object System.Collections.Generic.List[string]
            lanIdb       = New-Object System.Collections.Generic.List[string]
            erpSwCache   = $false
            httpCacheSupabase = $false
            localStorage = $false
            lsFile       = $false
            lsGithub     = $false
            lsLocalhost  = $false
            lsLan        = New-Object System.Collections.Generic.List[string]
        }
    }
}

# IndexedDB 출처(폴더 이름 또는 storage key)로 흔적 표시
function Add-IdbHint($Rec, [string]$Text) {
    if (-not $Text) { return }
    if ($Text -match '^file(__0|:)') { $Rec.hints.fileIdb = $true }
    if ($Text -match 'jachungu29\.github\.io') { $Rec.hints.githubIdb = $true }
    $hp = $null
    if ($Text -match '(localhost|127\.0\.0\.1)[_:](\d+)') { $hp = $Matches[1] + ':' + $Matches[2] }
    elseif ($Text -match '(localhost|127\.0\.0\.1)') { $hp = $Matches[1] }
    if ($hp -and -not $Rec.hints.localhostIdb.Contains($hp)) { $Rec.hints.localhostIdb.Add($hp) }
    $lm = [regex]::Match($Text, '(?i)https?(?:_|://)(' + $LanHostRx + ')(?:[_:](\d+))?')
    if ($lm.Success) {
        $lh = $lm.Groups[1].Value.ToLowerInvariant()
        if ($lm.Groups[2].Success) { $lh = $lh + ':' + $lm.Groups[2].Value }
        if (-not $Rec.hints.lanIdb.Contains($lh)) { $Rec.hints.lanIdb.Add($lh) }
    }
}

# 복사한 localStorage 파일 안에 ERP 출처 키가 있는지 대략 확인 (추정용)
function Set-LsHints($Rec, [string]$LsDirLP) {
    foreach ($f in (Get-TreeFiles -Dir $LsDirLP -DirectOnly).Files) {
        if ($f.Name -notmatch '\.(log|ldb)$') { continue }
        $s = Read-Latin1 $f.Full 512MB
        if (-not $s) { continue }
        if ($s.Contains("_file://`0") -or $s.Contains('META:file://')) { $Rec.hints.lsFile = $true }
        if ($s.Contains('jachungu29.github.io')) { $Rec.hints.lsGithub = $true }
        if ([regex]::IsMatch($s, '(?:_|META:)https?://(?:localhost|127\.0\.0\.1)')) { $Rec.hints.lsLocalhost = $true }
        foreach ($m in [regex]::Matches($s, '(?i)(?:_|META:)https?://(' + $LanHostRx + ')(?::(\d+))?(?![a-z0-9.-])')) {
            if ($Rec.hints.lsLan.Count -ge 20) { break }
            $lh = $m.Groups[1].Value.ToLowerInvariant()
            if ($m.Groups[2].Success) { $lh = $lh + ':' + $m.Groups[2].Value }
            if (-not $Rec.hints.lsLan.Contains($lh)) { $Rec.hints.lsLan.Add($lh) }
        }
    }
}

# 복사한 IndexedDB(leveldb) 안에서 ERP 가 파일 핸들로 연결해 둔 파일 경로 찾기 (예: C:\...\xxx.json)
#   경로는 UTF-16LE 로 들어 있는 것이 보통 - UTF-8 / UTF-16LE(짝수·홀수 위치) 세 가지로 훑음. 압축된 .ldb 안의
#   경로는 못 찾을 수도 있음 (그 경우에도 이름 규칙 검색과 분석기(parse.py)의 targetPath 로 보완)
function Find-LinkedPathRefs([string]$LdbCopyDir, [string]$From) {
    $rx = '(?i)(?:[a-z]:\\|\\\\[^\\\x00-\x1f]{1,80}\\)[^\x00-\x1f"*?<>|]{1,250}?\.(?:json|html?)(?![a-z0-9])'
    foreach ($f in (Get-TreeFiles -Dir $LdbCopyDir -DirectOnly).Files) {
        if ($f.Name -notmatch '\.(log|ldb)$') { continue }
        if ($f.Length -lt 8 -or $f.Length -gt 256MB) { continue }
        $bytes = $null
        try { $bytes = [System.IO.File]::ReadAllBytes($f.Full) } catch { continue }
        $views = @(
            @{ T = $Latin1.GetString($bytes); U8 = $true },
            @{ T = [System.Text.Encoding]::Unicode.GetString($bytes, 0, $bytes.Length - ($bytes.Length % 2)); U8 = $false },
            @{ T = [System.Text.Encoding]::Unicode.GetString($bytes, 1, ($bytes.Length - 1) - (($bytes.Length - 1) % 2)); U8 = $false })
        foreach ($v in $views) {
            foreach ($m in [regex]::Matches($v.T, $rx)) {
                $p = $m.Value
                if ($v.U8) { try { $p = (New-Object System.Text.UTF8Encoding($false, $true)).GetString($Latin1.GetBytes($p)) } catch { continue } }
                $k = $p.ToLowerInvariant()
                if (-not $script:LinkedRefKeys.ContainsKey($k)) {
                    $script:LinkedRefKeys[$k] = $true
                    $script:LinkedRefs.Add([pscustomobject]@{ path = $p; foundIn = $From })
                }
            }
        }
    }
}

# ERP 파일 1개를 '<실행폴더>\연결파일\' 로 복사 (원본은 읽기만). 클라우드 전용 파일은 내려받기가 일어나므로 복사 안 함
function Copy-LinkedFile([string]$Path, [string]$Reason) {
    if (-not $Path) { return }
    $plain = Strip-LP $Path
    $k = $plain.ToLowerInvariant()
    if ($script:LinkedSeen.ContainsKey($k)) { return }
    $script:LinkedSeen[$k] = $true
    if (Test-Under $plain $outRootFull) { return }
    if ($inRepo -and (Test-Under $plain $repoRoot)) { return }
    $fi = $null
    try { $fi = New-Object System.IO.FileInfo((Get-LP $plain)) } catch { }
    if (-not $fi -or -not $fi.Exists) {
        $script:LinkedSkipped.Add([pscustomobject]@{ source = $plain; reason = ('이 PC 에 파일 없음 - ' + $Reason); bytes = 0; modifiedLocal = $null })
        return
    }
    $mod = Get-LocalStamp $fi.LastWriteTimeUtc
    $attr = [long]$fi.Attributes
    # 0x400000 RecallOnDataAccess / 0x40000 RecallOnOpen / 0x1000 Offline = OneDrive 등 클라우드 전용(아직 안 내려받음)
    if ((($attr -band 0x400000) -ne 0) -or (($attr -band 0x40000) -ne 0) -or (($attr -band 0x1000) -ne 0)) {
        $script:LinkedSkipped.Add([pscustomobject]@{ source = $plain; reason = '클라우드 전용 파일 - 열면 내려받기가 일어나므로 복사 안 함 (필요하면 "이 장치에 항상 유지" 후 다시 실행)'; bytes = [long]$fi.Length; modifiedLocal = $mod })
        return
    }
    if ($fi.Length -gt $LinkedFileLimit -or ($script:LinkedBytes + $fi.Length) -gt $LinkedTotalLimit) {
        $script:LinkedSkipped.Add([pscustomobject]@{ source = $plain; reason = '크기 제한 초과 (파일당 1GB, 합계 4GB)'; bytes = [long]$fi.Length; modifiedLocal = $mod })
        return
    }
    $destRel = '연결파일\' + ('{0:D3}_' -f ($script:Linked.Count + 1)) + $fi.Name
    try {
        $n = Copy-FileShared $fi.FullName ($script:RunDirLP + '\' + $destRel) $fi.LastWriteTimeUtc
        $script:LinkedBytes += $n
        $script:Linked.Add([pscustomobject]@{ source = $plain; copiedAs = $destRel; bytes = $n; modifiedLocal = $mod; reason = $Reason })
        Write-Log ('  연결파일 복사: ' + $destRel + ' <- ' + $plain)
    } catch {
        $script:LinkedSkipped.Add([pscustomobject]@{ source = $plain; reason = ('복사 실패: ' + (Get-InnerEx $_.Exception).Message); bytes = [long]$fi.Length; modifiedLocal = $mod })
    }
}

# 폴더를 깊이 제한(기본 4단계)으로 훑어 ERP 파일 이름 규칙에 맞는 파일을 복사. 읽기만 함
#   OneDrive 폴더는 연결 지점(재분석 지점) 표시가 붙어 있어도 들어가야 하므로 깊이·개수 제한으로만 막음
function Search-LinkedFiles([string]$Root, [int]$MaxDepth) {
    if (-not $Root -or -not (Test-Dir $Root)) { return }
    $stack = New-Object System.Collections.Generic.Stack[object]
    $stack.Push([pscustomobject]@{ D = (Get-LP $Root); Depth = 0 })
    while ($stack.Count -gt 0) {
        $top = $stack.Pop()
        $dk = $top.D.ToLowerInvariant()
        if ($script:SweepVisited.ContainsKey($dk)) { continue }
        if ($script:SweepVisited.Count -ge $LinkedDirLimit) { $script:SweepTruncated = $true; return }
        $script:SweepVisited[$dk] = $true
        $plain = Strip-LP $top.D
        if (Test-Under $plain $outRootFull) { continue }
        if ($inRepo -and (Test-Under $plain $repoRoot)) { continue }
        try {
            $di = New-Object System.IO.DirectoryInfo($top.D)
            foreach ($f in $di.GetFiles()) {
                foreach ($pat in $LinkedNamePatterns) {
                    if ($f.Name -like $pat) { Copy-LinkedFile $f.FullName '파일 이름 규칙' ; break }
                }
            }
            if ($top.Depth -lt $MaxDepth) {
                foreach ($s in $di.GetDirectories()) {
                    if (@('node_modules', '.git', '$RECYCLE.BIN', 'System Volume Information') -contains $s.Name) { continue }
                    $stack.Push([pscustomobject]@{ D = ($top.D + '\' + $s.Name); Depth = ($top.Depth + 1) })
                }
            }
        } catch {
            Write-Log ('  폴더 훑기 실패: ' + $plain + ' / ' + (Get-InnerEx $_.Exception).Message)
        }
    }
}

# WebStorage\QuotaManager (SQLite) 에서 "묶음 번호 -> 사이트 주소" 표를 바이트 검색으로 읽음
#   buckets 표 한 줄 = [길이][번호][머리 크기][0x00(id)][주소 길이]... 바로 뒤에 주소 글자
function Get-BucketMap([string]$Path) {
    $map = @{}
    $s = Read-Latin1 $Path 64MB
    if (-not $s) { return $map }
    foreach ($m in [regex]::Matches($s, '(?:https?|file|chrome-extension|isolated-app)://')) {
        $p = $m.Index
        for ($h = 3; $h -le 60 -and $h -lt $p; $h++) {
            $hs = $p - $h
            if ([int]$s[$hs] -ne $h -or [int]$s[$hs + 1] -ne 0) { continue }
            $v = [long]0; $i = $hs + 2; $ok = $false
            for ($q = 0; $q -lt 9 -and $i -lt $p; $q++) {
                $b = [int]$s[$i]
                $v = ($v -shl 7) -bor ($b -band 0x7f)
                $i++
                if (($b -band 0x80) -eq 0) { $ok = $true; break }
            }
            if (-not $ok -or $v -lt 13 -or ($v % 2) -ne 1) { continue }
            $len = [int](($v - 13) / 2)
            if ($len -le 0 -or ($p + $len) -gt $s.Length) { continue }
            $e = $hs - 1
            if ($e -lt 1 -or ([int]$s[$e] -band 0x80) -ne 0) { continue }
            $st = $e
            while ($st -gt 0 -and ($e - $st) -lt 8 -and ([int]$s[$st - 1] -band 0x80) -ne 0) { $st-- }
            $rid = [long]0
            for ($j = $st; $j -le $e; $j++) { $rid = ($rid -shl 7) -bor ([int]$s[$j] -band 0x7f) }
            if ($rid -gt 0) { $map[[string]$rid] = $s.Substring($p, $len) }
            break
        }
    }
    return $map
}

# 같은 폴더가 두 경로로 보이는 경우(Claude 앱 등) 두 번 복사하지 않도록 지문 비교
function Get-ProfileSignature([string]$ProfDir) {
    $P = Get-LP $ProfDir
    $parts = New-Object System.Collections.Generic.List[string]
    try {
        $fi = New-Object System.IO.FileInfo($P + '\Preferences')
        if ($fi.Exists) { $parts.Add('P:' + $fi.Length + ':' + $fi.LastWriteTimeUtc.Ticks) }
    } catch { }
    foreach ($f in ((Get-TreeFiles -Dir ($P + '\Local Storage\leveldb') -DirectOnly).Files | Sort-Object Name)) {
        if ($f.Name -match '\.ldb$|^MANIFEST|^CURRENT$') { $parts.Add($f.Name + ':' + $f.Length + ':' + $f.MTime.Ticks) }
    }
    if ($parts.Count -eq 0) { return $null }
    return ($parts -join '|')
}

# ---------------------------------------------------------------- Chromium 계열 프로필 1개
function Backup-ChromiumProfile {
    param([string]$Name, [string]$ProfDir, [string]$OutRel)
    $P = Get-LP $ProfDir
    $rec = New-Record $Name $OutRel (Strip-LP $P)

    $sig = Get-ProfileSignature $P
    if ($sig) {
        if ($script:Signatures.ContainsKey($sig)) {
            $rec.duplicateOf = $script:Signatures[$sig]
            Write-Log ('  같은 폴더를 다른 경로로 이미 복사함: ' + $rec.duplicateOf)
            return $rec
        }
        $script:Signatures[$sig] = $OutRel
    }

    # (1) localStorage - 모든 사이트가 한 LevelDB 에 들어 있어서 폴더 통째로 복사
    $n = Copy-Tree -Rec $rec -SrcDir ($P + '\Local Storage\leveldb') -RelBase 'Local Storage\leveldb'
    if ($n -gt 0) {
        $rec.hints.localStorage = $true
        Set-LsHints $rec ($script:RunDirLP + '\' + $OutRel + '\Local Storage\leveldb')
    }

    # (2) IndexedDB - ERP 출처 폴더만 (leveldb + blob)
    #     같은 출처는 반드시 leveldb 를 먼저, blob 을 나중에 복사한다. 브라우저는 blob 파일을 먼저 쓰고 나서
    #     leveldb 에 기록하므로, 이 순서면 복사한 leveldb 가 가리키는 blob(사진·큰 값)이 빠지지 않는다.
    $idbMatch = New-Object System.Collections.Generic.List[object]
    foreach ($d in (Get-SubDirs ($P + '\IndexedDB'))) {
        if ($d.Name -match $IdbDirRegex) {
            $ord = 1
            if ($Matches['k'] -eq 'leveldb') { $ord = 0 }
            $idbMatch.Add([pscustomobject]@{ Dir = $d; Origin = $Matches['o']; Kind = $Matches['k']; Order = $ord })
        } else {
            Add-Skip $rec ('IndexedDB\' + $d.Name) 'ERP와 무관한 사이트' (Get-DirBytes $d.Full)
        }
    }
    foreach ($it in @($idbMatch | Sort-Object Origin, Order)) {
        $rel = 'IndexedDB\' + $it.Dir.Name
        $c = Copy-Tree -Rec $rec -SrcDir $it.Dir.Full -RelBase $rel
        if ($c -gt 0 -and $it.Kind -eq 'leveldb') {
            Add-IdbHint $rec $it.Origin
            # ERP 가 파일 핸들로 연결해 둔 파일(예: ...\seungjeong_erp_db.json) 경로 찾기 - 나중에 그 파일도 복사
            Find-LinkedPathRefs ($script:RunDirLP + '\' + $OutRel + '\' + $rel) ($OutRel + '\' + $rel)
        }
    }

    # (3) 서비스워커 등록 정보
    [void](Copy-Tree -Rec $rec -SrcDir ($P + '\Service Worker\Database') -RelBase 'Service Worker\Database')

    # (4) 서비스워커 캐시 - index.txt 에 ERP 흔적이 있는 것만
    foreach ($d in (Get-SubDirs ($P + '\Service Worker\CacheStorage'))) {
        $rel = 'Service Worker\CacheStorage\' + $d.Name
        $txt = Get-DirectText $d.Full
        $hit = Find-ErpPattern $txt
        $origin = Get-OriginText $txt
        if ($hit) {
            $c = Copy-Tree -Rec $rec -SrcDir $d.Full -RelBase $rel
            Write-Log ('  서비스워커 캐시 복사: ' + $rel + ' (' + $origin + ', 파일 ' + $c + '개)')
            if ($txt -match 'sj-erp|jachungu29\.github\.io') { $rec.hints.erpSwCache = $true }
        } else {
            $why = '관련 없는 캐시'
            if ($origin) { $why = '관련 없는 캐시: ' + $origin }
            Add-Skip $rec $rel $why (Get-DirBytes $d.Full)
        }
    }

    # (5) 새 방식 저장소 WebStorage\<묶음번호> - 사이트 주소는 QuotaManager 에 있음
    $W = $P + '\WebStorage'
    if (Test-Dir $W) {
        [void](Copy-Tree -Rec $rec -SrcDir $W -RelBase 'WebStorage' -DirectOnly -NameLike 'QuotaManager*')
        $map = Get-BucketMap ($W + '\QuotaManager')
        foreach ($b in (Get-SubDirs $W)) {
            $rel = 'WebStorage\' + $b.Name
            $key = $null
            if ($map.ContainsKey($b.Name)) { $key = $map[$b.Name] }
            $csTxt = Read-Latin1 ($b.Full + '\CacheStorage\index.txt') 4MB
            $csOrigin = Get-OriginText $csTxt
            $hit = $null
            if ($key) { $hit = Find-ErpPattern $key }
            if (-not $hit -and $csTxt) { $hit = Find-ErpPattern $csTxt }
            $dec = ''
            if ($hit) {
                $dec = 'copied'
                [void](Copy-Tree -Rec $rec -SrcDir $b.Full -RelBase $rel)
                $src = $key
                if (-not $src) { $src = $csOrigin }
                if (Test-Dir ($b.Full + '\IndexedDB')) { Add-IdbHint $rec $src }
                if ($csTxt -match 'sj-erp|jachungu29\.github\.io') { $rec.hints.erpSwCache = $true }
            } elseif ($key -or $csOrigin) {
                $dec = 'skipped'
                $who = $key
                if (-not $who) { $who = $csOrigin }
                Add-Skip $rec $rel ('ERP와 무관한 사이트: ' + $who) (Get-DirBytes $b.Full)
            } else {
                # 출처를 알 수 없음 -> 일단 복사. 단 300MB 넘는 캐시는 제외
                $dec = 'copied-unknown'
                [void](Copy-Tree -Rec $rec -SrcDir $b.Full -RelBase $rel -DirectOnly)
                foreach ($sub in (Get-SubDirs $b.Full)) {
                    $subRel = $rel + '\' + $sub.Name
                    if ($sub.Name -eq 'CacheStorage') {
                        $sz = Get-DirBytes $sub.Full
                        if ($sz -gt $UnknownCacheLimit) { Add-Skip $rec $subRel '출처 불명 + 300MB 초과 캐시' $sz; continue }
                    }
                    [void](Copy-Tree -Rec $rec -SrcDir $sub.Full -RelBase $subRel)
                }
            }
            $rec.buckets.Add([pscustomobject]@{ id = $b.Name; storageKey = $key; cacheOrigin = $csOrigin; decision = $dec })
        }
    }

    # (6) HTTP 디스크 캐시 (Cache\Cache_Data) - fetch() 로 받은 옛 Supabase 응답이 남아 있을 수 있는 곳.
    #     더블클릭(file://)으로 연 ERP 는 서비스워커를 못 쓰므로 여기가 유일한 후보. Supabase 흔적이 있을 때만 복사.
    #     (이 폴더에는 다른 사이트에서 받은 페이지·이미지 캐시도 섞여 있음)
    $C = $P + '\Cache\Cache_Data'
    if (Test-Dir $C) {
        $hit = $null
        foreach ($nm in @('data_1', 'data_2', 'data_3', 'data_0', 'index')) {
            $hit = Find-InFile ($C + '\' + $nm) $HttpNeedles
            if ($hit) { break }
        }
        # 간이(simple) 캐시 형식: 파일마다 앞부분에 URL(키)이 있음
        $simpleHits = New-Object System.Collections.Generic.List[string]
        foreach ($f in (Get-TreeFiles -Dir $C -DirectOnly).Files) {
            if ($f.Name -notmatch '^[0-9a-f]{16}_0$') { continue }
            $head = Read-Latin1 $f.Full 4096
            foreach ($nd in $HttpNeedles) {
                if ($head.IndexOf($nd, [System.StringComparison]::Ordinal) -ge 0) { $simpleHits.Add($f.Name); if (-not $hit) { $hit = $nd }; break }
            }
        }
        $sz = Get-DirBytes $C
        if ($hit) {
            $rec.hints.httpCacheSupabase = $true
            if ($sz -le $HttpCacheLimit) {
                $c = Copy-Tree -Rec $rec -SrcDir $C -RelBase 'Cache\Cache_Data'
                Write-Log ('  HTTP 캐시 복사 (흔적 "' + $hit + '"): 파일 ' + $c + '개, ' + (Format-Size $sz))
            } else {
                # 너무 크면 목록(index)과 작은 항목·헤더가 든 data_* 파일, 흔적이 있는 간이 캐시 파일만
                [void](Copy-Tree -Rec $rec -SrcDir $C -RelBase 'Cache\Cache_Data' -DirectOnly -NameLike 'index')
                [void](Copy-Tree -Rec $rec -SrcDir $C -RelBase 'Cache\Cache_Data' -DirectOnly -NameLike 'data_*')
                [void](Copy-Tree -Rec $rec -SrcDir ($C + '\index-dir') -RelBase 'Cache\Cache_Data\index-dir')
                foreach ($sn in $simpleHits) {
                    [void](Copy-Tree -Rec $rec -SrcDir $C -RelBase 'Cache\Cache_Data' -DirectOnly -NameLike $sn)
                }
                Add-Skip $rec 'Cache\Cache_Data (큰 본문 파일)' ('HTTP 캐시가 ' + (Format-Size $HttpCacheLimit) + ' 초과 - index·data_* 와 흔적 있는 항목만 복사') $sz
            }
        } else {
            Add-Skip $rec 'Cache\Cache_Data' 'Supabase 흔적 없는 HTTP 캐시' $sz
        }
    }
    return $rec
}

# ---------------------------------------------------------------- Firefox 프로필 1개
function Backup-FirefoxProfile {
    param([string]$Name, [string]$ProfDir, [string]$OutRel)
    $P = Get-LP $ProfDir
    $rec = New-Record $Name $OutRel (Strip-LP $P)
    foreach ($d in (Get-SubDirs ($P + '\storage\default'))) {
        if ($d.Name -notmatch $FfDirRegex) { continue }
        $c = Copy-Tree -Rec $rec -SrcDir $d.Full -RelBase ('storage\default\' + $d.Name)
        if ($c -le 0) { continue }
        $hasIdb = Test-Dir ($d.Full + '\idb')
        $hasLs  = Test-Dir ($d.Full + '\ls')
        if ($hasLs) { $rec.hints.localStorage = $true }
        if ($d.Name -like 'file++*') {
            if ($hasIdb) { $rec.hints.fileIdb = $true }
            if ($hasLs) { $rec.hints.lsFile = $true }
        } elseif ($d.Name -like '*jachungu29*') {
            if ($hasIdb) { $rec.hints.githubIdb = $true }
            if ($hasLs) { $rec.hints.lsGithub = $true }
            if (Test-Dir ($d.Full + '\cache')) { $rec.hints.erpSwCache = $true }
        } else {
            $hp = $d.Name -replace '\^.*$', '' -replace '^https?\+\+\+', '' -replace '\+', ':'
            $isLan = $d.Name -notmatch '^https?\+\+\+(localhost|127\.0\.0\.1)'
            if ($hasIdb) {
                if ($isLan) { if (-not $rec.hints.lanIdb.Contains($hp)) { $rec.hints.lanIdb.Add($hp) } }
                elseif (-not $rec.hints.localhostIdb.Contains($hp)) { $rec.hints.localhostIdb.Add($hp) }
            }
            if ($hasLs) {
                if ($isLan) { if (-not $rec.hints.lsLan.Contains($hp)) { $rec.hints.lsLan.Add($hp) } }
                else { $rec.hints.lsLocalhost = $true }
            }
        }
    }
    $c = Copy-Tree -Rec $rec -SrcDir $P -RelBase '' -DirectOnly -NameLike 'webappsstore.sqlite*'
    if ($c -gt 0) { $rec.hints.localStorage = $true }
    return $rec
}

function Get-HintText($Rec) {
    $h = $Rec.hints
    $parts = New-Object System.Collections.Generic.List[string]
    if ($h.lsFile)      { $parts.Add('파일로 연 ERP 저장값') }
    if ($h.fileIdb)     { $parts.Add('파일로 연 ERP 사진·자료') }
    if ($h.lsGithub)    { $parts.Add('인터넷 주소 ERP 저장값') }
    if ($h.githubIdb)   { $parts.Add('인터넷 주소 ERP 사진·자료') }
    if ($h.lsLocalhost) { $parts.Add('로컬 서버 ERP 저장값') }
    if ($h.localhostIdb.Count -gt 0) { $parts.Add('로컬 서버 ERP 사진·자료(' + ($h.localhostIdb -join ', ') + ')') }
    if ($h.lsLan.Count -gt 0) { $parts.Add('회사 나스 주소 저장값(' + ((@($h.lsLan) | ForEach-Object { Get-MaskedHost $_ }) -join ', ') + ')') }
    if ($h.lanIdb.Count -gt 0) { $parts.Add('회사 나스 주소 사진·자료(' + ((@($h.lanIdb) | ForEach-Object { Get-MaskedHost $_ }) -join ', ') + ')') }
    if ($h.erpSwCache)  { $parts.Add('ERP 앱 저장본') }
    if ($h.httpCacheSupabase) { $parts.Add('임시 인터넷 파일에 옛 인터넷 DB 흔적') }
    return ($parts -join ', ')
}
function Get-CopiedBytes($Rec) {
    $s = [long]0
    foreach ($c in $Rec.copied) { $s += [long]$c.bytes }
    return $s
}
function Show-ProfileLine($Rec) {
    if ($Rec.duplicateOf) {
        Say ('  - {0} : 이미 복사한 폴더({1})와 같은 곳 - 건너뜀' -f (Get-KoName $Rec.name), $Rec.duplicateOf) 'DarkGray'
        return
    }
    $col = 'Gray'
    if ($Rec.failed.Count -gt 0) { $col = 'Yellow' }
    Say ('  - {0} : 복사 {1}개 ({2}) / 건너뜀 {3}개 / 실패 {4}개' -f (Get-KoName $Rec.name), $Rec.copied.Count, (Format-Size (Get-CopiedBytes $Rec)), $Rec.skipped.Count, $Rec.failed.Count) $col
    $ht = Get-HintText $Rec
    if ($ht) { Say ('      ERP 흔적: ' + $ht) 'Green' }
}

function Stop-Run([string[]]$Lines) {
    Write-Host ''
    foreach ($l in $Lines) { Write-Host $l -ForegroundColor Red }
    Write-Host ''
    Write-Host ' 아무것도 복사하지 않고 종료합니다.' -ForegroundColor Red
    exit 1
}

# ================================================================ 시작
$startTime = Get-Date
$watch = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host '================================================================'
Write-Host ' 승정 ERP - 브라우저 데이터 백업 (원본 복사 / 브라우저는 읽기만 함)'
Write-Host '================================================================'

# ---- [1] 저장 위치 정하기
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir '..')).TrimEnd('\')
$inRepo = Test-Path -LiteralPath (Join-Path $repoRoot '.git')
$explicitOut = [bool]$OutRoot
if ($OutRoot) {
    $o = $OutRoot
    if (-not [System.IO.Path]::IsPathRooted($o)) { $o = Join-Path (Get-Location).ProviderPath $o }
    $outRootFull = [System.IO.Path]::GetFullPath($o)
} elseif ($inRepo) {
    $outRootFull = Join-Path $repoRoot '_private\백업'
} else {
    $outRootFull = Join-Path $scriptDir '승정ERP_브라우저백업'
}
if ($outRootFull.Length -gt 3) { $outRootFull = $outRootFull.TrimEnd('\') }

# 공개 저장소 안에 저장한다면: 반드시 _private 아래 + .gitignore 에 _private/ 가 있어야 함
if ($inRepo -and (Test-Under $outRootFull $repoRoot)) {
    $okPrivate = Test-Under $outRootFull (Join-Path $repoRoot '_private')
    $okIgnore = $false
    $gi = Join-Path $repoRoot '.gitignore'
    if (Test-Path -LiteralPath $gi) {
        foreach ($line in [System.IO.File]::ReadAllLines($gi)) {
            if ($line.Trim() -match '^/?_private/?(\*\*)?$') { $okIgnore = $true }
        }
    }
    if (-not $okPrivate) {
        Stop-Run @(' [중지] 저장 위치가 공개 깃허브 저장소 안인데 비공개 폴더(_private) 밖입니다.',
                   ('        지정한 위치: ' + $outRootFull),
                   '        브라우저 데이터가 깃허브에 올라갈 수 있어 중지합니다.',
                   '        저장 위치를 지정하지 말고 실행하거나, 비공개 폴더(_private) 아래를 지정하세요.')
    }
    if (-not $okIgnore) {
        Stop-Run @(' [중지] 깃허브 제외 목록(.gitignore)에 "_private/" 줄이 없습니다.',
                   '        이대로 저장하면 브라우저 데이터가 공개 깃허브에 올라갈 수 있습니다.',
                   ('        확인할 파일: ' + $gi),
                   '        작업시작.bat 으로 최신 파일을 받은 뒤 다시 실행하거나 클로드에게 물어보세요.')
    }
}

# 브라우저 폴더 안에는 절대 쓰지 않음
$L = $env:LOCALAPPDATA
$R = $env:APPDATA
$targets = New-Object System.Collections.Generic.List[object]
$targets.Add(@{ Name = 'Edge';   Root = "$L\Microsoft\Edge\User Data";           Kind = 'profiles' })
$targets.Add(@{ Name = 'Chrome'; Root = "$L\Google\Chrome\User Data";            Kind = 'profiles' })
$targets.Add(@{ Name = 'Whale';  Root = "$L\Naver\Naver Whale\User Data";        Kind = 'profiles' })
$targets.Add(@{ Name = 'Brave';  Root = "$L\BraveSoftware\Brave-Browser\User Data"; Kind = 'profiles' })
$targets.Add(@{ Name = 'Claude'; Root = "$R\Claude\Partitions";                  Kind = 'partitions' })
$storeNo = 0
if (Test-Path -LiteralPath "$L\Packages") {
    foreach ($pk in @(Get-ChildItem -LiteralPath "$L\Packages" -Directory -Filter 'Claude_*' -ErrorAction SilentlyContinue)) {
        $storeNo++
        $nm = 'Claude-Store'
        if ($storeNo -gt 1) { $nm = 'Claude-Store' + $storeNo }
        $targets.Add(@{ Name = $nm; Root = (Join-Path $pk.FullName 'LocalCache\Roaming\Claude\Partitions'); Kind = 'partitions' })
    }
}
$ffRoot = "$R\Mozilla\Firefox\Profiles"
$guardRoots = @($targets | ForEach-Object { $_.Root }) + @($ffRoot, "$R\Claude", "$L\Packages")
foreach ($g in $guardRoots) {
    if (Test-Under $outRootFull $g) {
        Stop-Run @(' [중지] 저장 위치가 브라우저 데이터 폴더 안입니다. 다른 폴더를 지정하세요.', ('        지정한 위치: ' + $outRootFull))
    }
}

# OneDrive 안이면 클라우드로 올라가므로 위험
$inOneDrive = $false
foreach ($od in @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer)) {
    if ($od -and (Test-Under $outRootFull $od)) { $inOneDrive = $true }
}
if ($outRootFull -match '\\OneDrive( - [^\\]+)?(\\|$)') { $inOneDrive = $true }
if ($inOneDrive -and -not $explicitOut) {
    Stop-Run @(' [중지] 저장 위치가 원드라이브 폴더 안입니다. 브라우저 데이터가 클라우드로 올라갈 수 있습니다.',
               ('        기본 위치: ' + $outRootFull),
               '        이 도구 폴더를 C:\ERP\seungjeong-erp\tools 에 두고 다시 실행하거나 클로드에게 물어보세요.')
}

# 실행 폴더 만들기 (현지 시각)
$stamp = (Get-Date).ToString('yyyyMMdd-HHmmss', $Inv)
$pcName = $env:COMPUTERNAME
if (-not $pcName) { $pcName = 'PC' }
$runName = '브라우저원본_' + $pcName + '_' + $stamp
$script:RunDir = Join-Path $outRootFull $runName
$dupNo = 2
while (Test-Path -LiteralPath $script:RunDir) {
    $script:RunDir = Join-Path $outRootFull ($runName + '_' + $dupNo)
    $dupNo++
}
try {
    [void][System.IO.Directory]::CreateDirectory((Get-LP $script:RunDir))
} catch {
    Stop-Run @(' [오류] 저장 폴더를 만들 수 없습니다.', ('        위치: ' + $script:RunDir), ('        이유: ' + (Get-InnerEx $_.Exception).Message))
}
$script:RunDirLP = Get-LP $script:RunDir
$runName = Split-Path -Leaf $script:RunDir

Say (' 저장 폴더 : ' + $script:RunDir)
if ($inOneDrive) {
    Say ' [주의] 지정한 저장 위치가 원드라이브 안입니다. 다 끝나면 USB 등으로 옮기고 원드라이브에서는 지우세요.' 'Yellow'
}

# 켜져 있는 브라우저 (끄지 않음. 안내만)
$procNames = [ordered]@{ msedge = '엣지'; chrome = '크롬'; whale = '웨일'; brave = '브레이브'; firefox = '파이어폭스'; claude = '클로드 앱' }
$running = New-Object System.Collections.Generic.List[string]
foreach ($pn in $procNames.Keys) {
    if (Get-Process -Name $pn -ErrorAction SilentlyContinue) { $running.Add($procNames[$pn]) }
}
if ($running.Count -gt 0) {
    Say (' 켜져 있는 브라우저: ' + ($running -join ', ') + '  (그대로 두어도 복사됩니다. 모두 닫고 실행하면 더 정확합니다)') 'DarkYellow'
}

# ---- [2] 브라우저별 복사
$browsersOut = New-Object System.Collections.Generic.List[object]
foreach ($t in $targets) {
    if (-not (Test-Dir $t.Root)) {
        Write-Log ('[' + $t.Name + '] 없음: ' + $t.Root)
        continue
    }
    Say ''
    Say ('[' + (Get-KoName $t.Name) + '] ' + $t.Root) 'Cyan'
    $bOut = [pscustomobject]@{ name = $t.Name; root = $t.Root; profiles = New-Object System.Collections.Generic.List[object] }
    $kind = $t.Kind
    $profDirs = @(Get-SubDirs $t.Root | Where-Object { $kind -eq 'partitions' -or $_.Name -eq 'Default' -or $_.Name -like 'Profile *' } | Sort-Object Name)
    if ($profDirs.Count -eq 0) { Say '  (프로필 없음)' 'DarkGray' }
    foreach ($pd in $profDirs) {
        $outRel = $t.Name + '\' + (Get-ShortName $pd.Name)
        Write-Log ('프로필 ' + $outRel + ' <- ' + (Strip-LP $pd.Full))
        $rec = Backup-ChromiumProfile -Name $pd.Name -ProfDir $pd.Full -OutRel $outRel
        $bOut.profiles.Add($rec)
        Show-ProfileLine $rec
    }
    $browsersOut.Add($bOut)
}

$ffOut = New-Object System.Collections.Generic.List[object]
if (Test-Dir $ffRoot) {
    Say ''
    Say ('[파이어폭스] ' + $ffRoot) 'Cyan'
    foreach ($pd in @(Get-SubDirs $ffRoot)) {
        $outRel = 'Firefox\' + (Get-ShortName $pd.Name)
        $rec = Backup-FirefoxProfile -Name $pd.Name -ProfDir $pd.Full -OutRel $outRel
        $ffOut.Add($rec)
        Show-ProfileLine $rec
    }
} else {
    Write-Log ('[Firefox] 없음: ' + $ffRoot)
}

# ---- [2b] ERP 가 브라우저 밖에 저장한 파일 (내보내기 JSON, 데이터 포함 HTML, 파일 핸들로 연결한 DB 파일)
#      원본은 읽기만 하고 '<실행폴더>\연결파일\' 로 복사. 이 백업 폴더와 저장소 폴더는 훑지 않음
Say ''
Say '[브라우저 밖 ERP 파일] 내보내기 파일·연결 파일 찾는 중...' 'Cyan'
# (a) IndexedDB 파일 핸들이 가리키던 파일 (있으면 그 폴더의 다른 ERP 파일도)
#     (주의: PowerShell 5.1 은 스크립트 맨 바깥의 @($script:목록) 에서 'Argument types do not match' 오류를 냄 → .ToArray())
foreach ($lref in $script:LinkedRefs.ToArray()) {
    Copy-LinkedFile $lref.path ('IndexedDB 파일 핸들 경로 (' + $lref.foundIn + ')')
    $par = $null
    try { $par = [System.IO.Path]::GetDirectoryName($lref.path) } catch { }
    if ($par -and (Test-Dir $par)) {
        foreach ($f in (Get-TreeFiles -Dir $par -DirectOnly).Files) {
            foreach ($pat in $LinkedNamePatterns) {
                if ($f.Name -like $pat) { Copy-LinkedFile $f.Full '파일 핸들 대상과 같은 폴더의 ERP 파일'; break }
            }
        }
    }
}
# (b) 이름 규칙으로 찾기: 다운로드 / 바탕화면 / 문서 / OneDrive / C:\MES (깊이 4단계까지)
$sweepCands = New-Object System.Collections.Generic.List[string]
if ($env:USERPROFILE) {
    foreach ($sub in @('Downloads', 'Desktop', 'Documents')) { $sweepCands.Add((Join-Path $env:USERPROFILE $sub)) }
}
foreach ($sf in @('Desktop', 'MyDocuments')) {
    try { $sweepCands.Add([Environment]::GetFolderPath($sf)) } catch { }
}
foreach ($od in @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer)) { if ($od) { $sweepCands.Add($od) } }
if ($env:USERPROFILE) {
    foreach ($od in @(Get-ChildItem -LiteralPath $env:USERPROFILE -Directory -Force -Filter 'OneDrive*' -ErrorAction SilentlyContinue)) { $sweepCands.Add($od.FullName) }
}
if ($env:SystemDrive) { $sweepCands.Add($env:SystemDrive + '\MES') }
$sweepCands.Add('C:\MES')
$sweepRoots = New-Object System.Collections.Generic.List[string]
$seenRoot = @{}
foreach ($sr in $sweepCands) {
    if (-not $sr) { continue }
    $k = $sr.TrimEnd('\').ToLowerInvariant()
    if ($seenRoot.ContainsKey($k)) { continue }
    $seenRoot[$k] = $true
    if (Test-Dir $sr) { $sweepRoots.Add($sr.TrimEnd('\')) }
}
foreach ($sr in $sweepRoots) { Search-LinkedFiles $sr $LinkedMaxDepth }
Write-Log ('브라우저 밖 ERP 파일: 훑은 폴더 ' + $script:SweepVisited.Count + '개, 복사 ' + $script:Linked.Count + '개, 못/안 한 것 ' + $script:LinkedSkipped.Count + '개')
if ($script:SweepTruncated) { Say ('  (폴더가 너무 많아 ' + $LinkedDirLimit + '개까지만 훑음)') 'DarkYellow' }
foreach ($l in $script:Linked) { Say ('  - 복사: ' + (Get-MaskedPath $l.source) + '  (' + (Format-Size $l.bytes) + ', ' + $l.modifiedLocal + ')') 'Green' }
foreach ($l in $script:LinkedSkipped) { Say ('  - 못/안 받음: ' + (Get-MaskedPath $l.source) + '  - ' + $l.reason) 'Yellow' }
if ($script:Linked.Count -eq 0 -and $script:LinkedSkipped.Count -eq 0) { Say '  찾은 파일 없음' }

# ---- [3] 합계 + 무결성 확인값 + manifest
$allRecs = New-Object System.Collections.Generic.List[object]
foreach ($b in $browsersOut) { foreach ($p in $b.profiles) { $allRecs.Add([pscustomobject]@{ label = ((Get-KoName $b.name) + '/' + (Get-KoName $p.name)); rec = $p }) } }
foreach ($p in $ffOut) { $allRecs.Add([pscustomobject]@{ label = ('파이어폭스/' + $p.name); rec = $p }) }

$totFiles = 0; $totBytes = [long]0; $totFailed = 0; $totSkipped = 0
$erpFound  = New-Object System.Collections.Generic.List[string]
$swFound   = New-Object System.Collections.Generic.List[string]
$httpFound = New-Object System.Collections.Generic.List[string]
$lanFound  = New-Object System.Collections.Generic.List[string]
foreach ($a in $allRecs) {
    $totFiles   += $a.rec.copied.Count
    $totBytes   += (Get-CopiedBytes $a.rec)
    $totFailed  += $a.rec.failed.Count
    $totSkipped += $a.rec.skipped.Count
    $ht = Get-HintText $a.rec
    if ($ht) { $erpFound.Add($a.label + ' (' + $ht + ')') }
    if ($a.rec.hints.erpSwCache) { $swFound.Add($a.label) }
    if ($a.rec.hints.httpCacheSupabase) { $httpFound.Add($a.label) }
    foreach ($lh in @($a.rec.hints.lanIdb) + @($a.rec.hints.lsLan)) {
        $mh = Get-MaskedHost $lh
        if (-not $lanFound.Contains($mh)) { $lanFound.Add($mh) }
    }
}

Say ''
Say '무결성 확인값 계산 중...'
$sumLines = New-Object System.Collections.Generic.List[string]
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$sumItems = New-Object System.Collections.Generic.List[string]
foreach ($a in $allRecs) { foreach ($c in $a.rec.copied) { $sumItems.Add($a.rec.dir + '\' + $c.relPath) } }
foreach ($l in $script:Linked) { $sumItems.Add($l.copiedAs) }
foreach ($rel in $sumItems) {
    $fs = $null
    try {
        $fs = [System.IO.FileStream]::new(($script:RunDirLP + '\' + $rel), [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
        $hash = [System.BitConverter]::ToString($sha256.ComputeHash($fs)).Replace('-', '').ToLowerInvariant()
        $sumLines.Add($hash + '  ' + $rel.Replace('\', '/'))
    } catch {
        Write-Log ('  SHA256 계산 실패: ' + $rel + ' / ' + (Get-InnerEx $_.Exception).Message)
    } finally {
        if ($fs) { $fs.Dispose() }
    }
}

$endTime = Get-Date
$manifest = [pscustomobject]@{
    format          = 'SEUNGJEONG_ERP_RAW_BROWSER_COPY'
    version         = 1
    computerName    = $env:COMPUTERNAME
    userName        = $env:USERNAME
    createdLocal    = $startTime.ToString("yyyy-MM-dd'T'HH:mm:sszzz", $Inv)
    finishedLocal   = $endTime.ToString("yyyy-MM-dd'T'HH:mm:sszzz", $Inv)
    psVersion       = $PSVersionTable.PSVersion.ToString()
    runFolder       = $runName
    layout          = '파일 위치 = <이 폴더>\<profiles[].dir>\<copied[].relPath>  (dir 는 보통 <브라우저>\<프로필>, 너무 긴 이름만 줄임)'
    patterns        = $ErpPatterns
    runningBrowsers = $running
    browsers        = $browsersOut
    firefox         = $ffOut
    erpHints        = $erpFound
    linkedFiles     = $script:Linked
    linkedSkipped   = $script:LinkedSkipped
    linkedRefs      = $script:LinkedRefs
    linkedSweep     = [pscustomobject]@{ roots = $sweepRoots; maxDepth = $LinkedMaxDepth; dirsVisited = $script:SweepVisited.Count; truncated = $script:SweepTruncated; namePatterns = $LinkedNamePatterns }
    totals          = [pscustomobject]@{ files = $totFiles; bytes = $totBytes; failed = $totFailed; skipped = $totSkipped; linkedFiles = $script:Linked.Count; linkedBytes = $script:LinkedBytes }
}
try {
    [System.IO.File]::WriteAllLines(($script:RunDirLP + '\SHA256SUMS.txt'), [string[]]$sumLines.ToArray(), $Utf8NoBom)
} catch { Say (' [주의] SHA256SUMS.txt 저장 실패: ' + (Get-InnerEx $_.Exception).Message) 'Yellow' }
try {
    $json = $manifest | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText(($script:RunDirLP + '\manifest.json'), $json, $Utf8NoBom)
} catch { Say (' [주의] manifest.json 저장 실패: ' + (Get-InnerEx $_.Exception).Message) 'Yellow' }

# ---- [4] 결과 요약
$watch.Stop()
$foundNames = New-Object System.Collections.Generic.List[string]
foreach ($b in $browsersOut) {
    $names = @($b.profiles | Where-Object { -not $_.duplicateOf } | ForEach-Object {
        $kn = Get-KoName $_.name; if ($kn.Length -gt 24) { $kn.Substring(0, 20) + '...' } else { $kn }
    })
    if ($names.Count -gt 0) {
        if ($names.Count -le 3) { $foundNames.Add((Get-KoName $b.name) + '(' + ($names -join ', ') + ')') }
        else { $foundNames.Add((Get-KoName $b.name) + '(' + $names.Count + '개)') }
    }
}
if ($ffOut.Count -gt 0) { $foundNames.Add('파이어폭스(' + $ffOut.Count + '개)') }

Say ''
Say '================================================================'
Say ' 결과 요약'
if ($foundNames.Count -gt 0) { Say ('   찾은 브라우저 : ' + ($foundNames -join ', ')) }
else { Say '   찾은 브라우저 : 없음' 'Yellow' }
if ($erpFound.Count -gt 0) {
    Say '   ERP 데이터    : 있을 가능성 높음' 'Green'
    foreach ($e in $erpFound) { Say ('                   - ' + $e) 'Green' }
} else {
    Say '   ERP 데이터    : 뚜렷한 흔적을 못 찾음 (그래도 복사본을 클로드에게 분석 요청하세요)' 'Yellow'
}
if ($swFound.Count -gt 0) { Say ('   ERP 앱 저장본      : 있음(옛 인터넷 DB 사본 가능) - ' + ($swFound -join ', ')) 'Green' }
else { Say '   ERP 앱 저장본      : 없음' }
if ($httpFound.Count -gt 0) {
    Say ('   임시 인터넷 파일   : 옛 인터넷 DB 흔적 있음 - 복사함 (' + ($httpFound -join ', ') + ')') 'Green'
    Say '                        (여기에는 다른 사이트에서 받은 페이지·그림도 섞여 있습니다)' 'Yellow'
} else {
    Say '   임시 인터넷 파일   : 옛 인터넷 DB 흔적 없음 (복사 안 함)'
}
if ($lanFound.Count -gt 0) { Say ('   회사 나스 주소     : ' + ($lanFound -join ', ') + ' 에 저장된 흔적 - 복사함 (ERP인지 나스 관리 화면인지는 분석 때 확인)') 'Green' }
if ($script:Linked.Count -gt 0 -or $script:LinkedSkipped.Count -gt 0) {
    $lcol = 'Green'
    if ($script:LinkedSkipped.Count -gt 0) { $lcol = 'Yellow' }
    Say ('   브라우저 밖 ERP 파일: {0}개 복사 ({1}) → 연결파일 폴더, 못/안 받은 파일 {2}개 (목록 파일 manifest.json 참고)' -f $script:Linked.Count, (Format-Size $script:LinkedBytes), $script:LinkedSkipped.Count) $lcol
} else {
    Say '   브라우저 밖 ERP 파일: 없음 (내보낸 파일·연결 파일을 못 찾음)'
}
Say ('   복사          : 파일 {0}개, 총 {1}  (걸린 시간 {2:N0}초)' -f $totFiles, (Format-Size $totBytes), $watch.Elapsed.TotalSeconds)
if ($totFailed -gt 0) { Say ('   실패          : {0}개  (목록 파일 manifest.json 참고)' -f $totFailed) 'Yellow' }
else { Say '   실패          : 0개' }
Say ('   저장 폴더     : ' + $script:RunDir)
Say ''
Say ' ※ 이 폴더에는 다른 사이트 로그인 정보도 들어 있습니다.' 'Yellow'
Say '    인터넷이나 클라우드(원드라이브 포함)에 절대 올리지 마세요.' 'Yellow'
Say ' ※ USB 또는 회사 나스 관리자 폴더에만 보관하세요.' 'Yellow'
Say ' ※ 클로드에게 "이 폴더 분석해줘" 라고 하면 됩니다.'
Say '================================================================'

try {
    [System.IO.File]::WriteAllLines(($script:RunDirLP + '\backup-log.txt'), [string[]]$script:LogLines.ToArray(), $Utf8NoBom)
} catch { }

if (-not $NoExplorer) {
    try { Start-Process -FilePath 'explorer.exe' -ArgumentList ('"' + $script:RunDir + '"') } catch { }
}
if (($totFiles + $script:Linked.Count) -eq 0) { exit 1 }
exit 0

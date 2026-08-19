<#
.SYNOPSIS
    Yayın öncesi kapsamlı kalite kontrolü / Pre-release quality gate.

.DESCRIPTION
    Tek komutla tüm kalite kapılarını çalıştırır:
      Backend lint / type check / test
      Frontend lint / type check / build
      Veritabanı migration doğrulaması
      Çeviri bütünlüğü
      Yedekleme dumanı testi
      Gizli anahtar (secret) taraması
      Git durumu

    Sonuçlar PASS / FAIL / WARNING olarak özetlenir.

.EXAMPLE
    .\scripts\final_check.ps1
    .\scripts\final_check.ps1 -SkipFrontend
#>
[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$results = [System.Collections.ArrayList]::new()

function Add-Result {
    param(
        [string]$Name,
        [ValidateSet('PASS', 'FAIL', 'WARNING', 'SKIPPED')][string]$Status,
        [string]$Detail = ''
    )
    [void]$results.Add([pscustomobject]@{ Check = $Name; Status = $Status; Detail = $Detail })
    $color = switch ($Status) {
        'PASS'    { 'Green' }
        'FAIL'    { 'Red' }
        'WARNING' { 'Yellow' }
        default   { 'DarkGray' }
    }
    $symbol = switch ($Status) {
        'PASS'    { '[+]' }
        'FAIL'    { '[X]' }
        'WARNING' { '[!]' }
        default   { '[-]' }
    }
    Write-Host ("  {0} {1,-34} {2}" -f $symbol, $Name, $Detail) -ForegroundColor $color
}

function Write-Section {
    param([string]$Title)
    Write-Host ''
    Write-Host "  --- $Title " -NoNewline -ForegroundColor Cyan
    Write-Host ('-' * [Math]::Max(0, 52 - $Title.Length)) -ForegroundColor Cyan
}

Write-Host ''
Write-Host '  ==============================================================' -ForegroundColor Cyan
Write-Host '    YAYIN ONCESI KALITE KONTROLU / RELEASE READINESS CHECK' -ForegroundColor Cyan
Write-Host '  ==============================================================' -ForegroundColor Cyan

# ===========================================================================
Write-Section 'ORTAM'
# ===========================================================================
if (Test-Path $python) {
    $pyVersion = (& $python --version 2>&1) -join ''
    Add-Result 'Python sanal ortami' 'PASS' $pyVersion
} else {
    Add-Result 'Python sanal ortami' 'FAIL' 'bulunamadi'
    Write-Host ''
    Write-Host '  Sanal ortam olmadan devam edilemez.' -ForegroundColor Red
    exit 1
}

if (Test-Path (Join-Path $root '.env')) {
    Add-Result '.env dosyasi' 'PASS' 'mevcut'
} else {
    Add-Result '.env dosyasi' 'WARNING' 'yok (.env.example kopyalanmali)'
}

# ===========================================================================
Write-Section 'BACKEND'
# ===========================================================================
Push-Location (Join-Path $root 'backend')

# Lint
$ruffOutput = & $python -m ruff check . 2>&1
if ($LASTEXITCODE -eq 0) {
    Add-Result 'Backend lint (ruff)' 'PASS'
} else {
    $issueCount = ($ruffOutput | Select-String -Pattern '^\s*\S+:\d+:\d+:' ).Count
    Add-Result 'Backend lint (ruff)' 'WARNING' "$issueCount uyari"
}

# Format
& $python -m black --check . 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Add-Result 'Backend bicim (black)' 'PASS'
} else {
    Add-Result 'Backend bicim (black)' 'WARNING' 'bicimlendirme onerileri var'
}

# Type check
$mypyOutput = & $python -m mypy app --ignore-missing-imports --no-error-summary 2>&1
if ($LASTEXITCODE -eq 0) {
    Add-Result 'Backend tip denetimi (mypy)' 'PASS'
} else {
    $errorCount = ($mypyOutput | Select-String -Pattern ': error:').Count
    Add-Result 'Backend tip denetimi (mypy)' 'WARNING' "$errorCount not"
}

# Tests
if ($SkipTests) {
    Add-Result 'Backend testleri' 'SKIPPED'
} else {
    $testOutput = & $python -m pytest tests -q --no-header -p no:cacheprovider 2>&1
    $summary = ($testOutput | Select-String -Pattern '\d+ (passed|failed)' | Select-Object -Last 1)
    if ($LASTEXITCODE -eq 0) {
        Add-Result 'Backend testleri (pytest)' 'PASS' ($summary -replace '\s+', ' ')
    } else {
        Add-Result 'Backend testleri (pytest)' 'FAIL' ($summary -replace '\s+', ' ')
    }
}

# Migration
& $python -m alembic upgrade head 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    $current = (& $python -m alembic current 2>&1 | Select-String -Pattern '\(head\)') -join ''
    Add-Result 'Veritabani migration' 'PASS' ($current -replace '\s+', ' ')
} else {
    Add-Result 'Veritabani migration' 'FAIL'
}

# Migration ile model uyumu (yeni degisiklik unutulmus mu?)
$autogen = & $python -m alembic check 2>&1
if ($LASTEXITCODE -eq 0) {
    Add-Result 'Model/migration uyumu' 'PASS' 'senkron'
} else {
    Add-Result 'Model/migration uyumu' 'WARNING' 'yeni migration gerekebilir'
}

# Ceviri butunlugu
# Not: PowerShell here-string'i `python -c` argumanina gecerken tirnaklari
# kaybediyor; bu yuzden gecici bir .py dosyasina yazip oyle calistiriyoruz.
$i18nScript = Join-Path $env:TEMP 'sws_i18n_check.py'
@'
import sys
sys.path.insert(0, ".")
from app.core.i18n import missing_translations, MESSAGES
missing = missing_translations()
total = sum(len(v) for v in missing.values())
print(f"{len(MESSAGES)} anahtar, {total} eksik")
sys.exit(1 if total else 0)
'@ | Set-Content -Path $i18nScript -Encoding utf8
$i18nCheck = & $python $i18nScript 2>&1
Remove-Item $i18nScript -ErrorAction SilentlyContinue
if ($LASTEXITCODE -eq 0) {
    Add-Result 'Backend ceviri butunlugu' 'PASS' ($i18nCheck -join '')
} else {
    Add-Result 'Backend ceviri butunlugu' 'FAIL' ($i18nCheck -join '')
}

# Yedekleme dumani testi
$backupScript = Join-Path $env:TEMP 'sws_backup_check.py'
@'
import sys
sys.path.insert(0, ".")
from app.db.session import SessionLocal
from app.services.backup import create_backup, verify_backup
from app.models.enums import BackupType
try:
    with SessionLocal() as db:
        record = create_backup(db, backup_type=BackupType.MANUAL, note="final_check")
        result = verify_backup(db, record.backup_id)
        status = "OK" if result["is_valid"] else "BASARISIZ"
        checks = len(result["checks"])
        print(f"{record.size_mb} MB, {checks} kontrol, dogrulama: {status}")
        sys.exit(0 if result["is_valid"] else 1)
except Exception as exc:
    print(f"{type(exc).__name__}: {exc}")
    sys.exit(1)
'@ | Set-Content -Path $backupScript -Encoding utf8
$backupCheck = & $python $backupScript 2>&1
Remove-Item $backupScript -ErrorAction SilentlyContinue
if ($LASTEXITCODE -eq 0) {
    Add-Result 'Yedekleme + dogrulama' 'PASS' ($backupCheck -join '')
} else {
    Add-Result 'Yedekleme + dogrulama' 'FAIL' ($backupCheck -join '')
}

Pop-Location

# ===========================================================================
Write-Section 'FRONTEND'
# ===========================================================================
$frontendPath = Join-Path $root 'frontend'
if ($SkipFrontend) {
    Add-Result 'Frontend kontrolleri' 'SKIPPED'
} elseif (-not (Test-Path (Join-Path $frontendPath 'node_modules'))) {
    Add-Result 'Frontend bagimliliklari' 'WARNING' 'node_modules yok (npm install)'
} else {
    Push-Location $frontendPath

    npm run typecheck --silent 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Add-Result 'Frontend tip denetimi (tsc)' 'PASS'
    } else {
        Add-Result 'Frontend tip denetimi (tsc)' 'FAIL'
    }

    npm run lint --silent 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Add-Result 'Frontend lint (eslint)' 'PASS'
    } else {
        Add-Result 'Frontend lint (eslint)' 'WARNING' 'uyarilar var'
    }

    npm run build --silent 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $distPath = Join-Path $frontendPath 'dist'
        if (Test-Path $distPath) {
            $sizeMb = [Math]::Round((Get-ChildItem $distPath -Recurse -File |
                Measure-Object -Property Length -Sum).Sum / 1MB, 2)
            Add-Result 'Frontend derleme (vite build)' 'PASS' "$sizeMb MB"
        } else {
            Add-Result 'Frontend derleme (vite build)' 'PASS'
        }
    } else {
        Add-Result 'Frontend derleme (vite build)' 'FAIL'
    }

    # Ceviri anahtar karsilastirmasi
    $i18nDiff = node -e @'
const fs = require('fs');
const flat = (obj, prefix = '') => Object.entries(obj).flatMap(([k, v]) =>
  v && typeof v === 'object' ? flat(v, prefix + k + '.') : [prefix + k]);
const tr = flat(JSON.parse(fs.readFileSync('src/locales/tr/translation.json', 'utf8')));
const en = flat(JSON.parse(fs.readFileSync('src/locales/en/translation.json', 'utf8')));
const missingEn = tr.filter(k => !en.includes(k));
const missingTr = en.filter(k => !tr.includes(k));
console.log(`${tr.length} TR / ${en.length} EN anahtar, eksik: TR=${missingTr.length} EN=${missingEn.length}`);
if (missingEn.length) console.log('EN eksik: ' + missingEn.slice(0, 10).join(', '));
if (missingTr.length) console.log('TR eksik: ' + missingTr.slice(0, 10).join(', '));
process.exit(missingEn.length + missingTr.length ? 1 : 0);
'@ 2>&1
    if ($LASTEXITCODE -eq 0) {
        Add-Result 'Frontend ceviri butunlugu' 'PASS' (($i18nDiff -join ' ') -replace '\s+', ' ')
    } else {
        Add-Result 'Frontend ceviri butunlugu' 'FAIL' (($i18nDiff -join ' ') -replace '\s+', ' ')
    }

    Pop-Location
}

# ===========================================================================
Write-Section 'GUVENLIK'
# ===========================================================================

# .env git tarafindan yok sayiliyor mu?
$gitignore = Get-Content (Join-Path $root '.gitignore') -Raw -ErrorAction SilentlyContinue
if ($gitignore -and $gitignore -match '(?m)^\.env\s*$') {
    Add-Result '.env gitignore icinde' 'PASS'
} else {
    Add-Result '.env gitignore icinde' 'FAIL' 'SIR SIZINTISI RISKI'
}

# Git index'inde sir dosyasi var mi?
Push-Location $root
$tracked = git ls-files 2>$null
if ($LASTEXITCODE -eq 0) {
    $secretPatterns = @('\.env$', '\.key$', '\.pem$', 'credentials', 'secrets\.', 'token.*\.json$')
    $trackedSecrets = @()
    foreach ($pattern in $secretPatterns) {
        $trackedSecrets += $tracked | Where-Object { $_ -match $pattern -and $_ -notmatch '\.env\.example$' }
    }
    if ($trackedSecrets.Count -eq 0) {
        Add-Result 'Git izlenen sir dosyasi' 'PASS' 'temiz'
    } else {
        Add-Result 'Git izlenen sir dosyasi' 'FAIL' ($trackedSecrets -join ', ')
    }
} else {
    Add-Result 'Git izlenen sir dosyasi' 'SKIPPED' 'git deposu degil'
}

# Kaynak kodda gomulu sir taramasi
$scanPaths = @('backend\app', 'frontend\src', 'scripts', 'desktop', 'docs')
$secretRegexes = @(
    @{ Name = 'NVIDIA API anahtari'; Pattern = 'nvapi-[A-Za-z0-9_\-]{20,}' },
    @{ Name = 'OpenAI API anahtari';  Pattern = 'sk-[A-Za-z0-9]{32,}' },
    @{ Name = 'GitHub token';         Pattern = 'gh[pousr]_[A-Za-z0-9]{30,}' },
    @{ Name = 'AWS erisim anahtari';  Pattern = 'AKIA[0-9A-Z]{16}' },
    @{ Name = 'Ozel anahtar blogu';   Pattern = 'BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY' }
)
$foundSecrets = @()
foreach ($scanPath in $scanPaths) {
    $full = Join-Path $root $scanPath
    if (-not (Test-Path $full)) { continue }
    foreach ($regex in $secretRegexes) {
        $hits = Get-ChildItem $full -Recurse -File -Include *.py, *.ts, *.tsx, *.js, *.json, *.md, *.ps1, *.bat -ErrorAction SilentlyContinue |
            Select-String -Pattern $regex.Pattern -ErrorAction SilentlyContinue
        foreach ($hit in $hits) {
            $foundSecrets += "$($regex.Name): $($hit.Filename):$($hit.LineNumber)"
        }
    }
}
if ($foundSecrets.Count -eq 0) {
    Add-Result 'Kaynak kodda sir taramasi' 'PASS' 'bulunamadi'
} else {
    Add-Result 'Kaynak kodda sir taramasi' 'FAIL' ($foundSecrets -join '; ')
}

# .env icerigi commit edilmemis mi (calisma agacinda degisiklik)
$gitStatus = git status --porcelain 2>$null
if ($LASTEXITCODE -eq 0) {
    if ([string]::IsNullOrWhiteSpace($gitStatus)) {
        Add-Result 'Git calisma agaci' 'PASS' 'temiz'
    } else {
        $changeCount = ($gitStatus -split "`n" | Where-Object { $_ }).Count
        Add-Result 'Git calisma agaci' 'WARNING' "$changeCount degisiklik commit bekliyor"
    }
} else {
    Add-Result 'Git calisma agaci' 'SKIPPED' 'git deposu degil'
}

# Bagimlilik guvenlik taramasi
$auditOutput = & $python -m pip_audit --skip-editable --progress-spinner off 2>&1
if ($LASTEXITCODE -eq 0) {
    Add-Result 'Bagimlilik guvenligi (pip-audit)' 'PASS' 'bilinen acik yok'
} else {
    $vulnCount = ($auditOutput | Select-String -Pattern 'GHSA-|PYSEC-').Count
    if ($vulnCount -gt 0) {
        Add-Result 'Bagimlilik guvenligi (pip-audit)' 'WARNING' "$vulnCount bulgu"
    } else {
        Add-Result 'Bagimlilik guvenligi (pip-audit)' 'WARNING' 'calistirilamadi'
    }
}
Pop-Location

# ===========================================================================
Write-Section 'DOKUMANTASYON'
# ===========================================================================
$requiredDocs = @(
    'README.md', 'CHANGELOG.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', '.env.example',
    'docs\ARCHITECTURE.md', 'docs\DATABASE.md', 'docs\API.md', 'docs\AI_ARCHITECTURE.md',
    'docs\LOCAL_AI.md', 'docs\NVIDIA_AI.md', 'docs\SECURITY.md', 'docs\DEVELOPER_AGENT.md',
    'docs\OPEN_SOURCE_RESEARCH.md', 'docs\ROADMAP.md',
    'docs\USER_GUIDE_TR.md', 'docs\USER_GUIDE_EN.md',
    'docs\ADMIN_GUIDE_TR.md', 'docs\ADMIN_GUIDE_EN.md',
    'docs\AI_GUIDE_TR.md', 'docs\AI_GUIDE_EN.md',
    'docs\BACKUP_RESTORE_TR.md', 'docs\BACKUP_RESTORE_EN.md',
    'docs\STATISTICS_GUIDE_TR.md', 'docs\STATISTICS_GUIDE_EN.md'
)
$missingDocs = $requiredDocs | Where-Object { -not (Test-Path (Join-Path $root $_)) }
if ($missingDocs.Count -eq 0) {
    Add-Result 'Dokumantasyon dosyalari' 'PASS' "$($requiredDocs.Count) dosya tam"
} else {
    Add-Result 'Dokumantasyon dosyalari' 'FAIL' ("eksik: " + ($missingDocs -join ', '))
}

# ===========================================================================
# Ozet
# ===========================================================================
$passCount    = @($results | Where-Object Status -eq 'PASS').Count
$failCount    = @($results | Where-Object Status -eq 'FAIL').Count
$warnCount    = @($results | Where-Object Status -eq 'WARNING').Count
$skipCount    = @($results | Where-Object Status -eq 'SKIPPED').Count

Write-Host ''
Write-Host '  ==============================================================' -ForegroundColor Cyan
Write-Host ("    SONUC:  PASS {0}   FAIL {1}   WARNING {2}   SKIPPED {3}" -f `
    $passCount, $failCount, $warnCount, $skipCount) -ForegroundColor Cyan
Write-Host '  ==============================================================' -ForegroundColor Cyan

if ($failCount -gt 0) {
    Write-Host ''
    Write-Host '  BASARISIZ KONTROLLER:' -ForegroundColor Red
    $results | Where-Object Status -eq 'FAIL' | ForEach-Object {
        Write-Host ("    - {0}: {1}" -f $_.Check, $_.Detail) -ForegroundColor Red
    }
    Write-Host ''
    Write-Host '  Yayina HAZIR DEGIL. Once bu sorunlari giderin.' -ForegroundColor Red
    Write-Host ''
    exit 1
}

Write-Host ''
if ($warnCount -gt 0) {
    Write-Host '  Yayina hazir (uyarilar gozden gecirilmeli).' -ForegroundColor Yellow
} else {
    Write-Host '  Tum kontroller basarili. Yayina hazir.' -ForegroundColor Green
}
Write-Host ''
exit 0

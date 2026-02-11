# === Ajustes ===
$portName = "COM5"        # mude se necessário (ex.: COM3, COM4...)
$baud     = 9600
$outCsv   = "C:\Users\Public\hipot_parsed.csv"

# >>> API (NOVO)
$apiBase  = "http://127.0.0.1:5000"
$apiUrl   = "$apiBase/producao/gp/hipot/api/result"
$serialTxt = "C:\Users\Public\hipot_serial.txt"
$adminPin  = ""                 # se usar PIN nas APIs, coloque aqui; caso contrário, deixe vazio
$maxRetries = 3
$retryBaseMs = 700
$alsoWriteCsvOnSuccess = $false # se quiser também registrar no CSV mesmo quando o POST der certo

# === Porta serial ===
$port = New-Object System.IO.Ports.SerialPort $portName, $baud, 'None', 8, 'One'
$port.NewLine = "`n"
$port.ReadTimeout = 500

# >>> Helpers (NOVO)
function Get-NowIso() {
  return (Get-Date).ToUniversalTime().ToString("s") + "Z"
}

function Resolve-Serial([string[]]$lines) {
  # 1) Variável de ambiente
  if ($env:HIPOT_SERIAL -and $env:HIPOT_SERIAL -match '^\d{3,}$') { return $env:HIPOT_SERIAL }
  # 2) Arquivo txt (uma linha com o serial)
  if (Test-Path $serialTxt) {
    $txt = (Get-Content $serialTxt -ErrorAction SilentlyContinue | Select-Object -Last 1).Trim()
    if ($txt -and $txt -match '^\d{3,}$') { return $txt }
  }
  # 3) Extração do texto das linhas (padrões comuns: "Serial:", "SN:", "N=")
  $blob = ($lines -join ' ')
  if ($blob -match '(?:Serial|S(?:er)?N|^N)\s*[:=]?\s*(\d{3,})\b') { return $Matches[1] }
  return $null
}

function Post-Result($payload) {
  $headers = @{}
  if ($adminPin) { $headers['X-Admin-PIN'] = $adminPin }
  for ($i=0; $i -lt $maxRetries; $i++) {
    try {
      $json = $payload | ConvertTo-Json -Depth 6
      $resp = Invoke-RestMethod -Uri $apiUrl -Method POST -ContentType "application/json" -Headers $headers -Body $json
      return @{ ok = $true; response = $resp }
    } catch {
      $delay = [int]($retryBaseMs * [math]::Pow(1.6, $i))
      Start-Sleep -Milliseconds $delay
      if ($i -eq ($maxRetries-1)) { return @{ ok = $false; error = $_.Exception.Message } }
    }
  }
}

# === Parser de etiquetas EPL ===
function Parse-EPLLabel($lines) {
  # Extrai o texto entre aspas das linhas A... (ignora coordenadas)
  $txt = @()
  foreach ($ln in $lines) {
    if ($ln -match '^A\d+,.+,"(.*)"$') {
      $txt += ($Matches[1] -replace '\r','')
    }
  }

  # Junta tudo em uma string para casar padrões que podem quebrar linha
  $blob = ($txt -join ' ') -replace '\s+',' '

  # Também guardamos as linhas limpas (p/ data/hora/status/etc.)
  $tlin = $txt | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }

  # Campos com defaults
  $date=""; $time=""; $teste=""; $hp_v=""; $hp_i=""; $gb_i=""; $gb_r="";
  $tf_v=""; $tf_i=""; $p_ap=""; $p_at=""; $status=""

  # Passada linha a linha
  foreach ($t in $tlin) {
    if (-not $date  -and $t -match '^\d{2}/\d{2}/\d{2}$')                           { $date = $t; continue }
    if (-not $time  -and $t -match '^\d{2}:\d{2}:\d{2}$')                           { $time = $t; continue }
    if (-not $teste -and $t -match 'SEGURAN[ÇC]A|ENTRAN|ENTRADA|SA[IÍ]DA')          { $teste = $t; continue }
    if (-not $status -and $t -match '^(OK|REP|APR)$')                                { $status = $Matches[1]; continue }

    # GB (versão robusta): aceita "Resistência/Resistencia/Resist?ncia" e várias unidades
    if (-not $gb_r -and $t -match 'Corrente[: ]*\s*([\d.,]+)\s*A\s*@\s*Resist\S*\s*[: ]*\s*(\d+)\s*(?:mR|mOHMNS|mΩ|mOhm|mO)') {
      $gb_i = ($Matches[1] -replace ',','.')
      $gb_r = $Matches[2]
      continue
    }
  }

  # --- HP (aceita “Tensão/Tensao/Tens?o”, vírgula ou ponto) ---
  if ($blob -match 'Tens[aã\?]o[: ]*\s*(\d+(?:[.,]\d+)?)\s*V\s*@\s*Corrente[: ]*\s*([\d.,]+)\s*mA') {
    $hp_v = ($Matches[1] -replace ',','.')
    $hp_i = ($Matches[2] -replace ',','.')
  }

  # --- TF ---
  if ($blob -match 'Tens[aã\?]o[: ]*\s*([\d.,]+)\s*V\s*@\s*Corren(?:te)?[: ]*\s*([\d.,]+)\s*A') {
    $tf_v = ($Matches[1] -replace ',','.')
    $tf_i = ($Matches[2] -replace ',','.')
  }

  # --- Potências ---
  if ($blob -match 'P\s*aparente[: ]*\s*([\d\s]+)\s*W\s*@\s*P\s*ativa[: ]*\s*([\d\s]+)\s*VA') {
    $p_ap = ($Matches[1].Trim() -replace '\s+','')
    $p_at = ($Matches[2].Trim() -replace '\s+','')
  }

  # --- GB fallback (mesmo padrão robusto no blob contínuo) ---
  if (-not $gb_r) {
    if ($blob -match 'Corrente[: ]*\s*([\d.,]+)\s*A\s*@\s*Resist\S*\s*[: ]*\s*(\d+)\s*(?:mR|mOHMNS|mΩ|mOhm|mO)') {
      $gb_i = ($Matches[1] -replace ',','.')
      $gb_r = $Matches[2]
    } elseif ($blob -match 'Resist\S*\s*[: ]*\s*(\d+)\s*(?:mR|mOHMNS|mΩ|mOhm|mO)') {
      # Caso venha só a resistência (sem a corrente)
      $gb_r = $Matches[1]
    }
  }

  # --- Status: aceita APR/APROVADO além de OK/REP ---
  if (-not $status) {
    if     ($blob -match 'APROV')  { $status = 'APR' }
    elseif ($blob -match 'REPROV') { $status = 'REP' }
  }

  # --- DEBUG amigável se ainda faltar algo ---
  if (-not $gb_r -or -not $status) {
    Write-Host "---- DEBUG (texto bruto detectado na etiqueta) ----"
    $txt | ForEach-Object { Write-Host $_ }
    Write-Host "----------------------------------------------------"
  }

  [PSCustomObject]@{
    Date = $date; Time = $time; Teste = $teste
    HP_V = $hp_v; HP_I_mA = $hp_i
    GB_I_A = $gb_i; GB_R_mOhms = $gb_r
    TF_V = $tf_v; TF_I_A = $tf_i
    P_aparente_W = $p_ap; P_ativa_VA = $p_at
    Status = $status
  }
}

try {
  $port.Open()
  Write-Host "Escutando $portName e parseando etiquetas EPL -> $outCsv (CTRL+C para parar)"

  # CSV: cria cabeçalho se não existir
  if (-not (Test-Path $outCsv)) {
    "Date;Time;Teste;HP_V;HP_I_mA;GB_I_A;GB_R_mOhms;TF_V;TF_I_A;P_aparente_W;P_ativa_VA;Status" | Out-File -Encoding UTF8 $outCsv
  }

  # Buffer da etiqueta (linhas entre 'N' e 'P1')
  $buf = New-Object System.Collections.Generic.List[string]

  while ($true) {
    try {
      $line = $port.ReadLine()
      if (-not $line) { continue }
      $line = $line.TrimEnd("`r")

      # Coleta linhas; etiqueta começa com 'N' e termina em 'P1'
      if ($line -eq 'N') { $buf.Clear() | Out-Null }
      $buf.Add($line) | Out-Null

      if ($line -eq 'P1') {
        $rec = Parse-EPLLabel $buf

        # Mostra resumo no console
        "{0} {1} | HP {2}V {3}mA | GB {4}A {5}mΩ | TF {6}V {7}A | P {8}W/{9}VA | {10}" -f `
          $rec.Date,$rec.Time,$rec.HP_V,$rec.HP_I_mA,$rec.GB_I_A,$rec.GB_R_mOhms,$rec.TF_V,$rec.TF_I_A,$rec.P_aparente_W,$rec.P_ativa_VA,($rec.Status)

        # >>> RESOLVE SERIAL (NOVO)
        $serial = Resolve-Serial $buf

        # >>> Monta payload e tenta POST (NOVO)
        $payload = @{
          serial      = $serial
          status      = $rec.Status            # APR | OK | REP
          received_at = Get-NowIso
          # campos opcionais para auditoria
          HP_V          = $rec.HP_V
          HP_I_mA       = $rec.HP_I_mA
          GB_I_A        = $rec.GB_I_A
          GB_R_mOhms    = $rec.GB_R_mOhms
          TF_V          = $rec.TF_V
          TF_I_A        = $rec.TF_I_A
          P_aparente_W  = $rec.P_aparente_W
          P_ativa_VA    = $rec.P_ativa_VA
          raw           = ($buf -join "`n")
        }

        $shouldFallback = $false
        if (-not $payload.serial) { Write-Host "AVISO: Serial não identificado."; $shouldFallback = $true }
        if (-not $payload.status) { Write-Host "AVISO: Status não identificado."; $shouldFallback = $true }

        if (-not $shouldFallback) {
          $res = Post-Result $payload
          if ($res.ok) {
            Write-Host "OK → POST $($payload.serial) / $($payload.status)"
            if ($alsoWriteCsvOnSuccess) {
              ($rec.PSObject.Properties | ForEach-Object Value) -join ';' | Add-Content -Encoding UTF8 $outCsv
            }
          } else {
            Write-Host "ERRO POST: $($res.error). Salvando fallback no CSV."
            ($rec.PSObject.Properties | ForEach-Object Value) -join ';' | Add-Content -Encoding UTF8 $outCsv
          }
        } else {
          # Falta serial ou status → fallback no CSV
          ($rec.PSObject.Properties | ForEach-Object Value) -join ';' | Add-Content -Encoding UTF8 $outCsv
        }

        $buf.Clear() | Out-Null
      }
    } catch {
      # timeouts de leitura são normais; só continua
    }
  }
}
finally {
  if ($port.IsOpen) { $port.Close() }
}

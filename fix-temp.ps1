$dir = 'D:\My\self_dev\Educonnect\frontend\src\temp'
Get-ChildItem $dir -Filter *.ts | ForEach-Object {
  $p = $_.FullName
  $c = Get-Content $p -Raw
  $s = $c -replace '[^\x00-\x7F]', ''
  $s = $s -replace '(?m)^\s*\{\s*$', ''
  $s = $s -replace ',{2,}', ','
  Set-Content $p $s -NoNewline -Encoding utf8
  Write-Output ($_.Name + ' fixed')
}
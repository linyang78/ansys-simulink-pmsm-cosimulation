param()

$python = 'C:\Env\miniconda3\envs\pmsm\python.exe'
$script = Join-Path $PSScriptRoot 'maxwell_ece.py'
& $python $script @args
exit $LASTEXITCODE

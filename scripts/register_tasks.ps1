# Registers the CryptoAcademy scheduled tasks (user-level, no admin needed).
# Re-runnable: /F overwrites existing definitions.

$py = "C:\CryptoAcademy\.venv\Scripts\pythonw.exe"

schtasks /Create /F /TN "CryptoAcademy\NewsCollector" `
  /TR "`"$py`" -m cryptoacademy collect" `
  /SC MINUTE /MO 10

schtasks /Create /F /TN "CryptoAcademy\OpenInterestArchiver" `
  /TR "`"$py`" -m cryptoacademy archive-oi" `
  /SC HOURLY /MO 1

schtasks /Query /TN "CryptoAcademy\NewsCollector" /V /FO LIST | Select-String "Task To Run|Schedule Type|Repeat: Every"

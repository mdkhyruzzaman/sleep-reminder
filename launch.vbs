' Silent 1-Click Launcher for Sleep Reminder
' Automatically enables Windows autostart on first run so it runs every time laptop boots up!
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 1. Determine Python executable (prefer .venv pythonw, then system pythonw)
venvPython = strDir & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(venvPython) Then
    pythonExe = venvPython
Else
    pythonExe = "pythonw.exe"
End If

' 2. Check if arguments passed (e.g. --minimized)
args = ""
For i = 0 to WScript.Arguments.Count - 1
    args = args & " " & WScript.Arguments(i)
Next

' 3. Automatically ensure autostart on Windows boot is active
regKey = "HKCU\Software\Microsoft\Windows\CurrentVersion\Run\SleepReminderApp"
runCmd = "wscript.exe """ & strDir & "\launch.vbs"" --minimized"
On Error Resume Next
WshShell.RegWrite regKey, runCmd, "REG_SZ"
On Error Goto 0

' 4. Launch Sleep Reminder silently (window style 0 = completely hidden console)
WshShell.CurrentDirectory = strDir
cmd = """" & pythonExe & """ """ & strDir & "\main.py""" & args
WshShell.Run cmd, 0, False

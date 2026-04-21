' OrgScan Launcher
' Double-click this file to start OrgScan.
' A minimized window will appear in your taskbar -- close it to stop the server.

Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

batPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\launch.bat"

' 2 = SW_SHOWMINIMIZED (starts minimized in taskbar, does not steal focus)
shell.Run "cmd /k """ & batPath & """", 2, False

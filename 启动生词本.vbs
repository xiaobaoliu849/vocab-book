Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory of the current script
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Set the working directory to the script's location
WshShell.CurrentDirectory = strPath

' Run the application using pythonw (no console window)
WshShell.Run "pythonw app.pyw", 0, False
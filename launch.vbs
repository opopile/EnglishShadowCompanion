Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\35439\.gemini\antigravity\scratch\type_english_companion"
cmd = """C:\Users\35439\AppData\Local\Programs\Python\Python312\python.exe"" ""C:\Users\35439\.gemini\antigravity\scratch\type_english_companion\main.py"""
WshShell.Run cmd, 0, False

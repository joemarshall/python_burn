from pathlib import Path

def fix_line_endings(directory_name):
    for f in Path(directory_name).glob("**/*"):
        ext=f.suffix
        if ext in [".sh",".py",".local"] or f.name in [".gitattributes","authorized_keys"]:
            bytes=f.read_bytes()
            if bytes.find(b"\r\n")!=-1:
                text=f.read_text()
                print("Fixing line endings:",f)
                f.write_text(text,newline="\n")
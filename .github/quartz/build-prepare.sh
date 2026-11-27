#!/usr/bin/env bash
set -e

NOTES_DIR="$1"
QUARTZ_DIR="$2"

if [ -z "$NOTES_DIR" ] || [ -z "$QUARTZ_DIR" ]; then
    echo "Error: Missing arguments. Usage: bash build-prepare.sh <notes-dir> <quartz-dir>"
    exit 1
fi

echo "Step 1/5: Cleaning old content..."
rm -rf "$QUARTZ_DIR/content/"*

echo "Step 2/5: Copying configs, styles, and icon..."
cp "$NOTES_DIR/.github/quartz/"*.ts "$QUARTZ_DIR/"
if [ -f "$NOTES_DIR/.github/quartz/custom.scss" ]; then
    git -C "$QUARTZ_DIR" checkout quartz/styles/custom.scss 2>/dev/null || true
    echo "" >> "$QUARTZ_DIR/quartz/styles/custom.scss"
    cat "$NOTES_DIR/.github/quartz/custom.scss" >> "$QUARTZ_DIR/quartz/styles/custom.scss"
fi
if [ -f "$NOTES_DIR/.github/quartz/icon.png" ]; then
    cp "$NOTES_DIR/.github/quartz/icon.png" "$QUARTZ_DIR/quartz/static/icon.png"
fi

echo "Step 3/5: Copying notes and meta-files..."
find "$NOTES_DIR" -maxdepth 1 -type d -name "*sem*" -exec cp -r {} "$QUARTZ_DIR/content/" \;

if [ -f "$NOTES_DIR/_index.md" ]; then
    cp "$NOTES_DIR/_index.md" "$QUARTZ_DIR/content/index.md"
else
    echo "Warning: _index.md not found in the root. Site homepage will be empty."
fi

if [ -f "$NOTES_DIR/README.md" ]; then
    cp "$NOTES_DIR/README.md" "$QUARTZ_DIR/content/README.md"
fi

if [ -f "$NOTES_DIR/CONTRIBUTING.md" ]; then
    cp "$NOTES_DIR/CONTRIBUTING.md" "$QUARTZ_DIR/content/CONTRIBUTING.md"
fi

find "$QUARTZ_DIR/content" -type f -name "_index.md" -print0 | while IFS= read -r -d '' file; do
    mv "$file" "${file%_index.md}index.md"
done

echo "Step 4/5: Generating index.md metadata..."
find "$QUARTZ_DIR/content" -mindepth 1 -type d ! -name "attachments" ! -path "*/attachments/*" | while read -r dir; do
    foldername=$(basename "$dir")
    index_file="$dir/index.md"

    if [ ! -f "$index_file" ]; then
        cat <<EOF > "$index_file"
---
title: "$foldername"
---
EOF
    fi
done

echo "Step 5/5: Fixing multiline \$\$ math blocks..."
python3 - "$QUARTZ_DIR/content" <<'EOF'
import os, re, sys

root = sys.argv[1]
for dirpath, _, filenames in os.walk(root):
    for name in filenames:
        if not name.endswith(".md"):
            continue
        path = os.path.join(dirpath, name)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        out = []
        in_code = False
        in_math = False
        changed = False

        for line in lines:
            stripped = line.strip()

            if re.match(r"^(`{3,}|~{3,})", stripped):
                in_code = not in_code
                out.append(line)
                continue

            if in_code:
                out.append(line)
                continue

            if not in_math:
                if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4 and stripped.count("$$") == 2:
                    indent = line[:len(line) - len(line.lstrip())]
                    inner = stripped[2:-2].strip()
                    out.append(f"{indent}$$\n")
                    out.append(f"{indent}{inner}\n")
                    out.append(f"{indent}$$\n")
                    changed = True
                    continue
                if stripped.startswith("$$") and stripped.count("$$") == 1:
                    indent = line[:len(line) - len(line.lstrip())]
                    rest = line.lstrip()[2:].lstrip()
                    if rest:
                        out.append(f"{indent}$$\n")
                        out.append(f"{indent}{rest}")
                        changed = True
                    else:
                        out.append(line)
                    in_math = True
                    continue
            else:
                if "$$" in line:
                    before, after = line.split("$$", 1)
                    if before.strip():
                        out.append(before.rstrip() + "\n")
                        changed = True
                    out.append("$$\n")
                    if after.strip():
                        out.append(after.lstrip())
                        changed = True
                    in_math = False
                    continue

            out.append(line)

        if changed:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(out)
EOF

echo "Success: Preparation complete."

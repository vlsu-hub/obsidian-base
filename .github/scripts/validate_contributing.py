import datetime
import os
import re
import sys
from pathlib import PurePosixPath
import yaml

ALLOWED_PREFIXES = ("LEC", "SEM", "LAB", "TST", "EXM")

ALLOWED_EXTENSIONS = {".md", ".pdf", ".webp"}
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 МБ

IGNORE_DIRS = {".github", ".git", ".obsidian", ".venv", "venv", "node_modules"}
WARNING_FILES = {".gitignore", "contributing.md", "readme.md"}
ALIAS_EXEMPT_TARGETS = {"README", "README.md", "CONTRIBUTING", "CONTRIBUTING.md"}

PREFIX_PATTERN = "|".join(ALLOWED_PREFIXES)
SEMESTER_RE = re.compile(r"^\d+-sem$")
SUBJECT_RE = re.compile(r"^[a-z0-9_]+$")
SUBFOLDER_RE = re.compile(r"^[a-z0-9_]+$")
TYPE_TEACHER_STD_RE = re.compile(r"^\d+-(LEC|SEM|LAB)_[A-Za-z-]+$")
TYPE_TEACHER_YEAR_RE = re.compile(r"^\d+-(TST|EXM)_[A-Za-z-]+_\d{4}$")

MD_FILENAME_RE = re.compile(rf"^({PREFIX_PATTERN})-(\d{{2}})_([a-z0-9_]+)\.md$")
CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG_RE = re.compile(r"^(author|typer|editor)/(\S+)$")


def normalize_path(filepath):
    p = filepath.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def format_mb(size_bytes):
    return f"{size_bytes / (1024 * 1024):.2f} МБ"


def strip_quote_prefix(line):
    return re.sub(r"^(\s*>\s*)+", "", line)


def has_unclosed_code_blocks(text):
    in_block = False
    fence_char = ""
    fence_len = 0

    for line in text.splitlines():
        line_clean = strip_quote_prefix(line).strip()
        if not in_block:
            match = re.match(r"^(`{3,}|~{3,})", line_clean)
            if match:
                in_block = True
                fence_str = match.group(1)
                fence_char = fence_str[0]
                fence_len = len(fence_str)
        else:
            match = re.match(r"^(`{3,}|~{3,})$", line_clean)
            if match:
                fence_str = match.group(1)
                if fence_str[0] == fence_char and len(fence_str) >= fence_len:
                    in_block = False

    return in_block


def strip_code(text):
    out_lines = []
    in_block = False
    fence_char = ""
    fence_len = 0

    for line in text.splitlines():
        line_clean = strip_quote_prefix(line).strip()
        if not in_block:
            match = re.match(r"^(`{3,}|~{3,})", line_clean)
            if match:
                in_block = True
                fence_str = match.group(1)
                fence_char = fence_str[0]
                fence_len = len(fence_str)
                continue
            out_lines.append(line)
        else:
            match = re.match(r"^(`{3,}|~{3,})$", line_clean)
            if match:
                fence_str = match.group(1)
                if fence_str[0] == fence_char and len(fence_str) >= fence_len:
                    in_block = False

    cleaned = "\n".join(out_lines)
    cleaned = re.sub(r"(`+)(?:(?!\1)[^\n])*?\1", "", cleaned)
    return cleaned


def is_blank_md_line(line):
    return strip_quote_prefix(line).strip() == ""


def check_display_math(body_text, norm_path):
    errors = []
    lines = body_text.splitlines()

    in_code_block = False
    fence_char = ""
    fence_len = 0
    in_math = False

    for idx, raw_line in enumerate(lines):
        content = strip_quote_prefix(raw_line)
        stripped = content.strip()

        if not in_code_block:
            match = re.match(r"^(`{3,}|~{3,})", stripped)
            if match:
                in_code_block = True
                fence_str = match.group(1)
                fence_char = fence_str[0]
                fence_len = len(fence_str)
                continue
        else:
            match = re.match(r"^(`{3,}|~{3,})$", stripped)
            if match:
                fence_str = match.group(1)
                if fence_str[0] == fence_char and len(fence_str) >= fence_len:
                    in_code_block = False
                continue
            continue

        content_no_inline_code = re.sub(r"(`+)(?:(?!\1)[^\n])*?\1", "", content)
        dollar_count = len(re.findall(r"\$\$", content_no_inline_code))

        if not in_math:
            if dollar_count == 0:
                continue
            if dollar_count == 1:
                if not content_no_inline_code.lstrip().startswith("$$"):
                    errors.append(
                        f"[{norm_path}] Строка {idx + 1}: перед открывающим `$$` не должно быть текста на той же строке."
                    )
                if idx > 0 and not is_blank_md_line(lines[idx - 1]):
                    errors.append(
                        f"[{norm_path}] Строка {idx + 1}: перед блочной формулой `$$` должна быть пустая строка."
                    )
                in_math = True
            elif dollar_count == 2:
                if not re.match(r"^\$\$.*\$\$$", content_no_inline_code.strip()):
                    errors.append(
                        f"[{norm_path}] Строка {idx + 1}: блочная формула `$$ ... $$` должна быть отделена от текста и занимать отдельную строку."
                    )
                if idx > 0 and not is_blank_md_line(lines[idx - 1]):
                    errors.append(
                        f"[{norm_path}] Строка {idx + 1}: перед блочной формулой `$$` должна быть пустая строка."
                    )
                if idx + 1 < len(lines) and not is_blank_md_line(lines[idx + 1]):
                    errors.append(
                        f"[{norm_path}] Строка {idx + 1}: после блочной формулы `$$` должна быть пустая строка."
                    )
            else:
                errors.append(
                    f"[{norm_path}] Строка {idx + 1}: некорректное количество разделителей `$$` в строке (ожидается одна формула на строку)."
                )
        else:
            if dollar_count == 0:
                continue
            if dollar_count == 1:
                if not content_no_inline_code.rstrip().endswith("$$"):
                    errors.append(
                        f"[{norm_path}] Строка {idx + 1}: после закрывающего `$$` не должно быть текста на той же строке."
                    )
                if idx + 1 < len(lines) and not is_blank_md_line(lines[idx + 1]):
                    errors.append(
                        f"[{norm_path}] Строка {idx + 1}: после блочной формулы `$$` должна быть пустая строка."
                    )
                in_math = False
            else:
                errors.append(
                    f"[{norm_path}] Строка {idx + 1}: некорректное закрытие блочной формулы `$$`."
                )
                in_math = False

    if in_math:
        errors.append(f"[{norm_path}] Обнаружена незакрытая блочная формула `$$`.")

    return errors


def validate_academic_dirs(dir_parts, norm_path):
    errors = []

    if len(dir_parts) >= 1 and not SEMESTER_RE.match(dir_parts[0]):
        errors.append(
            f"[{norm_path}] Корневая папка '{dir_parts[0]}' должна быть в формате `<номер>-sem` (например, `1-sem`)."
        )

    if len(dir_parts) >= 2 and not SUBJECT_RE.match(dir_parts[1]):
        errors.append(
            f"[{norm_path}] Папка предмета '{dir_parts[1]}' должна быть на английском в snake_case (только `a-z`, `0-9`, `_`)."
        )

    if len(dir_parts) >= 3:
        folder_3 = dir_parts[2]
        if not (TYPE_TEACHER_STD_RE.match(folder_3) or TYPE_TEACHER_YEAR_RE.match(folder_3)):
            errors.append(
                f"[{norm_path}] Папка 3-го уровня '{folder_3}' не соответствует формату `<цифра>-<ПРЕФИКС>_<ФамилияИО>` "
                f"(для TST/EXM обязательно `_<ГОД>` в конце; в фамилии допустимы только латиница и `-`)."
            )

    for subfolder in dir_parts[3:]:
        if not SUBFOLDER_RE.match(subfolder):
            errors.append(
                f"[{norm_path}] Подпапка '{subfolder}' должна быть на английском в snake_case (только `a-z`, `0-9`, `_`)."
            )

    return errors


def is_local_absolute_path(target):
    return bool(
        target.startswith("file://")
        or re.match(r"^[a-zA-Z]:[/\\]", target)
        or re.match(r"^/(Users|home|root|tmp)/", target)
        or target.startswith(r"\\")
    )


def validate_body_common(body_text, norm_path, require_non_empty=True):
    errors = []

    if has_unclosed_code_blocks(body_text):
        errors.append(f"[{norm_path}] Обнаружен незакрытый блок кода.")

    clean_body = strip_code(body_text)

    if require_non_empty and not re.search(r"[a-zA-Zа-яА-Я0-9]", clean_body):
        errors.append(f"[{norm_path}] Файл не содержит текста конспекта.")

    errors.extend(check_display_math(body_text, norm_path))

    md_links = re.findall(r"!?\[.*?\]\((.*?)\)", clean_body)
    for raw_link in md_links:
        if not raw_link.strip():
            continue
        target = raw_link.strip().split()[0].strip("<>")
        if is_local_absolute_path(target):
            errors.append(f"[{norm_path}] Обнаружен локальный абсолютный путь '{target}'.")

    embed_links = re.findall(r"!\[\[(.*?)\]\]", clean_body)
    for raw_link in embed_links:
        target = raw_link.strip().split("|")[0].strip()
        if is_local_absolute_path(target):
            errors.append(f"[{norm_path}] Обнаружен локальный абсолютный путь '{target}'.")

    wiki_links = re.findall(r"(?<!!)\[\[(.*?)\]\]", clean_body)
    for raw_link in wiki_links:
        inner = raw_link.strip()
        target = inner.split("|", 1)[0].strip()
        if is_local_absolute_path(target):
            errors.append(f"[{norm_path}] Обнаружен локальный абсолютный путь '{target}'.")

        if "|" not in inner:
            if target not in ALIAS_EXEMPT_TARGETS and not target.startswith("#"):
                errors.append(
                    f"[{norm_path}] Вики-ссылка `[[{inner}]]` должна содержать русский алиас через `|` (например, `[[{target}|...]]`)."
                )
        else:
            alias = inner.split("|", 1)[1].strip()
            if not alias:
                errors.append(f"[{norm_path}] В вики-ссылке `[[{inner}]]` пустой алиас после `|`.")

    text_for_tags = re.sub(r"\$\$.*?\$\$", "", clean_body, flags=re.DOTALL)
    text_for_tags = re.sub(r"\$[^$\n]+\$", "", text_for_tags)
    text_for_tags = re.sub(r"!?\[.*?\]\(.*?\)", "", text_for_tags)
    text_for_tags = re.sub(r"!?\[\[.*?\]\]", "", text_for_tags)
    text_for_tags = re.sub(r"https?://\S+", "", text_for_tags)

    body_tags = re.findall(r"(?<!\S)#[a-zA-Zа-яА-ЯёЁ0-9_/-]+", text_for_tags)
    for tag in body_tags:
        errors.append(
            f"[{norm_path}] Запрещённый хештег '{tag}' в тексте конспекта. Теги допустимы только в YAML-шапке."
        )

    return errors


def parse_frontmatter(content, norm_path):
    yaml_match = re.match(r"^---\r?\n(.*?\r?\n)?---(?:\r?\n(.*))?$", content, re.DOTALL)
    if not yaml_match:
        return None, None, [f"[{norm_path}] Отсутствует или повреждена YAML-шапка (`---`)."]

    yaml_text = yaml_match.group(1) or ""
    body_text = yaml_match.group(2) or ""

    try:
        metadata = yaml.safe_load(yaml_text)
    except (yaml.YAMLError, ValueError) as e:
        return None, None, [f"[{norm_path}] Синтаксическая ошибка или некорректная дата (`date`) в YAML-шапке: {e}"]

    if not isinstance(metadata, dict):
        return None, None, [f"[{norm_path}] YAML-шапка должна быть словарём (ключ: значение)."]

    return metadata, body_text, []


def validate_note_yaml(metadata, norm_path, expected_prefix, expected_num):
    errors = []

    title = metadata.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(f"[{norm_path}] В YAML-шапке отсутствует или пустое поле `title`.")
    else:
        expected_head = f"{expected_prefix}-{expected_num} "
        if not title.strip().startswith(expected_head) or len(title.strip()) <= len(expected_head):
            errors.append(
                f"[{norm_path}] Поле `title` должно начинаться с `{expected_head}` и содержать название (например, `{expected_head}введение`)."
            )

    if "date" not in metadata:
        errors.append(f"[{norm_path}] В YAML-шапке отсутствует поле `date`.")
    else:
        date_val = metadata.get("date")
        date_str = str(date_val).strip()
        is_valid_date = False
        if (type(date_val) is datetime.date or isinstance(date_val, str)) and DATE_RE.match(date_str):
            try:
                datetime.date.fromisoformat(date_str)
                is_valid_date = True
            except ValueError:
                is_valid_date = False

        if not is_valid_date:
            errors.append(f"[{norm_path}] Поле `date` должно быть корректной датой в формате `YYYY-MM-DD`.")

    tags = metadata.get("tags")
    if not tags or not isinstance(tags, list):
        errors.append(f"[{norm_path}] В YAML-шапке отсутствует список `tags`.")
    else:
        authors = []
        typers = []

        for tag in tags:
            tag_str = str(tag).strip()
            match = TAG_RE.match(tag_str)
            if not match:
                errors.append(
                    f"[{norm_path}] Недопустимый тег '{tag_str}' в YAML-шапке. Разрешены только `author/ник`, `typer/ник` и `editor/ник`."
                )
                continue

            role, username = match.groups()
            if role == "author":
                authors.append(username)
            elif role == "typer":
                typers.append(username)

        if not authors:
            errors.append(f"[{norm_path}] В `tags` отсутствует обязательный тег `author/username`.")
        elif len(authors) >= 2 and not typers:
            errors.append(
                f"[{norm_path}] Указано несколько авторов — тег `typer/username` обязателен."
            )
        elif len(authors) == 1 and any(t.lower() == authors[0].lower() for t in typers):
            errors.append(
                f"[{norm_path}] Если автор один и он же набрал конспект, тег `typer/{authors[0]}` указывать нельзя."
            )

    return errors


def check_file(filepath):
    errors = []
    warnings = []

    norm_path = normalize_path(filepath)
    path_parts = PurePosixPath(norm_path).parts

    if not path_parts or any(part in IGNORE_DIRS for part in path_parts):
        return errors, warnings

    filename = path_parts[-1]
    ext = os.path.splitext(filename)[1].lower()

    if len(path_parts) == 1 and filename.lower() in WARNING_FILES:
        warnings.append(f"Изменён системный файл `{norm_path}` — убедитесь, что правка согласована с мейнтейнерами.")
        return errors, warnings

    if ext not in ALLOWED_EXTENSIONS:
        errors.append(f"[{norm_path}] Недопустимое расширение '{ext}'. Разрешены только: .md, .pdf, .webp.")
        return errors, warnings

    file_size = os.path.getsize(filepath)
    if file_size > MAX_FILE_SIZE_BYTES:
        errors.append(
            f"[{norm_path}] Превышен размер файла: {format_mb(file_size)} (лимит 1.00 МБ)."
        )

    if ext == ".pdf":
        if CYRILLIC_RE.search(filename):
            errors.append(f"[{norm_path}] В имени PDF-файла запрещены русские буквы.")
        return errors, warnings

    if ext == ".webp":
        if len(path_parts) < 5 or path_parts[-2] != "attachments":
            errors.append(
                f"[{norm_path}] Изображения `.webp` должны лежать внутри папки `attachments/` рядом с конспектами (минимум внутри папки `<цифра>-<ПРЕФИКС>_<ФамилияИО>/attachments/`)."
            )
            return errors, warnings

        dir_parts = path_parts[:-2]
        errors.extend(validate_academic_dirs(dir_parts, norm_path))

        expected_prefix = "_".join(dir_parts)
        webp_re = re.compile(rf"^{re.escape(expected_prefix)}_({PREFIX_PATTERN})-\d{{2}}_\d+\.webp$")
        if not webp_re.match(filename):
            errors.append(
                f"[{norm_path}] Неверное имя изображения. Ожидается: `{expected_prefix}_<ПРЕФИКС>-<XX>_<N>.webp`."
            )
        return errors, warnings

    if "attachments" in [part.lower() for part in path_parts[:-1]]:
        errors.append(f"[{norm_path}] Markdown-файлы нельзя размещать внутри папки `attachments/`.")
        return errors, warnings

    is_index = filename == "_index.md"
    if not is_index and filename.startswith("_"):
        errors.append(f"[{norm_path}] Файлы, начинающиеся с `_`, запрещены (допускается только `_index.md`).")
        return errors, warnings

    if len(path_parts) == 1:
        if not is_index:
            errors.append(
                f"[{norm_path}] Учебные файлы не могут лежать в корне репозитория. Используйте папку семестра (например, `1-sem/`)."
            )
            return errors, warnings
    else:
        errors.extend(validate_academic_dirs(path_parts[:-1], norm_path))

    note_prefix = None
    note_num = None

    if not is_index:
        if len(path_parts) < 4:
            errors.append(
                f"[{norm_path}] Учебный конспект должен находиться внутри папки `<N>-sem/<subject>/<цифра>-<ПРЕФИКС>_<ФамилияИО>/`."
            )
        match_name = MD_FILENAME_RE.match(filename)
        if not match_name:
            errors.append(
                f"[{norm_path}] Неверное имя файла. Ожидается `<ПРЕФИКС>-<XX>_<english_snake_case>.md` "
                f"(допустимые префиксы: {', '.join(ALLOWED_PREFIXES)})."
            )
        else:
            note_prefix, note_num, _ = match_name.groups()

    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except UnicodeDecodeError:
        errors.append(f"[{norm_path}] Файл не в кодировке UTF-8.")
        return errors, warnings
    except OSError as e:
        errors.append(f"[{norm_path}] Ошибка чтения файла: {e}")
        return errors, warnings

    metadata, body_text, fm_errors = parse_frontmatter(content, norm_path)
    errors.extend(fm_errors)
    if metadata is None:
        return errors, warnings

    if is_index:
        title = metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"[{norm_path}] В `_index.md` должно быть заполнено поле `title`.")
        errors.extend(validate_body_common(body_text, norm_path, require_non_empty=False))
    else:
        if note_prefix and note_num:
            errors.extend(validate_note_yaml(metadata, norm_path, note_prefix, note_num))
        errors.extend(validate_body_common(body_text, norm_path, require_non_empty=True))

    return errors, warnings


def build_markdown_report(checked_count, all_errors, all_warnings):
    lines = ["<!-- vlsu-contributing-bot -->"]

    if all_errors:
        lines.append("## ❌ Проверка регламента не пройдена")
        lines.append("")
        lines.append(
            f"Проверено файлов: **{checked_count}** | Ошибок: **{len(all_errors)}** | Предупреждений: **{len(all_warnings)}**"
        )
        lines.append("")
        lines.append(
            "Исправь замечания ниже и запушь новый коммит в этот же Pull Request — проверка перезапустится автоматически (закрывать PR не нужно)."
        )
        lines.append("")
        lines.append("### Ошибки")
        for err in all_errors:
            lines.append(f"- {err}")
    else:
        lines.append("## ✅ Проверка регламента пройдена")
        lines.append("")
        lines.append(f"Проверено файлов: **{checked_count}**. Ошибок не обнаружено.")

    if all_warnings:
        lines.append("")
        lines.append("### Предупреждения")
        for warn in all_warnings:
            lines.append(f"- {warn}")

    return "\n".join(lines) + "\n"


def write_report(report_path, content):
    if not report_path:
        return
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    changed_list_path = os.environ.get("CHANGED_FILES_PATH", "changed_files.txt")
    report_path = os.environ.get("REPORT_FILE_PATH", "pr_report.md")

    try:
        with open(changed_list_path, "r", encoding="utf-8") as f:
            files_to_check = [line.strip().strip('"') for line in f if line.strip()]
    except FileNotFoundError:
        msg = "Файл changed_files.txt не найден. Проверка пропущена."
        print(msg)
        write_report(report_path, build_markdown_report(0, [], [msg]))
        return 0

    existing_files = [fp for fp in files_to_check if os.path.exists(fp) and os.path.isfile(fp)]
    if not existing_files:
        print("Нет файлов для проверки.")
        write_report(report_path, build_markdown_report(0, [], []))
        return 0

    all_errors = []
    all_warnings = []

    print(f"Запуск проверки для {len(existing_files)} файла(ов)...")
    for filepath in existing_files:
        errors, warnings = check_file(filepath)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

        for warning in warnings:
            print(f"::warning title=Внимание::{warning}")
        for error in errors:
            print(f"::error file={normalize_path(filepath)},title=Ошибка валидации::{error}")

    report_md = build_markdown_report(len(existing_files), all_errors, all_warnings)
    write_report(report_path, report_md)

    if all_errors:
        print(f"\n[!] ОШИБКА ВАЛИДАЦИИ (найдено проблем: {len(all_errors)}):\n")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("\n[OK] Проверка успешно пройдена.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

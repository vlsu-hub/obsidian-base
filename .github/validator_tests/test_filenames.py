import pytest
from validate_contributing import check_file

# Валидный контент, чтобы тесты имен не падали на ошибках парсинга YAML
DUMMY_VALID_CONTENT = """---
date: 2024-01-01
tags:
  - author/tester
---
Тело документа
"""


@pytest.fixture
def make_file(tmp_path, monkeypatch):
    """Фикстура-помощник для быстрого создания файлов по относительному пути."""
    monkeypatch.chdir(tmp_path)

    def _create(rel_path, content=DUMMY_VALID_CONTENT, is_binary=False):
        file_path = tmp_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if is_binary:
            file_path.write_bytes(b"\x00" * 100)
        else:
            file_path.write_text(content, encoding="utf-8")
        return rel_path

    return _create


# =====================================================================
# 1. ТЕСТЫ РАСШИРЕНИЙ ФАЙЛОВ
# =====================================================================


@pytest.mark.parametrize(
    "ext", [".md", ".MD", ".png", ".PNG", ".jpg", ".JPEG", ".webp", ".pdf", ".svg"]
)
def test_allowed_extensions_case_insensitive(make_file, ext):
    """Разрешенные расширения в любом регистре должны проходить."""
    path = make_file(f"folder/test_file{ext}", is_binary=(ext.lower() != ".md"))
    errors, _ = check_file(path)
    assert not any("Недопустимое расширение" in err for err in errors)


@pytest.mark.parametrize("ext", [".exe", ".txt", ".docx", ".py", ".sh", ".zip"])
def test_forbidden_extensions(make_file, ext):
    """Запрещенные расширения должны выдавать ошибку."""
    path = make_file(f"folder/danger{ext}")
    errors, _ = check_file(path)
    assert any("Недопустимое расширение" in err for err in errors)


# =====================================================================
# 2. ТЕСТЫ СТРОГОГО ФОРМАТА ИМЕНИ ФАЙЛА
# =====================================================================


@pytest.mark.parametrize(
    "valid_name",
    [
        "ПР 01 - os-intro.md",
        "ЛБ 12 - lab_work.md",
        "КП 00 - course-project.md",
        "ЭКЗ 99 - билеты-к-экзамену.md",
        "ПР 01 - тема-с-буквой-ё-и-цифрами-123.md",  # Буква ё и цифры
    ],
)
def test_valid_filename_formats(make_file, valid_name):
    """Корректные названия файлов Markdown."""
    path = make_file(f"folder/{valid_name}")
    errors, _ = check_file(path)
    # Проверяем, что ошибок формата имени нет
    assert not any("Неверный формат имени" in err for err in errors)
    assert not any("Ошибка в теме" in err for err in errors)


@pytest.mark.parametrize(
    "invalid_prefix",
    [
        "пр 01 - topic.md",  # Маленькие буквы префикса
        "Пр 01 - topic.md",  # Смешанный регистр
        "ДЗ 01 - topic.md",  # Запрещенный префикс
        "ТЕСТ 01 - topic.md",
    ],
)
def test_invalid_prefixes(make_file, invalid_prefix):
    """Префикс должен быть строго из ALLOWED_PREFIXES в верхнем регистре."""
    path = make_file(f"folder/{invalid_prefix}")
    errors, _ = check_file(path)
    assert any("Неверный формат имени" in err for err in errors)


@pytest.mark.parametrize(
    "invalid_spacing_or_digits",
    [
        "ПР 1 - topic.md",  # 1 цифра вместо 2
        "ПР 001 - topic.md",  # 3 цифры вместо 2
        "ПР  01 - topic.md",  # Двойной пробел
        "ПР 01- topic.md",  # Нет пробела перед дефисом
        "ПР 01 -topic.md",  # Нет пробела после дефиса
        "ПР 01-topic.md",  # Дефис слитный
        "ПР 01 – topic.md",  # Длинное тире (en-dash) вместо дефиса
    ],
)
def test_invalid_spacing_and_delimiters(make_file, invalid_spacing_or_digits):
    """Ошибки в пробелах, количестве цифр и знаках разделения."""
    path = make_file(f"folder/{invalid_spacing_or_digits}")
    errors, _ = check_file(path)
    assert any("Неверный формат имени" in err for err in errors)


@pytest.mark.parametrize(
    "invalid_topic",
    [
        "ПР 01 - Topic.md",  # Заглавная буква
        "ПР 01 - моё_Задание.md",  # Заглавная русская буква
        "ПР 01 - тема с пробелами.md",  # Пробелы в теме запрещены
        "ПР 01 - тема.с.точкой.md",  # Точки в теме запрещены
        "ПР 01 - тема,запятая.md",  # Запятые запрещены
        "ПР 01 - topic(v1).md",  # Скобки запрещены
        "ПР 01 - topic_🔥.md",  # Эмодзи запрещены
        "ПР 01 - .md",  # Пустая тема
    ],
)
def test_invalid_topic_characters(make_file, invalid_topic):
    """Проверка ограничений темы: только a-z, а-я, ё, 0-9, '_' и '-'."""
    path = make_file(f"folder/{invalid_topic}")
    errors, _ = check_file(path)
    assert any(
        ("Ошибка в теме" in err or "Неверный формат имени" in err) for err in errors
    )


# =====================================================================
# 3. ИСКЛЮЧЕНИЯ И СЛУЖЕБНЫЕ ФАЙЛЫ
# =====================================================================


def test_underscore_files_are_ignored(make_file):
    """Файлы, начинающиеся с '_', игнорируют проверку формата имени."""
    # У него нет префикса и есть пробелы, но есть '_' в начале
    path = make_file("folder/_sidebar menu.md")
    errors, _ = check_file(path)
    assert not any("Неверный формат имени" in err for err in errors)


def test_non_markdown_files_skip_naming_rules(make_file):
    """Картинки не обязаны подчиняться правилу 'ПР 01 - ...'."""
    path = make_file("folder/my screenshot (1).png", is_binary=True)
    errors, _ = check_file(path)
    assert len(errors) == 0


def test_system_warning_files(make_file):
    """Изменение системных файлов порождает Warning, а не Error."""
    path = make_file(".gitignore", content="# ignore")
    errors, warnings = check_file(path)
    assert len(errors) == 0
    assert len(warnings) == 1
    assert "Изменен системный файл" in warnings[0]


# =====================================================================
# 4. ТЕСТЫ ПУТЕЙ И ВЛОЖЕННОСТИ (СЕМЕСТРЫ И ПАПКИ 3-ГО УРОВНЯ)
# =====================================================================


@pytest.mark.parametrize("semester_folder", ["1_семестр", "2_Семестр", "СЕМЕСТР_3"])
def test_semester_casing_detection(make_file, semester_folder):
    """Слово 'семестр' должно определяться независимо от регистра."""
    # 4 уровня: [семестр, предмет, папка_без_цифры, файл]
    path = make_file(f"{semester_folder}/мат_анализ/теория/ПР 01 - intro.md")
    errors, _ = check_file(path)
    assert any("должна начинаться с цифры" in err for err in errors)


@pytest.mark.parametrize(
    "valid_lvl3_folder", ["1_intro", "02_lection", "999_super_practice"]
)
def test_valid_folder_level_3(make_file, valid_lvl3_folder):
    """Папка 3-го уровня правильно начинается с цифры и подчеркивания."""
    path = make_file(f"1_семестр/мат_анализ/{valid_lvl3_folder}/ПР 01 - intro.md")
    errors, _ = check_file(path)
    assert not any("должна начинаться с цифры" in err for err in errors)


@pytest.mark.parametrize(
    "invalid_lvl3_folder", ["intro", "_1_intro", "lection_1", "1-intro"]
)
def test_invalid_folder_level_3(make_file, invalid_lvl3_folder):
    """Папка 3-го уровня НЕ начинается с 'цифра_'."""
    path = make_file(f"1_семестр/мат_анализ/{invalid_lvl3_folder}/ПР 01 - intro.md")
    errors, _ = check_file(path)
    assert any("должна начинаться с цифры" in err for err in errors)


def test_path_outside_semester_is_not_checked_for_digits(make_file):
    """Если папка не семестр, требование '1_' к 3-му уровню не применяется."""
    path = make_file("общие_материалы/книги/любая_папка/ПР 01 - intro.md")
    errors, _ = check_file(path)
    assert not any("должна начинаться с цифры" in err for err in errors)


def test_semester_path_less_than_4_levels(make_file):
    """Если в семестре файл лежит неглубоко (нет 3 уровня папок), ошибки нет."""
    # 3 уровня: [1_семестр, мат_анализ, файл.md]
    path = make_file("1_семестр/мат_анализ/ПР 01 - intro.md")
    errors, _ = check_file(path)
    assert not any("должна начинаться с цифры" in err for err in errors)


def test_media_in_semester_without_attachments_folder_fails(make_file):
    path = make_file("1 семестр/физика/1_лекции/доска.png", is_binary=True)
    errors, _ = check_file(path)
    assert any("должны находиться внутри папки 'attachments/'" in err for err in errors)


def test_media_in_semester_with_attachments_folder_passes(make_file):
    path = make_file("1 семестр/физика/1_лекции/attachments/доска.png", is_binary=True)
    errors, _ = check_file(path)
    assert len(errors) == 0

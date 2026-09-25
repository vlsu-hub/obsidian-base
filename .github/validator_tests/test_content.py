import pytest
from validate_contributing import check_file


@pytest.fixture
def make_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _create(rel_path="ПР 01 - test.md", content="", encoding="utf-8"):
        file_path = tmp_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Записываем с нужной кодировкой
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return rel_path

    return _create


# =====================================================================
# 1. ТЕСТЫ YAML ТЕГОВ (AUTHOR, TYPER, EDITOR)
# =====================================================================


def test_yaml_valid_mandatory_tags(make_file):
    """Присутствуют оба тега: author и typer (разные или одинаковые люди)."""
    content = """---
date: 2024-01-01
tags:
  - author/ivanov
  - typer/petrov
  - editor/sidorov
---
Текст
"""
    errors, _ = check_file(make_file(content=content))
    assert len(errors) == 0


def test_yaml_same_author_and_typer(make_file):
    """Один и тот же человек и автор, и тайпер."""
    content = """---
date: 2024-01-01
tags:
  - author/ivanov
  - typer/ivanov
---
Текст
"""
    errors, _ = check_file(make_file(content=content))
    assert len(errors) == 0


@pytest.mark.parametrize(
    "bad_tags, expected_errors",
    [
        ("- author/ivanov\n", ["Отсутствует обязательный тег 'typer/username'."]),
        ("- typer/petrov\n", ["Отсутствует обязательный тег 'author/username'."]),
        (
            "- editor/sidorov\n",
            [
                "Отсутствует обязательный тег 'author/username'.",
                "Отсутствует обязательный тег 'typer/username'.",
            ],
        ),
    ],
)
def test_yaml_missing_mandatory_tags(make_file, bad_tags, expected_errors):
    """Проверка ошибок при отсутствии одного или обоих обязательных тегов."""
    content = f"---\ndate: 2024-01-01\ntags:\n  {bad_tags}---\nТекст"
    errors, _ = check_file(make_file(content=content))

    assert len(errors) == len(expected_errors)
    for expected in expected_errors:
        assert any(expected in err for err in errors)


def test_yaml_tags_is_not_an_array(make_file):
    """Если поле tags передано как строка, а не массив."""
    content = """---
date: 2024-01-01
tags: author/ivanov, typer/ivanov
---
Текст
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Отсутствует массив 'tags'" in err for err in errors)


# =====================================================================
# 2. ТЕСТЫ ТЕГОВ В ТЕЛЕ ДОКУМЕНТА (BODY TAGS)
# =====================================================================


def test_body_tags_case_insensitive(make_file):
    """Разрешенные теги в теле документа в любом регистре."""
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст #ЭКЗАМЕН #ВаЖнО #дописать #вопрос
"""
    errors, _ = check_file(make_file(content=content))
    assert len(errors) == 0


def test_body_tags_forbidden(make_file):
    """Запрещенные теги отлавливаются."""
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст #шпора #какойтотег
"""
    errors, _ = check_file(make_file(content=content))
    assert len(errors) == 2
    assert any("Запрещенный тег '#шпора'" in err for err in errors)
    assert any("Запрещенный тег '#какойтотег'" in err for err in errors)


def test_tags_inside_code_blocks_are_ignored(make_file):
    """Теги внутри inline-кода и блоков кода должны игнорироваться скриптом."""
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Вот блок кода:
```python
#запрещенный_тег_в_коде
print("Hello")
```
А вот инлайн: `#еще_один_плохой_тег`
"""
    errors, _ = check_file(make_file(content=content))
    assert len(errors) == 0


# =====================================================================
# 3. ТЕСТЫ СТРУКТУРЫ YAML И ДАТЫ
# =====================================================================


@pytest.mark.parametrize(
    "invalid_date", ["01-01-2024", "2024/01/01", "24-01-01", "2024-1-1"]
)
def test_invalid_date_format(make_file, invalid_date):
    """Дата должна быть строго YYYY-MM-DD."""
    content = f"---\ndate: {invalid_date}\ntags:\n  - author/i\n  - typer/i\n---\nТекст"
    errors, _ = check_file(make_file(content=content))
    assert any("формате YYYY-MM-DD" in err for err in errors)


def test_missing_date(make_file):
    """Отсутствие поля date."""
    content = """---
tags:
  - author/i
  - typer/i
---
Текст
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Отсутствует поле 'date'" in err for err in errors)


def test_missing_yaml_frontmatter(make_file):
    """Полное отсутствие YAML шапки."""
    content = "# Заголовок\n\nПросто текст без шапки"
    errors, _ = check_file(make_file(content=content))
    assert any("Отсутствует или повреждена YAML шапка" in err for err in errors)


def test_malformed_yaml(make_file):
    """Синтаксическая ошибка внутри YAML."""
    content = """---
date: 2024-01-01
tags:
  - author/i
  typer/i  # сломан отступ (syntax error)
---
Текст
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Синтаксическая ошибка в YAML" in err for err in errors)


# =====================================================================
# 4. КРАЕВЫЕ СЛУЧАИ СИСТЕМЫ ФАЙЛОВ
# =====================================================================


def test_file_wrong_encoding(make_file):
    """Попытка подсунуть файл в кодировке Windows-1251 (должна быть UTF-8)."""
    content = (
        "---\ndate: 2024-01-01\ntags:\n  - author/i\n  - typer/i\n---\nРусский текст"
    )
    # Создаем файл с неверной кодировкой
    path = make_file(content=content, encoding="windows-1251")

    errors, _ = check_file(path)
    assert any("Файл не в кодировке UTF-8" in err for err in errors)


# =====================================================================
# 5. ТЕСТЫ ОГРАНИЧЕНИЙ И СПЕЦСИМВОЛОВ В ПУТЯХ
# =====================================================================


def test_file_size_exceeded(make_file, monkeypatch):
    """Проверка лимита размера файла (> 10 МБ)."""
    import os

    # Создаем обычный маленький файлик
    path = make_file("folder/ПР 01 - test.md")

    # "Обманываем" os.path.getsize, чтобы для любого файла он возвращал 11 МБ
    # 11 МБ = 11 * 1024 * 1024 байт
    monkeypatch.setattr(os.path, "getsize", lambda x: 11 * 1024 * 1024)

    errors, _ = check_file(path)
    assert any("Превышен размер файла" in err for err in errors)


def test_spaces_and_brackets_in_directory_names(make_file):
    """Проверка путей с пробелами, скобками и русскими буквами (как в contributing.md)."""

    # Даем файлу правильную шапку, чтобы скрипт не ругался на пустой контент
    valid_content = (
        "---\ndate: 2024-01-01\ntags:\n  - author/i\n  - typer/i\n---\nТекст"
    )

    path = make_file(
        rel_path="1 семестр/физика/1_лекции (Малышева ДА)/ПР 01 - кинематика.md",
        content=valid_content,
    )

    errors, _ = check_file(path)
    assert len(errors) == 0, f"Ошибки при обработке сложных путей: {errors}"


def test_unclosed_code_blocks(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст конспекта
```python
print("Hello world")
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Обнаружен незакрытый блок кода" in err for err in errors)


def test_closed_code_blocks_with_tildes(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст конспекта
~~~
print("Hello world")
~~~
"""
    errors, _ = check_file(make_file(content=content))
    assert not any("Обнаружен незакрытый блок кода" in err for err in errors)


def test_empty_body_rejected(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---

   \n\n
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Файл не содержит текста конспекта" in err for err in errors)


def test_h1_header_forbidden(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
# Главный заголовок темы

## Подзаголовок
Текст конспекта
"""
    errors, _ = check_file(make_file(content=content))
    assert any(
        "Запрещено использовать заголовок первого уровня" in err for err in errors
    )


def test_tag_at_line_start_is_not_h1(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
#важно
Текст конспекта продолжается тут.
"""
    errors, _ = check_file(make_file(content=content))
    assert not any(
        "Запрещено использовать заголовок первого уровня" in err for err in errors
    )


def test_unclosed_code_blocks(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст конспекта
```python
print("Hello world")
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Обнаружен незакрытый блок кода" in err for err in errors)


def test_closed_code_blocks_with_tildes(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст конспекта
~~~
print("Hello world")
~~~
"""
    errors, _ = check_file(make_file(content=content))
    assert not any("Обнаружен незакрытый блок кода" in err for err in errors)


def test_empty_body_rejected(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---

   \n\n
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Файл не содержит текста конспекта" in err for err in errors)


def test_h1_header_forbidden(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
# Главный заголовок темы

## Подзаголовок
Текст конспекта
"""
    errors, _ = check_file(make_file(content=content))
    assert any(
        "Запрещено использовать заголовок первого уровня" in err for err in errors
    )


def test_tag_at_line_start_is_not_h1(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
#важно
Текст конспекта продолжается тут.
"""
    errors, _ = check_file(make_file(content=content))
    assert not any(
        "Запрещено использовать заголовок первого уровня" in err for err in errors
    )


@pytest.mark.parametrize(
    "bad_link",
    [
        "![img](C:/Users/student/Desktop/pic.png)",
        "![img](C:\\Users\\student\\Desktop\\pic.png)",
        "[link](file:///home/user/doc.pdf)",
        "![[D:/images/schema.png]]",
        "![[/home/ivan/schema.png]]",
    ],
)
def test_local_absolute_paths_rejected(make_file, bad_link):
    content = f"""---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст конспекта.
{bad_link}
"""
    errors, _ = check_file(make_file(content=content))
    assert any("Обнаружен локальный абсолютный путь" in err for err in errors)


def test_local_path_inside_code_block_is_allowed(make_file):
    content = """---
date: 2024-01-01
tags:
  - author/i
  - typer/i
---
Текст конспекта.
```python
path = "C:/Users/admin/file.txt"
```
"""
    errors, _ = check_file(make_file(content=content))
    assert not any("Обнаружен локальный абсолютный путь" in err for err in errors)

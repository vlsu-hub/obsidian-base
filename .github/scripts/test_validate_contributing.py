import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import validate_contributing as vc  # noqa: E402


class BaseValidatorTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def write_file(self, rel_path, content="dummy", binary=False, encoding="utf-8"):
        parent = os.path.dirname(rel_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        mode = "wb" if binary else "w"
        kwargs = {} if binary else {"encoding": encoding}
        with open(rel_path, mode, **kwargs) as f:
            f.write(content)
        return rel_path

    def make_note(
        self,
        title="LEC-01 законы ньютона",
        date="2026-09-02",
        tags_block="  - author/user1",
        body="Основной текст конспекта.\n",
    ):
        return (
            f"---\n"
            f"title: {title}\n"
            f"date: {date}\n"
            f"tags:\n"
            f"{tags_block}\n"
            f"---\n\n"
            f"{body}"
        )


class TestIgnoreAndSystemFiles(BaseValidatorTest):
    def test_ignored_directories_are_skipped(self):
        ignored_paths = [
            ".github/workflows/pr-check.yml",
            ".git/HEAD",
            ".obsidian/workspace.json",
            ".venv/bin/python",
            "venv/lib/test.exe",
            "node_modules/pkg/index.js",
        ]
        for rel in ignored_paths:
            p = self.write_file(rel, "broken content ### [[bad]]")
            errors, warnings = vc.check_file(p)
            self.assertEqual(errors, [], f"Ожидали игнор для {rel}")
            self.assertEqual(warnings, [], f"Ожидали игнор для {rel}")

    def test_root_system_files_produce_warning_only(self):
        for name in ("README.md", "readme.md", "CONTRIBUTING.md", ".gitignore"):
            p = self.write_file(name, "# Системный файл без YAML\n")
            errors, warnings = vc.check_file(p)
            self.assertEqual(errors, [], f"Не должно быть ошибок для {name}")
            self.assertEqual(len(warnings), 1, f"Ожидалось предупреждение для {name}")

    def test_readme_inside_subfolder_is_not_treated_as_system_file(self):
        p = self.write_file("1-sem/physics/README.md", "# Readme\n")
        errors, warnings = vc.check_file(p)
        self.assertTrue(errors)
        self.assertEqual(warnings, [])

    def test_regular_file_in_root_rejected(self):
        for rel in ("LEC-01_test.md", "notes.md", "image.webp"):
            p = self.write_file(rel, "content")
            errors, _ = vc.check_file(p)
            self.assertTrue(errors, f"Файл в корне {rel} должен отклоняться")


class TestExtensionsSizesAndPdf(BaseValidatorTest):
    def test_disallowed_extensions_rejected(self):
        bad_files = [
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/pic.png",
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/pic.jpg",
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/pic.svg",
            "1-sem/physics/1-LEC_MalyshevaDA/notes.txt",
            "1-sem/physics/1-LEC_MalyshevaDA/archive.zip",
            "1-sem/physics/1-LEC_MalyshevaDA/no_ext",
        ]
        for rel in bad_files:
            p = self.write_file(rel, b"data", binary=True)
            errors, _ = vc.check_file(p)
            self.assertTrue(any("Недопустимое расширение" in e for e in errors), rel)

    def test_file_size_limit_1mb_boundary(self):
        exact_1mb = 1024 * 1024
        ok_webp = self.write_file(
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/1-sem_physics_1-LEC_MalyshevaDA_LEC-01_1.webp",
            b"0" * exact_1mb,
            binary=True,
        )
        too_big_webp = self.write_file(
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/1-sem_physics_1-LEC_MalyshevaDA_LEC-01_2.webp",
            b"0" * (exact_1mb + 1),
            binary=True,
        )
        too_big_pdf = self.write_file(
            "1-sem/physics/book.pdf",
            b"0" * (exact_1mb + 1),
            binary=True,
        )

        self.assertEqual(vc.check_file(ok_webp)[0], [])
        self.assertTrue(any("Превышен размер файла" in e for e in vc.check_file(too_big_webp)[0]))
        self.assertTrue(any("Превышен размер файла" in e for e in vc.check_file(too_big_pdf)[0]))

    def test_pdf_location_flexible_and_cyrillic_forbidden(self):
        valid_pdfs = [
            "1-sem/physics/manual_2026.pdf",
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/lecture-01.pdf",
            "manual.PDF",
        ]
        for rel in valid_pdfs:
            p = self.write_file(rel, b"%PDF-1.4", binary=True)
            self.assertEqual(vc.check_file(p)[0], [], rel)

        bad_pdfs = [
            "1-sem/physics/методичка.pdf",
            "1-sem/physics/task_ё.pdf",
            "1-sem/physics/Лекция_1.PDF",
        ]
        for rel in bad_pdfs:
            p = self.write_file(rel, b"%PDF-1.4", binary=True)
            errors, _ = vc.check_file(p)
            self.assertTrue(any("русские буквы" in e for e in errors), rel)


class TestDirectoryAndFileNaming(BaseValidatorTest):
    def test_valid_academic_paths_and_prefixes(self):
        cases = [
            ("1-sem/physics/1-LEC_MalyshevaDA/LEC-00_intro.md", "LEC-00 введение"),
            ("1-sem/math/2-SEM_MorozovMV/SEM-12_integrals.md", "SEM-12 интегралы"),
            ("2-sem/defense_basics/3-LAB_Petrov-VodkinKS/LAB-03_lab_work.md", "LAB-03 лаба"),
            ("10-sem/physics/4-TST_MalyshevaDA_2026/1_mechanics/TST-01_test.md", "TST-01 рейтинг"),
            ("1-sem/math/5-EXM_MakarovaOV_2026/0_review/sub_2/EXM-99_ticket.md", "EXM-99 билет"),
        ]
        for rel, title in cases:
            p = self.write_file(rel, self.make_note(title=title))
            errors, _ = vc.check_file(p)
            self.assertEqual(errors, [], f"Должно проходить: {rel} -> {errors}")

    def test_invalid_directory_levels_rejected(self):
        bad_paths = [
            "sem-1/physics/1-LEC_IvanovII/LEC-01_a.md",
            "1_sem/physics/1-LEC_IvanovII/LEC-01_a.md",
            "1-sem/Physics/1-LEC_IvanovII/LEC-01_a.md",
            "1-sem/russian-statehood/1-LEC_IvanovII/LEC-01_a.md",
            "1-sem/физика/1-LEC_IvanovII/LEC-01_a.md",
            "1-sem/physics/LEC_IvanovII/LEC-01_a.md",
            "1-sem/physics/1-PST_IvanovII/LEC-01_a.md",
            "1-sem/physics/1-LEC_ИвановИИ/LEC-01_a.md",
            "1-sem/physics/1-LEC_Ivanov II/LEC-01_a.md",
            "1-sem/physics/4-TST_MalyshevaDA/TST-01_a.md",
            "1-sem/physics/5-EXM_MakarovaOV/EXM-01_a.md",
            "1-sem/physics/1-LEC_IvanovII/1-mechanics/LEC-01_a.md",
            "1-sem/physics/1-LEC_IvanovII/Mechanics/LEC-01_a.md",
        ]
        for rel in bad_paths:
            prefix_num = os.path.basename(rel).split("_")[0]
            p = self.write_file(rel, self.make_note(title=f"{prefix_num} тест"))
            errors, _ = vc.check_file(p)
            self.assertTrue(errors, f"Путь {rel} должен отклоняться")

    def test_md_too_shallow_or_inside_attachments_rejected(self):
        bad_paths = [
            "1-sem/LEC-01_a.md",
            "1-sem/physics/LEC-01_a.md",
            "1-sem/physics/1-LEC_IvanovII/attachments/LEC-01_a.md",
            "1-sem/physics/1-LEC_IvanovII/attachments/_index.md",
        ]
        for rel in bad_paths:
            p = self.write_file(rel, self.make_note(title="LEC-01 тест"))
            errors, _ = vc.check_file(p)
            self.assertTrue(errors, f"Должно отклоняться: {rel}")

    def test_invalid_md_filenames_rejected(self):
        bad_names = [
            "PST-01_problems.md",
            "SOL-01_solutions.md",
            "LEC-1_mechanics.md",
            "LEC_01_mechanics.md",
            "LEC-01-mechanics.md",
            "LEC-01_Mechanics.md",
            "LEC-01_механика.md",
            "LEC-01_newtons laws.md",
            "_draft.md",
            "_template.md",
        ]
        for name in bad_names:
            p = self.write_file(
                f"1-sem/physics/1-LEC_MalyshevaDA/{name}",
                self.make_note(title="LEC-01 тест"),
            )
            errors, _ = vc.check_file(p)
            self.assertTrue(errors, f"Имя файла {name} должно отклоняться")

    def test_index_allowed_at_all_non_attachment_levels(self):
        index_paths = [
            "_index.md",
            "1-sem/_index.md",
            "1-sem/physics/_index.md",
            "1-sem/physics/1-LEC_MalyshevaDA/_index.md",
            "1-sem/physics/4-TST_MalyshevaDA_2026/1_mechanics/_index.md",
        ]
        for rel in index_paths:
            p = self.write_file(rel, "---\ntitle: Раздел\n---\n")
            errors, _ = vc.check_file(p)
            self.assertEqual(errors, [], f"Ошибка на {rel}: {errors}")

    def test_webp_naming_and_location_rules(self):
        valid_webps = [
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/1-sem_physics_1-LEC_MalyshevaDA_LEC-10_1.webp",
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/1-sem_physics_1-LEC_MalyshevaDA_LEC-11_2.webp",
            "1-sem/physics/4-TST_MalyshevaDA_2026/1_mechanics/attachments/1-sem_physics_4-TST_MalyshevaDA_2026_1_mechanics_TST-02_1.webp",
        ]
        for rel in valid_webps:
            p = self.write_file(rel, b"WEBP", binary=True)
            self.assertEqual(vc.check_file(p)[0], [], rel)

        bad_webps = [
            # Не в attachments
            "1-sem/physics/1-LEC_MalyshevaDA/1-sem_physics_1-LEC_MalyshevaDA_LEC-10_1.webp",
            # В _attachments (старый формат)
            "1-sem/physics/1-LEC_MalyshevaDA/_attachments/1-sem_physics_1-LEC_MalyshevaDA_LEC-10_1.webp",
            # В корне предмета
            "1-sem/physics/attachments/1-sem_physics_LEC-10_1.webp",
            # Подпапка внутри attachments
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/sub/1-sem_physics_1-LEC_MalyshevaDA_LEC-10_1.webp",
            # Неверное имя (не совпадает с путём)
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/image.webp",
            "1-sem/physics/4-TST_MalyshevaDA_2026/1_mechanics/attachments/1-sem_physics_4-TST_MalyshevaDA_2026_TST-02_1.webp",
            # Запрещённый префикс PST или однозначный номер
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/1-sem_physics_1-LEC_MalyshevaDA_PST-01_1.webp",
            "1-sem/physics/1-LEC_MalyshevaDA/attachments/1-sem_physics_1-LEC_MalyshevaDA_LEC-1_1.webp",
        ]
        for rel in bad_webps:
            p = self.write_file(rel, b"WEBP", binary=True)
            errors, _ = vc.check_file(p)
            self.assertTrue(errors, f"Картинка {rel} должна отклоняться")


class TestYamlFrontmatter(BaseValidatorTest):
    def test_non_utf8_encoding_rejected(self):
        p = self.write_file(
            "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
            "---\ntitle: LEC-01 тест\n---\nТекст на русском\n".encode("cp1251"),
            binary=True,
        )
        errors, _ = vc.check_file(p)
        self.assertTrue(any("UTF-8" in e for e in errors))

    def test_utf8_bom_handled(self):
        p = self.write_file("_index.md", "\ufeff---\ntitle: Главная\n---\n\nТекст\n")
        errors, _ = vc.check_file(p)
        self.assertEqual(errors, [])

    def test_missing_or_broken_yaml_rejected(self):
        broken_contents = [
            "Просто текст без шапки",
            "---\ntitle: LEC-01 тест\nБез закрытия",
            "---\n---\nТекст",
            "---\n- просто список\n---\nТекст",
            "---\ntitle: [broken\n---\nТекст",
        ]
        for idx, content in enumerate(broken_contents):
            p = self.write_file(f"1-sem/physics/1-LEC_MalyshevaDA/LEC-0{idx}_test.md", content)
            errors, _ = vc.check_file(p)
            self.assertTrue(errors, f"Кейс #{idx} должен отклоняться")

    def test_index_requires_non_empty_title(self):
        for bad_index in ("---\ndate: 2026-09-02\n---\n", "---\ntitle: \"   \"\n---\n"):
            p = self.write_file("1-sem/_index.md", bad_index)
            errors, _ = vc.check_file(p)
            self.assertTrue(any("title" in e for e in errors))

    def test_note_title_must_match_prefix_and_number(self):
        bad_titles = [
            "",
            "введение в физику",
            "LEC-02 введение",
            "SEM-01 введение",
            "LEC-01: введение",
            "LEC-01",
        ]
        for title in bad_titles:
            content = self.make_note(title=title)
            p = self.write_file("1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md", content)
            errors, _ = vc.check_file(p)
            self.assertTrue(any("title" in e for e in errors), f"title='{title}' должен отклоняться")

    def test_date_validation(self):
        for good_date in ("2026-09-02", '"2026-09-02"'):
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(date=good_date),
            )
            self.assertEqual(vc.check_file(p)[0], [], good_date)

        for bad_date in ("02.09.2026", "2026/09/02", "2026-02-30", "2026-09-02T12:00:00", ""):
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(date=bad_date),
            )
            errors, _ = vc.check_file(p)
            self.assertTrue(any("date" in e for e in errors), f"date='{bad_date}' должна отклоняться")

    def test_tags_roles_rules(self):
        valid_tag_sets = [
            "  - author/ivan",
            "  - author/ivan\n  - typer/petr",
            "  - author/ivan\n  - author/petr\n  - typer/ivan",
            "  - author/ivan\n  - author/petr\n  - typer/maria\n  - editor/alex\n  - editor/olga",
        ]
        for tags in valid_tag_sets:
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(tags_block=tags),
            )
            self.assertEqual(vc.check_file(p)[0], [], f"Неожиданная ошибка для:\n{tags}")

        invalid_tag_sets = [
            # Нет author
            "  - typer/ivan",
            # Запрещённый смысловой тег
            "  - author/ivan\n  - физика",
            # Пустой ник
            "  - author/",
            # Один автор и он же typer (включая другой регистр)
            "  - author/Ivan\n  - typer/ivan",
            # Один автор, два typer и один из них сам автор
            "  - author/ivan\n  - typer/petr\n  - typer/ivan",
            # Несколько авторов без typer
            "  - author/ivan\n  - author/petr",
        ]
        for tags in invalid_tag_sets:
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(tags_block=tags),
            )
            errors, _ = vc.check_file(p)
            self.assertTrue(errors, f"Набор тегов должен отклоняться:\n{tags}")


class TestMarkdownBodyAndMath(BaseValidatorTest):
    def test_empty_or_code_only_note_rejected(self):
        for body in ("", "   \n\n  ", "```python\nprint(123)\n```\n"):
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=body),
            )
            errors, _ = vc.check_file(p)
            self.assertTrue(any("не содержит текста" in e for e in errors), repr(body))

    def test_unclosed_and_nested_code_blocks(self):
        valid_bodies = [
            "Текст\n\n```python\nx = 1\n```\n",
            "Текст\n\n~~~bash\necho ok\n~~~\n",
            "Текст\n\n````markdown\n```python\n#тег\n$$\n```\n````\n",
            "> [!NOTE]\n> Пример:\n>\n> ```python\n> x = 1\n> ```\n",
        ]
        for body in valid_bodies:
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=body),
            )
            self.assertEqual(vc.check_file(p)[0], [], body)

        bad_bodies = [
            "Текст\n\n```python\nx = 1\n",
            "Текст\n\n~~~~python\nx = 1\n```\n",
            "Текст\n\n~~~bash\necho 1\n",
            "> ```python\n> x = 1\n",
        ]
        for body in bad_bodies:
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=body),
            )
            errors, _ = vc.check_file(p)
            self.assertTrue(any("незакрытый блок кода" in e for e in errors), body)

    def test_display_math_valid_cases(self):
        valid_bodies = [
            "$$E = mc^2$$\n\nТекст после.\n",
            "Текст до.\n\n$$E = mc^2$$",
            "Текст.\n\n$$\na^2 + b^2 = c^2\n$$\n\nТекст.\n",
            "> [!IMPORTANT]\n> Формула:\n>\n> $$\n> F = ma\n> $$\n>\n> Пояснение.\n",
            "Внутристрочная $a = b$ и `$$ не формула $$` в коде.\n",
        ]
        for body in valid_bodies:
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=body),
            )
            self.assertEqual(vc.check_file(p)[0], [], body)

    def test_display_math_invalid_cases(self):
        invalid_bodies = [
            "Текст без отступа\n$$E = mc^2$$\n\nДальше.\n",
            "Текст.\n\n$$E = mc^2$$\nСразу текст.\n",
            "Формула $$E = mc^2$$ внутри строки.\n",
            "$$a = 1$$ + $$b = 2$$\n",
            "Текст перед $$ a = 1\n+ b\n$$\n\nДальше.\n",
            "Текст.\n\n$$\na = 1\n$$ и текст\n\nДальше.\n",
            "Текст.\n\n$$\na = 1\n",
        ]
        for body in invalid_bodies:
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=body),
            )
            errors, _ = vc.check_file(p)
            self.assertTrue(any("$$" in e for e in errors), f"Должно отклоняться:\n{body}")

    def test_absolute_local_paths_rejected(self):
        bad_links = [
            "[файл](file:///Users/test/a.md)",
            "![img](C:\\Users\\Student\\pic.png)",
            "![img](D:/study/pic.webp)",
            "[doc](/Users/alice/notes.md)",
            "[doc](/home/bob/notes.md)",
            "[doc](/root/secret.md)",
            "[doc](/tmp/temp.md)",
            "[share](\\\\server\\folder\\file.pdf)",
            "[[C:\\Notes\\file|Заметка]]",
            "![[/home/user/pic.webp]]",
        ]
        for link in bad_links:
            p = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=f"Смотри {link}\n"),
            )
            errors, _ = vc.check_file(p)
            self.assertTrue(any("абсолютный путь" in e for e in errors), link)

    def test_wikilinks_alias_rules(self):
        valid_body = (
            "Смотри [[LEC-00_intro|LEC-00 введение]], "
            "картинку ![[1-sem_physics_1-LEC_MalyshevaDA_LEC-01_1.webp]], "
            "[[#Локальный заголовок]] и код `[[без_алиаса]]`.\n"
        )
        p_ok = self.write_file(
            "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
            self.make_note(body=valid_body),
        )
        self.assertEqual(vc.check_file(p_ok)[0], [])

        p_idx = self.write_file(
            "_index.md",
            "---\ntitle: Главная\n---\n\n* [[README]]\n* [[CONTRIBUTING]]\n",
        )
        self.assertEqual(vc.check_file(p_idx)[0], [])

        for bad_wiki in ("[[LEC-00_intro]]", "[[LEC-00_intro|   ]]"):
            p_bad = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=f"Текст {bad_wiki}\n"),
            )
            errors, _ = vc.check_file(p_bad)
            self.assertTrue(any("алиас" in e for e in errors), bad_wiki)

    def test_body_hashtags_prohibited_with_safe_exclusions(self):
        safe_body = (
            "## Заголовок второго уровня\n\n"
            "Формула $a#1$ и ссылка [сайт](https://example.com/#anchor), "
            "вики [[LEC-00_intro#part|LEC-00 часть]], "
            "прямой URL https://example.com/#top и код `#не_тег`.\n"
        )
        p_ok = self.write_file(
            "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
            self.make_note(body=safe_body),
        )
        self.assertEqual(vc.check_file(p_ok)[0], [])

        for bad_tag in ("#важно", "#дописать", "#экзамен", "#todo_1"):
            p_bad = self.write_file(
                "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
                self.make_note(body=f"Текст с тегом {bad_tag}\n"),
            )
            errors, _ = vc.check_file(p_bad)
            self.assertTrue(any("Запрещённый хештег" in e for e in errors), bad_tag)


class TestMainCliAndReport(BaseValidatorTest):
    def run_main(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vc.main()
        return code, buf.getvalue()

    def test_main_without_changed_files_txt(self):
        code, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists("pr_report.md"))
        with open("pr_report.md", "r", encoding="utf-8") as f:
            report = f.read()
        self.assertIn("<!-- vlsu-contributing-bot -->", report)
        self.assertIn("changed_files.txt не найден", report)

    def test_main_success_and_warning_report(self):
        ok_note = self.write_file(
            "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_test.md",
            self.make_note(),
        )
        readme = self.write_file("README.md", "# Readme\n")
        self.write_file("changed_files.txt", f'"{ok_note}"\n{readme}\nmissing_deleted.md\n')

        code, stdout = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("::warning", stdout)

        with open("pr_report.md", "r", encoding="utf-8") as f:
            report = f.read()
        self.assertIn("## ✅ Проверка регламента пройдена", report)
        self.assertIn("Проверено файлов: **2**", report)
        self.assertIn("### Предупреждения", report)

    def test_main_failure_report(self):
        bad_note = self.write_file(
            "1-sem/physics/1-LEC_MalyshevaDA/LEC-01_ПлохоеИмя.md",
            self.make_note(body="Текст #важно\n"),
        )
        self.write_file("changed_files.txt", f"{bad_note}\n")

        code, stdout = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("::error", stdout)

        with open("pr_report.md", "r", encoding="utf-8") as f:
            report = f.read()
        self.assertIn("## ❌ Проверка регламента не пройдена", report)
        self.assertIn("### Ошибки", report)
        self.assertIn("LEC-01_ПлохоеИмя.md", report)


if __name__ == "__main__":
    unittest.main()

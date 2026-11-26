"""Pin the two reviewed My Mario metadata additions and exercise offline codegen.

IDs and historical category links were cross-checked against:
https://github.com/Odessakun/pixl.js/commit/b3aa858a38e51ac7cc4a614cc3c0defefdc309d5
https://github.com/8bitDream/AmiiboAPI/commit/c4a90748edf2277cc987bd901eef5d677f3422c4
Category 26 follows the existing wooden-block records; it is not a hardware or
gameplay compatibility claim. No tag payloads, keys or devices are used here.
"""
from contextlib import redirect_stdout
from hashlib import sha256
from pathlib import Path
import csv
import io
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

FW = Path(__file__).resolve().parents[2]
ADDITIONS = [
    ["0000000404431c02", "Mario (Melody Car) - My Mario Wooden Blocks", "马力欧(旋律车) - 我的马力欧木制积木"],
    ["000a000404451c02", "Toad - My Mario Wooden Blocks", "奇诺比奥 - 我的马力欧木制积木"],
]
# Structural digests ignore localized columns: the zh-Hans branch may update
# translations without weakening the reviewed ID/EN catalogue proof.
STRUCTURE_BASELINE = {
    "amiidb_amiibo.csv": (950, "a119b2d70dede844abdbb4456e917031cc9335ff407ea6a05921afc276c35986"),
    "amiidb_link.csv": (1342, "e42d079421a2da4a0310019c4e6e356eb7ec097cf48543ae37288d0bdfe0c9ae"),
}
GAME_STRUCTURE_SHA256 = "839ddf1cd9ad1641ca06ee96e42d22fd13c99d918e2407195a19ed2ac5dc29a9"


class CatalogDE39Tests(unittest.TestCase):
    @staticmethod
    def structure_digest(rows, fields):
        return sha256("".join(",".join(row[index] for index in fields) + "\n" for row in rows).encode()).hexdigest()

    def test_only_reviewed_entries_and_links_are_added(self):
        with (FW / "data/amiidb_amiibo.csv").open(encoding="utf8", newline="") as stream:
            amiibos = list(csv.reader(stream))
        with (FW / "data/amiidb_link.csv").open(encoding="utf8", newline="") as stream:
            links = list(csv.reader(stream))
        self.assertEqual(len(amiibos), 956)
        self.assertEqual(len(links), 1348)

        amiibo_prefix = [row[:] for row in amiibos[:950]]
        for aid, old, new in [
            ("018b000002460502", "Cyrrus", "Cyrus"),
            ("04d0000101960502", "[AC] 339 - Fritta", "[AC] 339 - Frita"),
            ("033f0001008f0502", "[AC] 076 - Jeramiah", "[AC] 076 - Jeremiah"),
            ('0a02000103b30502', '412 - C.J. ', '412 - C.J.'),
            ('0a0c000103c30502', '428 - Audie ', '428 - Audie'),
            ('0a0e000103c50502', '430 - Judy ', '430 - Judy'),
        ]:
            matched = [row for row in amiibo_prefix if row[0] == aid]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0][1], new)
            matched[0][1] = old
        for aid, old, new in [
            ("1f00000004c41e03", "Kirby", "Kirby (& Warp Star)"),
            ("1f03010004c91e03", "Bandana Waddle Dee", "Bandana Waddle Dee (& Winged Star)"),
            ("1f01000004c61e03", "Meta Knight", "Meta Knight (& Shadow Star)"),
        ]:
            matched = [row for row in amiibo_prefix if row[0] == aid]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0][1], new)
            matched[0][1] = old
        self.assertEqual(self.structure_digest(amiibo_prefix, (0, 1)),
                         STRUCTURE_BASELINE["amiidb_amiibo.csv"][1])

        link_prefix = [row[:] for row in links[:1342]]
        with (Path(__file__).parent / "fixtures" / "zelda_champion_notes_before_correction.csv").open(encoding="utf8", newline="") as stream:
            old_rows = list(csv.reader(stream))
        self.assertEqual(len(old_rows), 4)
        for line_number, old_row in zip((17, 23, 54, 60), old_rows):
            current = link_prefix[line_number - 1]
            self.assertEqual(current[:2], old_row[:2])
            self.assertNotEqual(current[:3], old_row[:3])
            current[2] = old_row[2]
        for aid in ("1f00000004c41e03", "1f03010004c91e03", "1f01000004c61e03",
                    "1f02000004c71e03", "1f04000004ca1e03"):
            matched = [row for row in link_prefix if row[0] == "75" and row[1] == aid]
            self.assertEqual(len(matched), 1)
            self.assertEqual(matched[0][2], "Train the rider as a Figure Player.")
            matched[0][2] = ""
        self.assertEqual(self.structure_digest(link_prefix, (0, 1, 2)),
                         STRUCTURE_BASELINE["amiidb_link.csv"][1])

        self.assertEqual(amiibos[-6:-4], ADDITIONS)
        self.assertEqual(amiibos[-4:-2], [
            ["1f00010004c51e03", "Sword Kirby (& Dragoon)", "剑士卡比(& 龙骑兵)"],
            ["1f02010004c81e03", "Noir Dedede (& Hydra)", "暗黑迪迪迪(& 九头蛇)"]])
        self.assertEqual(len({row[0] for row in amiibos}), 956)
        self.assertEqual(links[-6:-4], [["26", row[0], "", "", ""] for row in ADDITIONS])
        self.assertEqual(sum(row[0] == "26" for row in links), 37)
        self.assertEqual(links[-4:-2], [["75", row[0], "Train the rider as a Figure Player.",
                                        "将骑手作为手办玩家培养。", ""] for row in amiibos[-4:-2]])
        self.assertEqual(amiibos[-2:], [
            ["0100000004fd0902", "Young Link (Ocarina of Time)", "幼年林克(时之笛)"],
            ["0101000004ff0902", "Young Zelda (Ocarina of Time)", "幼年塞尔达(时之笛)"]])
        self.assertEqual(links[-2:], [["82", figure[0], "Unlocks a special mask that Link can wear.",
                                     "解锁林克可佩戴的特殊面具。", ""] for figure in amiibos[-2:]])

        with (FW / "data/amiidb_game.csv").open(encoding="utf8", newline="") as stream:
            games = list(csv.reader(stream))
        self.assertEqual(games[-2], ["82", "0", "The Legend of Zelda: Ocarina of Time",
                                     "塞尔达传说：时之笛", "5"])
        self.assertEqual(games[-1], ["255", "0", "Others", "未分类", "0"])
        games = [row for row in games if row[0] != "82"]
        for row in games:
            if row[0] == "49":
                self.assertEqual(row[2], "Yu-Gi-Oh! Rush Duel Saikyo Battle Royale")
                row[2] += " "
        self.assertEqual(self.structure_digest(games, (0, 1, 2, 4)), GAME_STRUCTURE_SHA256)

    def test_generated_metadata_compiles_and_all_links_resolve(self):
        compiler = shutil.which("gcc")
        self.assertIsNotNone(compiler, "Existing host gcc is required")
        with tempfile.TemporaryDirectory(prefix="pixl-de39-catalog-") as temporary:
            project = Path(temporary)
            script = project / "scripts/amiibo_db_gen.py"
            script.parent.mkdir()
            shutil.copyfile(FW / "scripts/amiibo_db_gen.py", script)
            (project / "data").mkdir()
            for filename in (*STRUCTURE_BASELINE, "amiidb_game.csv"):
                shutil.copyfile(FW / "data" / filename, project / "data" / filename)
            generated = project / "application/src/amiidb"
            generated.mkdir(parents=True)
            previous = None
            for _ in range(2):
                stdout = io.StringIO()
                with patch("urllib.request.urlopen", side_effect=AssertionError("offline network access")) as request, \
                        patch.object(sys, "argv", [str(script), "--offline"]), redirect_stdout(stdout):
                    runpy.run_path(str(script), run_name="__main__")
                request.assert_not_called()
                self.assertIn("Found 956 amiibo records.", stdout.getvalue())
                self.assertNotIn("uncategorized", stdout.getvalue())
                current = {path.name: path.read_bytes() for path in generated.glob("*.c")}
                if previous is not None:
                    self.assertEqual(current, previous, "Offline code generation must be deterministic")
                previous = current
            for filename in ("db_header.h", "db_search.c", "amiibo_model_details.h"):
                shutil.copyfile(FW / "application/src/amiidb" / filename, generated / filename)
            (generated / "settings.h").write_text(
                "enum { LANGUAGE_DE_DE, LANGUAGE_EN_US }; extern int catalog_language; extern int catalog_chinese; static int getLanguage(void){return catalog_language;} static int isChineseLanguage(void) { return catalog_chinese; }\n", encoding="utf8")
            main = generated / "test_catalog.c"
            main.write_text(r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "db_header.h"
int catalog_language = 0;
int catalog_chinese = 0;
static unsigned count_links(uint8_t id) {
    unsigned count = 0;
    for (const db_link_t *link = link_list; link->game_id; ++link)
        if (link->game_id == id) ++count;
    for (const db_game_t *game = game_list; game->game_id; ++game)
        if (game->parent_game_id == id) count += count_links(game->game_id);
    return count;
}
int main(void) {
    assert(amiibo_list_size == 956);
    for (size_t i = 0; i < amiibo_list_size; ++i) {
        const db_amiibo_t *amiibo = &amiibo_list[i];
        assert(get_amiibo_by_id(amiibo->head, amiibo->tail) == amiibo);
        if (i) {
            uint64_t before = ((uint64_t)amiibo_list[i - 1].head << 32) | amiibo_list[i - 1].tail;
            uint64_t current = ((uint64_t)amiibo->head << 32) | amiibo->tail;
            assert(before < current);
        }
    }
    unsigned links = 0;
    for (const db_link_t *link = link_list; link->game_id; ++link) {
        assert(link->amiibo_index < amiibo_list_size);
        const db_amiibo_t *linked = &amiibo_list[link->amiibo_index];
        assert(get_amiibo_by_id(linked->head, linked->tail) == linked);
        unsigned matching_games = 0;
        for (const db_game_t *game = game_list; game->game_id; ++game)
            matching_games += game->game_id == link->game_id;
        assert(matching_games == 1);
        ++links;
    }
    const db_amiibo_t *young_link = get_amiibo_by_id(0x01000000, 0x04fd0902);
    const db_amiibo_t *young_zelda = get_amiibo_by_id(0x01010000, 0x04ff0902);
    assert(young_link && young_zelda && count_links(82) == 2);
    assert(!strcmp(get_amiibo_display_name(young_link), "Junger Link (Ocarina of Time)"));
    assert(!strcmp(get_amiibo_display_name(young_zelda), "Junge Zelda (Ocarina of Time)"));
    catalog_language = 1;
    assert(!strcmp(get_amiibo_display_name(young_link), "Young Link (Ocarina of Time)"));
    assert(!strcmp(get_amiibo_display_name(young_zelda), "Young Zelda (Ocarina of Time)"));
    assert(links == 1348 && count_links(26) == 37 && count_links(75) == 7);
    assert(get_link_by_id(75, 0x1f000100, 0x04c51e03));
    assert(get_link_by_id(75, 0x1f020100, 0x04c81e03));
    for (const db_game_t *game = game_list; game->game_id; ++game)
        assert(game->link_cnt == count_links(game->game_id));
    const db_amiibo_t *mario = get_amiibo_by_id(0x00000004, 0x04431c02);
    const db_amiibo_t *toad = get_amiibo_by_id(0x000a0004, 0x04451c02);
    assert(mario && toad);
    assert(strcmp(get_amiibo_display_name(mario), "Mario (Melody Car) - My Mario Wooden Blocks") == 0);
    assert(strcmp(get_amiibo_display_name(toad), "Toad - My Mario Wooden Blocks") == 0);
    assert(get_link_by_id(26, mario->head, mario->tail));
    assert(get_link_by_id(26, toad->head, toad->tail));
    assert(!is_valid_amiibo_v3(mario->head, mario->tail));
    assert(!is_valid_amiibo_v3(toad->head, toad->tail));
    catalog_chinese = 1;
    assert(!strcmp(get_amiibo_display_name(young_link), "幼年林克(时之笛)"));
    assert(!strcmp(get_amiibo_display_name(young_zelda), "幼年塞尔达(时之笛)"));
    puts("PASS: 956 unique sorted IDs, 1348 links, every category count and two My Mario lookups");
    return 0;
}
''', encoding="utf8")
            executable = generated / "test_catalog.exe"
            build = subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                                    "-Wno-unused-parameter", "-Wno-missing-field-initializers",
                                    *map(str, generated.glob("*.c")), "-o", str(executable)],
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS: 956 unique sorted IDs, 1348 links", result.stdout)


if __name__ == "__main__":
    unittest.main()

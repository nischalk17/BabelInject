from pathlib import Path

from aie.analysis.report_check import known_counts, unmatched_fractions

HEADER = "model_tag,defense,attack,language,channel,metric,k,n\n"


def write_table(folder: Path) -> None:
    folder.mkdir()
    (folder / "t.csv").write_text(
        HEADER
        + "m,none,A,en,file,asr,3,10\n"
        + "m,none,A,en,email,asr,2,10\n"
        + "m,none,A,hi,user,asr,9,10\n",
        encoding="utf-8",
    )


def test_cells_pooled_sums_and_injected_only_sums_are_known(tmp_path: Path) -> None:
    write_table(tmp_path / "summary")
    known = known_counts([tmp_path / "summary"])
    assert (3, 10) in known  # a cell
    assert (5, 20) in known  # pooled over channels, control row left out
    assert (14, 30) in known  # pooled over everything, including the control
    assert (4, 10) not in known


def test_unmatched_fractions_are_reported_with_their_line(tmp_path: Path) -> None:
    write_table(tmp_path / "summary")
    known = known_counts([tmp_path / "summary"])
    doc = tmp_path / "doc.md"
    doc.write_text("ok 3/10 and 5 of 20\nstale 4 of 10, and 1 of 1 is ignored\n", encoding="utf-8")
    scanned, missing = unmatched_fractions([doc], known)
    assert scanned == 3
    assert missing == [(doc, 2, 4, 10)]

import pytest

from jupynium.buffer import JupyniumBuffer


def test_buffer_1():
    buffer = JupyniumBuffer(["a", "b", "c", "# %%", "d", "e", "f"])
    assert buffer.num_rows_per_cell == [3, 4]
    assert buffer.cell_types == ["header", "code"]


def test_buffer_markdown():
    buffer = JupyniumBuffer(["a", "b", "c", "# %%%", "d", "# %%", "f"])
    assert buffer.num_rows_per_cell == [3, 2, 2]
    assert buffer.cell_types == ["header", "markdown", "code"]


def test_buffer_markdown_2(jupbuf1):
    assert jupbuf1.num_rows_per_cell == [3, 2, 2]
    assert jupbuf1.cell_types == ["header", "markdown", "code"]


def test_get_cell_start_row(jupbuf1):
    assert jupbuf1.get_cell_start_row(0) == 0
    assert jupbuf1.get_cell_start_row(1) == 3
    assert jupbuf1.get_cell_start_row(2) == 5


def test_get_cell_index_from_row(jupbuf1):
    assert jupbuf1.get_cell_index_from_row(0) == (0, 0, 0)
    assert jupbuf1.get_cell_index_from_row(1) == (0, 0, 1)
    assert jupbuf1.get_cell_index_from_row(2) == (0, 0, 2)
    assert jupbuf1.get_cell_index_from_row(3) == (1, 3, 0)
    assert jupbuf1.get_cell_index_from_row(4) == (1, 3, 1)
    assert jupbuf1.get_cell_index_from_row(5) == (2, 5, 0)
    assert jupbuf1.get_cell_index_from_row(6) == (2, 5, 1)


def test_check_validity(jupbuf1):
    jupbuf1._check_validity()


@pytest.mark.xfail(raises=Exception)
def test_check_invalid():
    buffer = JupyniumBuffer(["a", "b", "c", "'''%%%", "d", "%%'''", "f"])
    # manually modify the buffer
    buffer.buf.append("g")
    buffer._check_validity()


def test_num_cells(jupbuf1):
    assert jupbuf1.num_cells == 3
    assert jupbuf1.num_cells_in_notebook == 2


def test_num_cells_2():
    buffer = JupyniumBuffer([""])
    assert buffer.num_cells == 1
    assert buffer.num_cells_in_notebook == 1


@pytest.mark.parametrize(
    "content,lines,start_row,old_end_row,new_end_row",
    [
        (["a", "b", "c", "# %%", "d", "e", "f"], ["# %%%", "g"], 3, 4, 5),
        (["b", "c", "# %%", "d", "e", "f"], ["# %%%", "g"], 3, 4, 5),
        (["b", "# %%", "d", "f", "f", "f", "f"], ["# %%"], 3, 4, 4),
        (["b", "# %%", "d", "f", "f", "f", "f"], ["# %%"], 3, 3, 4),
        (["b", "# %%", "d", "# %%", "f", "f", "f"], [""], 1, 4, 2),
        (["b", "# %%", "d", "# %%", "f", "f", "f"], [], 2, 5, 2),
        (["b", "# %%", "d", "# %%", "f", "f", "f"], [], 1, 5, 1),
    ],
)
def test_on_lines_cellinfo(content, lines, start_row, old_end_row, new_end_row):
    buffer = JupyniumBuffer(content)
    # change # %% to # %%% and g
    buffer._on_lines_update_buf(lines, start_row, old_end_row, new_end_row)

    fully_analysed_buf = JupyniumBuffer(buffer.buf)
    assert buffer.num_rows_per_cell == fully_analysed_buf.num_rows_per_cell
    assert buffer.cell_types == fully_analysed_buf.cell_types


@pytest.mark.parametrize(
    "content,lines,start_row,old_end_row,new_end_row,final_content",
    [
        (
            ["a", "b", "c", "# %%", "d", "e", "f"],
            ["# %%%", "g"],
            3,
            4,
            5,
            ["a", "b", "c", "# %%%", "g", "d", "e", "f"],
        ),
        (
            ["b", "c", "# %%", "d", "e", "f"],
            ["# %%%", "g"],
            3,
            4,
            5,
            ["b", "c", "# %%", "# %%%", "g", "e", "f"],
        ),
        (
            ["b", "# %%", "d", "f", "f", "f", "f"],
            ["# %%"],
            3,
            4,
            4,
            ["b", "# %%", "d", "# %%", "f", "f", "f"],
        ),
        (
            ["b", "# %%", "d", "f", "f", "f", "f"],
            ["# %%"],
            3,
            3,
            4,
            ["b", "# %%", "d", "# %%", "f", "f", "f", "f"],
        ),
        (
            ["b", "# %%", "d", "# %%", "f", "f", "f"],
            [],
            1,
            4,
            1,
            ["b", "f", "f", "f"],
        ),
    ],
)
def test_on_lines_content(
    content, lines, start_row, old_end_row, new_end_row, final_content
):
    buffer = JupyniumBuffer(content)
    # change # %% to # %%% and g
    buffer._on_lines_update_buf(lines, start_row, old_end_row, new_end_row)

    final_buf = JupyniumBuffer(final_content)
    assert buffer == final_buf

from __future__ import annotations

import logging

from pkg_resources import resource_stream

from .jupyter_notebook_selenium import insert_cell_at

logger = logging.getLogger(__name__)


set_cell_text_js_code = (
    resource_stream("jupynium", "js/set_cell_text.js").read().decode("utf-8")
)


def _process_cell_type(cell_type: str) -> str:
    if cell_type == "markdown (jupytext)":
        return "markdown"

    return cell_type


def _process_cell_types(cell_types: list[str]) -> list[str]:
    """
    Return the cell types, e.g. ["markdown", "code", "header"].
    markdown (jupytext) is converted to markdown.
    """
    return [_process_cell_type(cell_type) for cell_type in cell_types]


class JupyniumBuffer:
    """
    This class mainly deals with the Nvim buffer and its cell information.
    This does have a functionality to sync with the Notebook.
    """

    def __init__(
        self,
        buf: list[str] = [""],
        header_cell_type="header",
    ):
        """
        self.buf is a list of lines of the nvim buffer,

        Args:
            header_cell_type (str, optional): Use only when partial update.
            header_cell_separator (str, optional): Use only when partial update.
        """
        self.buf = buf
        if self.buf == [""]:
            # each cell's row length. 0-th cell is not a cell, but it's the header.
            # You can put anything above and it won't be synced to Jupyter Notebook.
            self.num_rows_per_cell: list[int] = [1]

            self.cell_types = ["header"]  # 0-th cell is not a cell.
        else:
            self.full_analyse_buf(header_cell_type)

    def full_analyse_buf(self, header_cell_type="header"):
        """
        Main parser for the jupynium format (*.ju.*).
        This function needs to support partial update.

        E.g. by looking at 1 line of change, it should be able to understand if:
            - the change is within a cell
            - cell creation/deletion
            - cell type change

        During the partial update, the header cell will be continuation from
        the existing cell.
        We don't know if it will be header/cell/markdown.
        So we need to pass the header_cell_type.
        (This is deprecated, in favour of self.get_cells_text() dealing with
        content processing.)

        Args:
            header_cell_type (str, optional): Used to be used only when partial update.
                                              Now deprecated.
        """
        num_rows_this_cell = 0
        num_rows_per_cell = []
        cell_types = [header_cell_type]
        for row, line in enumerate(self.buf):
            if (
                line.startswith("# %%%")
                or line.startswith('"""%%')
                or line.startswith("'''%%")
            ):
                num_rows_per_cell.append(num_rows_this_cell)
                num_rows_this_cell = 1
                cell_types.append("markdown")
            elif line.startswith("# %% [md]") or line.startswith("# %% [markdown]"):
                num_rows_per_cell.append(num_rows_this_cell)
                num_rows_this_cell = 1
                cell_types.append("markdown (jupytext)")
            elif (
                line.strip() == "# %%"
                or line.startswith('%%"""')
                or line.startswith("%%'''")
            ):
                num_rows_per_cell.append(num_rows_this_cell)
                num_rows_this_cell = 1
                cell_types.append("code")
            else:
                num_rows_this_cell += 1
        num_rows_per_cell.append(num_rows_this_cell)

        self.num_rows_per_cell = num_rows_per_cell
        self.cell_types = cell_types

    def _process_cell_text(self, cell_type, lines: list[str]):
        """
        Assuming that lines is just one cell's content, process it.
        """
        if cell_type == "code":
            return "\n".join(
                line[2:] if line.startswith("# %") else line for line in lines
            )
        elif cell_type == "markdown (jupytext)":
            if len(lines) > 0 and lines[0] == '"""':
                return "\n".join(line for line in lines if not line.startswith('"""'))
            else:
                return "\n".join(
                    line[2:] if line.startswith("# ") else line for line in lines
                )
        else:
            # header, markdown
            return "\n".join(lines)

    def get_cells_text(
        self, start_cell_idx: int, end_cell_idx: int, strip: bool = True
    ) -> list[str]:
        """
        Get processed cell text.
        In a code cell, remove comments for the magic commands.
        e.g. '# %time' -> '%time'
        In a markdown cell, remove the leading # from the lines or multiline string.
        e.g. '# # Markdown header' -> '# Markdown header'
        """

        if start_cell_idx == 0:
            start_row_offset = 0
        else:
            start_row_offset = 1

        texts_per_cell = []
        start_row = self.get_cell_start_row(start_cell_idx)
        texts_per_cell.append(
            self._process_cell_text(
                self.cell_types[start_cell_idx],
                self.buf[
                    start_row
                    + start_row_offset : start_row
                    + self.num_rows_per_cell[start_cell_idx]
                ],
            )
        )

        for cell_idx in range(start_cell_idx + 1, end_cell_idx + 1):
            start_row += self.num_rows_per_cell[cell_idx - 1]
            texts_per_cell.append(
                self._process_cell_text(
                    self.cell_types[cell_idx],
                    self.buf[
                        start_row + 1 : start_row + self.num_rows_per_cell[cell_idx]
                    ],
                )
            )

        if strip:
            texts_per_cell = [x.strip() for x in texts_per_cell]

        return texts_per_cell

    def get_cell_text(self, cell_idx: int, strip: bool = True) -> str:
        return self.get_cells_text(cell_idx, cell_idx, strip=strip)[0]

    def process_on_lines(
        self, driver, strip, lines, start_row, old_end_row, new_end_row
    ):
        (
            notebook_cell_operations,
            modified_cell_idx_start,
            modified_cell_idx_end,
        ) = self._on_lines_update_buf(lines, start_row, old_end_row, new_end_row)
        self._apply_cell_operations(driver, notebook_cell_operations)

        num_cells = self.num_cells_in_notebook
        num_cells_in_notebook = driver.execute_script(
            "return Jupyter.notebook.ncells();"
        )

        if num_cells_in_notebook != num_cells:
            self.full_sync_to_notebook(driver, strip=strip)
        else:
            self._partial_sync_to_notebook(
                driver, modified_cell_idx_start, modified_cell_idx_end, strip=strip
            )

    def _on_lines_update_buf(self, lines, start_row, old_end_row, new_end_row):
        """
        Replace start_row:old_end_row to lines from self.buf
        """

        # Analyse how many cells are removed
        notebook_cell_delete_operations = []
        notebook_cell_operations = []

        try:
            cell_idx, _, row_within_cell = self.get_cell_index_from_row(start_row)

            if row_within_cell == 0 and cell_idx > 0:
                # If the row is the first row of a cell, and it's not the first cell,
                # then it's a cell separator.
                row_within_cell = self.num_rows_per_cell[cell_idx - 1]
                cell_idx -= 1
        except IndexError:
            assert start_row == old_end_row == self.num_rows
            cell_idx = self.num_cells - 1
            row_within_cell = self.num_rows_per_cell[-1]

        modified_cell_idx_start = cell_idx

        lines_to_remove = old_end_row - start_row

        while lines_to_remove > 0:
            if row_within_cell < self.num_rows_per_cell[cell_idx]:
                # If the row is within the cell, then it's a cell content.
                self.num_rows_per_cell[cell_idx] -= 1
            else:
                # If the row is not within the cell, then it's a cell separator.
                notebook_cell_delete_operations.append(("delete", cell_idx + 1, None))
                self.num_rows_per_cell[cell_idx] += (
                    self.num_rows_per_cell[cell_idx + 1] - 1
                )
                del self.num_rows_per_cell[cell_idx + 1]
                del self.cell_types[cell_idx + 1]
            lines_to_remove -= 1

        # Analyse how many cells are added
        new_lines_buf = JupyniumBuffer(
            lines,
            header_cell_type=self.cell_types[
                cell_idx
            ],  # This is required as we're analysing partially.
        )
        if new_lines_buf.num_cells - 1 == 0:
            self.num_rows_per_cell[cell_idx] += new_lines_buf.num_rows_per_cell[0]
            notebook_cell_operations = notebook_cell_delete_operations
        else:
            num_delete_cells = len(notebook_cell_delete_operations)
            num_insert_cells = new_lines_buf.num_cells - 1
            if num_delete_cells > num_insert_cells:
                notebook_cell_operations = notebook_cell_delete_operations[
                    :num_insert_cells
                ]
            elif num_delete_cells < num_insert_cells:
                notebook_cell_operations = [
                    (
                        "cell_type",
                        cell_idx + 1,
                        _process_cell_types(
                            new_lines_buf.cell_types[
                                1 : 1 + len(notebook_cell_delete_operations)
                            ]
                        ),
                    )
                ]
                notebook_cell_operations.append(
                    (
                        "insert",
                        cell_idx + 1,
                        _process_cell_types(
                            new_lines_buf.cell_types[
                                1 + len(notebook_cell_delete_operations) :
                            ]
                        ),
                    )
                )
            else:
                notebook_cell_operations = [
                    (
                        "cell_type",
                        cell_idx + 1,
                        _process_cell_types(new_lines_buf.cell_types[1:]),
                    )
                ]

            num_tail_rows = self.num_rows_per_cell[cell_idx] - row_within_cell
            self.num_rows_per_cell[cell_idx] = (
                row_within_cell + new_lines_buf.num_rows_per_cell[0]
            )
            new_lines_buf.num_rows_per_cell[-1] += num_tail_rows
            self.num_rows_per_cell[
                cell_idx + 1 : cell_idx + 1
            ] = new_lines_buf.num_rows_per_cell[1:]
            self.cell_types[cell_idx + 1 : cell_idx + 1] = new_lines_buf.cell_types[1:]

        modified_cell_idx_end = modified_cell_idx_start + new_lines_buf.num_cells - 1

        # Now actually replace the lines
        # Optimisation: if the number of lines is not changed,
        # which is most of the cases,
        # then we can just replace the the strings in the list
        # instead of modifying list itself.
        if old_end_row == new_end_row:
            for i, line in enumerate(lines):
                self.buf[start_row + i] = line
        else:
            # If the number of lines is changed,
            # then we need to remove the old lines and insert the new lines.
            self.buf[start_row:old_end_row] = lines

        return notebook_cell_operations, modified_cell_idx_start, modified_cell_idx_end

    def _apply_cell_operations(self, driver, notebook_cell_operations):
        # Remove / create cells in Notebook
        for operation, cell_idx, cell_types in notebook_cell_operations:
            nb_cell_idx = cell_idx - 1
            if operation == "delete":
                logger.info(f"Deleting cell {nb_cell_idx} from Notebook")
                driver.execute_script(
                    "Jupyter.notebook.delete_cell(arguments[0]);", nb_cell_idx
                )
            elif operation == "insert":
                for i, cell_type in enumerate(cell_types):
                    logger.info(f"Inserting cell {nb_cell_idx + i} from Notebook")
                    insert_cell_at(driver, cell_type, nb_cell_idx + i)
            elif operation == "cell_type":
                for i, cell_type in enumerate(cell_types):
                    logger.info(
                        f"Cell {nb_cell_idx + i} type change to {cell_type} "
                        "from Notebook"
                    )
                    # "markdown" or "markdown (jupytext)"
                    if cell_type == "markdown":
                        driver.execute_script(
                            "Jupyter.notebook.cells_to_markdown([arguments[0]]);",
                            nb_cell_idx + i,
                        )
                    elif cell_type == "code":
                        driver.execute_script(
                            "Jupyter.notebook.cells_to_code([arguments[0]]);",
                            nb_cell_idx + i,
                        )
                    else:
                        raise ValueError(f"Unknown cell type {cell_type}")

    def get_cell_start_row(self, cell_idx):
        return sum(self.num_rows_per_cell[:cell_idx])

    def get_cell_index_from_row(
        self,
        row: int,
        num_rows_per_cell: list[int] | None = None,
        raise_out_of_bound: bool = True,
    ) -> tuple[int, int, int]:
        """
        Returns the cell index for the given row.

        Args:
            row (int): row index
            num_rows_per_cell (list): number of rows per cell. If None, use self.num_rows_per_cell
            raise_out_of_bound (bool): whether to raise an IndexError if the row is out of bound

        Returns:
            int: cell index
            int: cell start row
            int: row index within the cell
        """  # noqa: E501
        if num_rows_per_cell is None:
            num_rows_per_cell = self.num_rows_per_cell

        cell_start_row = 0
        i = 0
        for i, num_rows in enumerate(num_rows_per_cell):
            if cell_start_row + num_rows > row:
                return i, cell_start_row, row - cell_start_row
            cell_start_row += num_rows

        # Out of bound. Could be adding a new line.
        if raise_out_of_bound:
            raise IndexError(f"Could not find cell for row {row}")
        else:
            return i, cell_start_row, row - cell_start_row

    def _check_validity(self):
        assert len(self.buf) == sum(self.num_rows_per_cell)
        assert len(self.cell_types) == len(self.num_rows_per_cell)
        assert self.cell_types[0] == "header"
        assert all(
            x in ("code", "markdown", "markdown (jupytext)")
            for x in self.cell_types[1:]
        )

    def _partial_sync_to_notebook(
        self, driver, start_cell_idx, end_cell_idx, strip=True
    ):
        """
        Cell 1 in JupyniumBuffer is cell 0 in Notebook
        Args are inclusive range in ju.py JupyniumBuffer
        """
        assert start_cell_idx <= end_cell_idx < self.num_cells

        if self.num_cells == 1:
            # Markdown file
            driver.execute_script(
                "Jupyter.notebook.cells_to_markdown([0]);"
                "Jupyter.notebook.get_cell(0).set_text(arguments[0]);"
                "Jupyter.notebook.get_cell(0).render()",
                "\n".join(self.buf),
            )
        else:
            # Notebook file

            if end_cell_idx == 0:
                # Nothing to update
                return

            if start_cell_idx == 0:
                start_cell_idx = 1

            texts_per_cell = self.get_cells_text(start_cell_idx, end_cell_idx, strip)

            code_cell_indices = [
                start_cell_idx + i
                for i, cell_type in enumerate(
                    self.cell_types[start_cell_idx : end_cell_idx + 1]
                )
                if cell_type == "code"
            ]
            markdown_cell_indices = [
                start_cell_idx + i
                for i, cell_type in enumerate(
                    self.cell_types[start_cell_idx : end_cell_idx + 1]
                )
                if cell_type.startswith("markdown")
                # "markdown" or "markdown (jupytext)"
            ]

            if len(code_cell_indices) > 0:
                logger.info(f"Converting to code cells: {code_cell_indices}")
                for i in code_cell_indices:
                    driver.execute_script(
                        "Jupyter.notebook.cells_to_code([arguments[0]]);", i - 1
                    )

            if len(markdown_cell_indices) > 0:
                logger.info(f"Converting to markdown cells: {markdown_cell_indices}")
                for i in markdown_cell_indices:
                    driver.execute_script(
                        "Jupyter.notebook.cells_to_markdown([arguments[0]]);", i - 1
                    )

            # This will render markdown cells
            driver.execute_script(
                set_cell_text_js_code,
                start_cell_idx - 1,
                end_cell_idx - 1,
                *texts_per_cell,
            )

    def full_sync_to_notebook(self, driver, strip=True):
        # Full sync with notebook.
        # WARNING: syncing may result in data loss.
        num_cells = self.num_cells_in_notebook
        num_cells_in_notebook = driver.execute_script(
            "return Jupyter.notebook.ncells();"
        )
        if num_cells > num_cells_in_notebook:
            for _ in range(num_cells - num_cells_in_notebook):
                driver.execute_script("Jupyter.notebook.insert_cell_below();")
        elif num_cells < num_cells_in_notebook:
            for _ in range(num_cells_in_notebook - num_cells):
                driver.execute_script("Jupyter.notebook.delete_cell(-1);")

        self._partial_sync_to_notebook(driver, 0, self.num_cells - 1, strip=strip)

    @property
    def num_cells(self):
        return len(self.num_rows_per_cell)

    @property
    def num_cells_in_notebook(self):
        """
        If the buffer has 1 cell (no separator), it will be treated as markdown file.
        If the buffer has more than 1 cell, it will be treated as notebook.

        Notebook always has 1 cell minimum.
        """
        return max(self.num_cells - 1, 1)

    @property
    def num_rows(self):
        return len(self.buf)

    def __eq__(self, other):
        return (
            self.buf == other.buf
            and self.num_rows_per_cell == other.num_rows_per_cell
            and self.cell_types == other.cell_types
        )

import logging

logger = logging.getLogger(__name__)


def insert_cell_at(driver, cell_type, cell_idx):
    """
    Instead of insert_cell_below or insert_cell_above, it will select based on the given index.
    If cell_idx == 0, insert above, otherwise insert below.
    """
    if cell_idx == 0:
        logger.info(f"New {cell_type} cell created above cell 0")
        driver.execute_script(
            "Jupyter.notebook.insert_cell_above(arguments[0], arguments[1]);",
            cell_type,
            cell_idx,
        )
    else:
        logger.info(f"New {cell_type} cell created below cell {cell_idx-1}")
        driver.execute_script(
            "Jupyter.notebook.insert_cell_below(arguments[0], arguments[1]);",
            cell_type,
            cell_idx - 1,
        )

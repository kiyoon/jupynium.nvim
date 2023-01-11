var cell_index_cursor = arguments[0]
var cell_index_visual_start = arguments[1]

var select_start = Math.min(cell_index_cursor, cell_index_visual_start)
var select_end = Math.max(cell_index_cursor, cell_index_visual_start)

var all_cells = Jupyter.notebook.get_cells()

var updated = false

for (var i = 0; i < all_cells.length; i++) {
  var cell = all_cells[i]
  if (i >= select_start && i <= select_end) {
    if (!cell.selected) {
      cell.select()
      updated = true
    }
  } else {
    if (cell.selected) {
      cell.unselect()
      updated = true
    }
  }
}

return updated

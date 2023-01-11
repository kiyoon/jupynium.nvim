var start_cell_idx = arguments[0]
var end_cell_idx = arguments[1]
var cells = Jupyter.notebook.get_cells()

var text_idx = 2
for (var i = start_cell_idx; i <= end_cell_idx; i++, text_idx++) {
  cells[i].set_text(arguments[text_idx])
  if (cells[i].cell_type === 'markdown') {
    cells[i].render()
  }
}

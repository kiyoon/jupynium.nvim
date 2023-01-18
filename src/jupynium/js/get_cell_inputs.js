var cells = Jupyter.notebook.get_cells()
var cell_types = Array(cells.length)
var inputs = Array(cells.length)
for (i = 0; i < cells.length; i++) {
  cell_types[i] = cells[i].cell_type
  inputs[i] = cells[i].get_text()
}
return [cell_types, inputs]

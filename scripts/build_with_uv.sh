
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <path-to-venv>"
    exit 1
fi

# check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed"
    exit 1
fi

path_to_venv="$1"

if [[ -f "$path_to_venv" ]]; then
    echo "Error: $path_to_venv is a file"
    exit 1
fi

if [[ ! -d "$path_to_venv" ]]; then
    uv venv "$path_to_venv"
fi

source "$path_to_venv/bin/activate"
uv pip install .
mkdir -p "$HOME/.local/bin"
# ln -sf "$path_to_venv/bin/jupynium" "$HOME/.local/bin"

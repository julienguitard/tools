# rename-papers

Rename research paper PDFs based on their content using OpenAI.

```
2510.12269v3.pdf  →  2510.12269v3.tensor_logic_for_ai.pdf
0310054.pdf       →  0310054_kleene_algebra_domain.pdf
```

## Setup

```bash
# 1. Clone / copy this folder to ~/tools/
cp -r rename-papers ~/tools/rename-papers
cd ~/tools/rename-papers

# 2. Create venv + install deps
make setup

# 3. Add your API key
$EDITOR .env
```

## Usage

```bash
# Preview (recommended first)
make dry-run FOLDER=~/Downloads/papers

# Apply renames
make run FOLDER=~/Downloads/papers
```

### Global access (optional)

```bash
# Symlink the wrapper into your PATH
ln -s ~/tools/rename-papers/bin/rename-papers ~/.local/bin/rename-papers

# Then from anywhere:
rename-papers ~/Downloads/papers --dry-run
rename-papers ~/Downloads/papers
rename-papers ~/Downloads/papers --model gpt-4o
```

## Files

```
rename-papers/
├── .env.example          # Template — copy to .env
├── .env                  # Your secrets (gitignored)
├── .venv/                # Python virtual environment
├── Makefile              # setup / run / clean targets
├── README.md
├── bin/
│   └── rename-papers     # Shell wrapper for ~/.local/bin/
├── rename_papers.py      # Main script
└── requirements.txt
```

## .gitignore reminder

If you version this, add:

```
.env
.venv/
__pycache__/
```

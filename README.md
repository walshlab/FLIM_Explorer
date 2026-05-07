# FLIMExplorer

Interactive Dash-based tools for analyzing fluorescence lifetime imaging microscopy (FLIM) datasets.

---

# Installation

## 1. Install prerequisites

### Conda (recommended)

Install either:

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html?utm_source=chatgpt.com) (recommended; lightweight installer)
- [Anaconda](https://www.anaconda.com/download?utm_source=chatgpt.com)

### Git

Install :contentReference[oaicite:2]{index=2} from:

- [Git download page](https://git-scm.com/downloads?utm_source=chatgpt.com)

Verify installation:

```bash
git --version
conda --version
```

---

## 2. Clone the repository

Open a terminal (Anaconda Prompt, PowerShell, Terminal, or terminal in VS Code).

Clone the repository:

```bash
git clone https://github.com/walshlab/FLIM_Explorer.git
```

Move into the project directory:

```bash
cd FLIM_Explorer
```

---

## 3. Create the conda environment

Create the environment from the provided `environment.yml` file:

```bash
conda env create -f environment.yml
```

Activate the environment:

```bash
conda activate flimexplorer
```

> Note: the environment name may differ depending on the `name:` field inside `environment.yml`.

---

## 4. Install FLIMExplorer in editable mode

Install the package in editable/development mode:

```bash
pip install -e .
```

This command:
- installs FLIMExplorer into the active environment
- links the local source code directly to the environment
- allows local code edits without reinstalling the package

Editable mode is recommended for:
- development
- debugging
- modifying analysis workflows
- contributing to the project

---

# Running FLIMExplorer

## Launch the main application

```bash
python -m flimexplorer.app
```

---

## Launch the IO table generator tool

```bash
python -m flimexplorer.tools.generate_input_table
```

---

# Updating FLIMExplorer

Pull the latest changes from GitHub:

```bash
git pull
```

If dependencies changed, update the environment:

```bash
conda env update -f environment.yml
```

---

# Troubleshooting

## `ModuleNotFoundError`

If you encounter missing package errors such as:

```bash
ModuleNotFoundError: No module named 'matplotlib'
```

try updating the environment:

```bash
conda env update -f environment.yml
```

or manually install the missing package:

```bash
conda install matplotlib
```

---

## Verify the correct environment is active

Check available conda environments:

```bash
conda info --envs
```

The active environment is marked with `*`.

---

## Reinstall the package

If changes are not being recognized, reinstall in editable mode:

```bash
pip install -e .
```

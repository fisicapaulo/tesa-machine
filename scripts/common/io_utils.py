import json
import yaml
from pathlib import Path


def ensure_dir(path):
    """
    Garante que o diretório exista. Aceita str ou Path.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path):
    """
    Lê um arquivo JSON e retorna o objeto Python.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj, *, indent=2):
    """
    Escreve um objeto Python em JSON.
    """
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def read_yaml(path):
    """
    Lê um arquivo YAML e retorna o objeto Python.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_yaml(path, obj):
    """
    Escreve um objeto Python em YAML.
    """
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def write_text(path, text):
    """
    Escreve texto simples em um arquivo.
    """
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_text(path):
    """
    Lê texto simples de um arquivo.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def file_exists(path):
    """
    Verifica se um arquivo existe.
    """
    return Path(path).exists()


def list_files(dir_path, pattern="*"):
    """
    Lista arquivos em um diretório com um padrão glob.
    """
    p = Path(dir_path)
    return sorted([str(x) for x in p.glob(pattern) if x.is_file()])


def list_dirs(dir_path):
    """
    Lista subdiretórios imediatos.
    """
    p = Path(dir_path)
    return sorted([str(x) for x in p.iterdir() if x.is_dir()])


if __name__ == "__main__":
    # Pequeno teste manual
    tmp = ensure_dir("build/test_io")
    write_json(tmp / "sample.json", {"ok": True, "n": 3})
    write_yaml(tmp / "sample.yaml", {"ok": True, "n": 3})
    write_text(tmp / "hello.txt", "Olá, IO Utils!")
    print("Arquivos:", list_files(tmp))
    print("Dirs:", list_dirs("build"))
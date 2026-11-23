import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "app"))
from mascaras import mascara_altura, mascara_idade, mascara_peso


def test_altura_poe_ponto_sozinho():
    assert mascara_altura("1") == "1"
    assert mascara_altura("17") == "1.7"
    assert mascara_altura("156") == "1.56"
    assert mascara_altura("1.56") == "1.56"
    assert mascara_altura("1.") == "1"
    assert mascara_altura("1567") == "1.56"
    assert mascara_altura("") == ""
    assert mascara_altura(None) == ""


def test_peso_e_idade():
    assert mascara_peso("68") == "68"
    assert mascara_peso("1005") == "100"
    assert mascara_peso("68,55") == "68.5"
    assert mascara_peso("a7b0") == "70"
    assert mascara_idade("19a") == "19"
    assert mascara_idade("1234") == "123"

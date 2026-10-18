"""Testes de interface com Selenium (3ª atividade).

Antes de rodar, deixe o sistema no ar em outro terminal:  flask run
Depois:  pytest tests/selenium -v
"""
import os
import unittest
import urllib.request

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # selenium não instalado
    webdriver = None

URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def servidor_no_ar():
    try:
        urllib.request.urlopen(URL, timeout=2)
        return True
    except Exception:
        return False


@unittest.skipIf(webdriver is None, "selenium não instalado")
@unittest.skipUnless(servidor_no_ar(), "sistema não está rodando em " + URL)
class TestInterface(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)
        self.driver.get(URL)

    def tearDown(self):
        self.driver.quit()

    def login(self, email, senha):
        self.driver.find_element(By.ID, "email").send_keys(email)
        self.driver.find_element(By.ID, "senha").send_keys(senha)
        self.driver.find_element(By.ID, "btn-login").click()

    def test_login_admin_valido(self):
        self.login("admin@farmacia.com", "admin123")
        self.wait.until(EC.visibility_of_element_located((By.ID, "painel")))
        self.assertIn("admin", self.driver.find_element(By.ID, "usuario-logado").text)

    def test_login_invalido_mostra_erro(self):
        self.login("admin@farmacia.com", "senha-errada")
        self.wait.until(lambda d: d.find_element(By.ID, "msg-login").text != "")
        self.assertIn("incorretos", self.driver.find_element(By.ID, "msg-login").text)

    def test_admin_cadastra_produto(self):
        self.login("admin@farmacia.com", "admin123")
        self.wait.until(EC.element_to_be_clickable((By.ID, "menu-produtos"))).click()
        nome = "Produto Selenium " + str(os.getpid())
        self.wait.until(EC.visibility_of_element_located((By.ID, "p-nome"))).send_keys(nome)
        self.driver.find_element(By.ID, "p-preco").send_keys("9.90")
        self.driver.find_element(By.ID, "btn-add-produto").click()
        self.wait.until(EC.text_to_be_present_in_element((By.ID, "tb-produtos"), nome))
